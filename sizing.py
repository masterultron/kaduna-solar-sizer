"""Sizing engine: turns an appliance list into a solar system design.

The key idea: size the panels for the WORST (least sunny) month, not the average,
so the system keeps working through the rainy season.
"""
import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

MONTHLY_DATA = Path(__file__).parent / "outputs" / "kaduna_monthly.csv"

# --- Real-world losses -------------------------------------------------------
PANEL_TEMP_COEFF = 0.004   # panels lose ~0.4% output per °C above 25 °C
CELL_TEMP_RISE = 25        # in sunshine, panel cells run ~25 °C hotter than the air
SOILING_LOSS = 0.05        # dust (harmattan) on panels
WIRING_LOSS = 0.03         # cables and connections
INVERTER_EFFICIENCY = 0.90

# --- Equipment ---------------------------------------------------------------
INVERTER_SIZES_KVA = [1, 1.5, 2.5, 3.5, 5, 7.5, 10, 15]
POWER_FACTOR = 0.8         # kVA → usable watts
INVERTER_MARGIN = 1.25     # 25% headroom over the peak load
INVERTER_SURGE_RATIO = 2.0 # inverters can briefly deliver ~2x their rating to start motors
CONTROLLER_SIZES_A = [20, 30, 40, 60, 80, 100]

BATTERIES = {
    "Lithium (LiFePO4)": {"amp_hours": 100, "depth_of_discharge": 0.9, "efficiency": 0.95, "module_volts": None},
    "Lead-acid (tubular)": {"amp_hours": 200, "depth_of_discharge": 0.5, "efficiency": 0.85, "module_volts": 12},
}

# Example Nigerian market prices (₦). Installers should replace these with their own.
DEFAULT_PRICES = {
    "panel": 165_000,             # per panel
    "battery_lithium_per_kwh": 300_000,
    "battery_lead_acid": 380_000,  # per 12V 200Ah battery
    "inverter_per_kva": 180_000,
    "controller_per_amp": 4_000,
    "installation_pct": 0.15,      # cables, mounting, protection, labour
}


@dataclass
class Appliance:
    name: str
    watts: float
    quantity: int
    day_hours: float    # hours used while the sun is up
    night_hours: float  # hours used after sunset (runs from the battery)
    duty: float = 1.0   # share of the time it draws full power (fridges cycle on and off)
    surge: float = 1.0  # start-up multiplier for motors (pumps, compressors)
    variant: str = ""   # type / size, e.g. "Double-door"
    note: str = ""      # brand or note, e.g. "Samsung, kitchen"

    @property
    def total_watts(self) -> float:
        return self.watts * self.quantity

    @property
    def daily_wh(self) -> float:
        return self.total_watts * self.duty * (self.day_hours + self.night_hours)

    @property
    def label(self) -> str:
        details = ", ".join(x for x in [self.variant, self.note] if x)
        return f"{self.name} ({details})" if details else self.name

    @property
    def night_wh(self) -> float:
        return self.total_watts * self.duty * self.night_hours


def load_monthly_sun(path: Path = MONTHLY_DATA) -> pd.DataFrame:
    """Monthly average sun (kWh/m²/day = 'peak sun hours') and temperature."""
    return pd.read_csv(path, index_col=0)


def panel_derate(air_temp_c: float) -> float:
    """Fraction of rated panel output you actually get, after heat, dust and wiring losses."""
    cell_temp = air_temp_c + CELL_TEMP_RISE
    temp_loss = max(0.0, (cell_temp - 25) * PANEL_TEMP_COEFF)
    return (1 - temp_loss) * (1 - SOILING_LOSS) * (1 - WIRING_LOSS)


def round_up_to(value: float, sizes: list[float]) -> float:
    for size in sizes:
        if size >= value:
            return size
    step = sizes[-1]
    return math.ceil(value / step) * step


def system_voltage(inverter_kva: float, pv_watts: float) -> int:
    """Bigger systems use higher voltage so cables and controllers carry less current."""
    if inverter_kva <= 1 and pv_watts <= 800:
        return 12
    if inverter_kva <= 2.5 and pv_watts <= 1600:
        return 24
    return 48


def size_system(
    appliances: list[Appliance],
    battery_type: str = "Lithium (LiFePO4)",
    panel_watts: int = 550,
    backup_nights: float = 1,
    design_month: str | None = None,
    prices: dict | None = None,
    monthly: pd.DataFrame | None = None,
) -> dict:
    """Size a full system. design_month=None means 'use the worst month'."""
    monthly = load_monthly_sun() if monthly is None else monthly
    prices = {**DEFAULT_PRICES, **(prices or {})}
    battery = BATTERIES[battery_type]

    # 1. How much energy does the customer use?
    daily_wh = sum(a.daily_wh for a in appliances)
    night_wh = sum(a.night_wh for a in appliances)
    peak_w = sum(a.total_watts for a in appliances)

    # 2. Which month do we design for?
    if design_month is None:
        design_month = monthly["irradiance_kwh_m2"].idxmin()
    sun_hours = monthly.loc[design_month, "irradiance_kwh_m2"]
    derate = panel_derate(monthly.loc[design_month, "temp_c"])

    # 3. Panels: energy needed ÷ (sun hours × losses)
    energy_from_panels_wh = daily_wh / INVERTER_EFFICIENCY
    pv_watts_needed = energy_from_panels_wh / (sun_hours * derate)
    panel_count = max(1, math.ceil(pv_watts_needed / panel_watts))
    pv_watts = panel_count * panel_watts

    # 4. Inverter: everything on at once, plus headroom. It must also start the
    #    biggest motor (one at a time) while everything else is running.
    extra_surge_w = max((a.watts * (a.surge - 1) for a in appliances), default=0)
    inverter_w = max(peak_w * INVERTER_MARGIN, (peak_w + extra_surge_w) / INVERTER_SURGE_RATIO)
    inverter_kva = round_up_to(inverter_w / (POWER_FACTOR * 1000), INVERTER_SIZES_KVA)
    volts = system_voltage(inverter_kva, pv_watts)

    # 5. Batteries: night-time energy, only part of the battery is usable
    battery_wh_needed = night_wh * backup_nights / (
        battery["depth_of_discharge"] * battery["efficiency"] * INVERTER_EFFICIENCY
    )
    module_volts = battery["module_volts"] or volts        # lithium modules match the system voltage
    unit_wh = module_volts * battery["amp_hours"]
    per_string = volts // module_volts                      # 12V batteries wired in series to reach 24V/48V
    strings = max(1, math.ceil(battery_wh_needed / (unit_wh * per_string)))
    battery_count = strings * per_string
    battery_kwh = battery_count * unit_wh / 1000

    # 6. Charge controller: panel current at system voltage, plus 25%
    controller_amps = round_up_to(pv_watts / volts * 1.25, CONTROLLER_SIZES_A)

    # 7. Cost
    if battery_type.startswith("Lithium"):
        battery_cost = battery_kwh * prices["battery_lithium_per_kwh"]
    else:
        battery_cost = battery_count * prices["battery_lead_acid"]
    equipment = {
        "Solar panels": panel_count * prices["panel"],
        "Batteries": battery_cost,
        "Inverter": inverter_kva * prices["inverter_per_kva"],
        "Charge controller": controller_amps * prices["controller_per_amp"],
    }
    equipment_total = sum(equipment.values())
    installation = equipment_total * prices["installation_pct"]

    # 8. Month-by-month check: does the system cover the load all year?
    monthly_check = pd.DataFrame({
        "production_kwh_day": [
            pv_watts * monthly.loc[m, "irradiance_kwh_m2"] * panel_derate(monthly.loc[m, "temp_c"])
            * INVERTER_EFFICIENCY / 1000
            for m in monthly.index
        ],
    }, index=monthly.index)
    monthly_check["need_kwh_day"] = daily_wh / 1000
    monthly_check["coverage_pct"] = (monthly_check["production_kwh_day"] / monthly_check["need_kwh_day"] * 100).round(0)

    return {
        "design_month": design_month,
        "sun_hours": round(float(sun_hours), 2),
        "derate": round(derate, 3),
        "daily_kwh": round(daily_wh / 1000, 2),
        "night_kwh": round(night_wh / 1000, 2),
        "peak_w": peak_w,
        "panel_count": panel_count,
        "panel_watts": panel_watts,
        "pv_kw": pv_watts / 1000,
        "inverter_kva": inverter_kva,
        "system_volts": volts,
        "battery_type": battery_type,
        "battery_count": battery_count,
        "battery_unit": f"{module_volts}V {battery['amp_hours']}Ah",
        "battery_kwh": round(battery_kwh, 2),
        "controller_amps": controller_amps,
        "costs": {**equipment, "Installation & accessories": installation},
        "total_cost": equipment_total + installation,
        "monthly_check": monthly_check.round(2),
    }


EXAMPLE_HOME = [
    Appliance("LED bulbs", 10, 8, 0, 6),
    Appliance("Ceiling fan", 75, 3, 6, 8),
    Appliance("TV (43 inch)", 100, 1, 3, 4),
    Appliance("Fridge", 150, 1, 12, 12),
    Appliance("Phone & laptop charging", 65, 2, 3, 2),
]


if __name__ == "__main__":
    worst = size_system(EXAMPLE_HOME)
    average = size_system(EXAMPLE_HOME, design_month="Apr")

    print(f"Example home uses {worst['daily_kwh']} kWh/day ({worst['night_kwh']} kWh at night), peak {worst['peak_w']} W\n")
    for label, r in [("Sized for worst month (Aug)", worst), ("Sized for sunniest month (Apr)", average)]:
        aug = r["monthly_check"].loc["Aug", "coverage_pct"]
        print(f"{label}:")
        print(f"  {r['panel_count']} x {r['panel_watts']}W panels ({r['pv_kw']} kW)")
        print(f"  {r['inverter_kva']} kVA inverter, {r['system_volts']}V system")
        print(f"  {r['battery_count']} x {r['battery_unit']} {r['battery_type']} ({r['battery_kwh']} kWh)")
        print(f"  {r['controller_amps']}A charge controller")
        print(f"  Total: ₦{r['total_cost']:,.0f}")
        print(f"  August coverage: {aug:.0f}% of daily need\n")
