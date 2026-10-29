"""Appliance catalogue: common Nigerian household and small-business appliances.

Each appliance has variants (types/sizes). For every variant we store:
  watts  - rated power on the label (what the installer sees and can edit)
  duty   - share of the time it actually draws that power. Fridges, freezers and
           ACs switch their motor on and off, so a 150 W fridge on for 24 hours
           uses far less than 150 W x 24 h.
  surge  - start-up multiplier for appliances with motors (pumps, compressors).
           The inverter must be able to start them.

Each appliance also has a default usage pattern and typical hours per day.
Values are typical figures; installers can change the watts for any item.
"""
from dataclasses import dataclass

CUSTOM_VARIANT = "Other / custom size"

# Usage presets: how the daily hours are split between daytime (runs straight
# from the panels) and night-time (runs from the battery).
USAGE_PRESETS = ["24 hours", "Day and evening", "Daytime only", "Evening only", "Custom"]


@dataclass(frozen=True)
class Variant:
    name: str
    watts: float
    duty: float = 1.0
    surge: float = 1.0


@dataclass(frozen=True)
class CatalogueItem:
    name: str
    category: str
    variants: tuple[Variant, ...]
    usage: str        # one of USAGE_PRESETS (not "Custom")
    hours: float      # typical hours per day for that pattern


def _item(name, category, variants, usage, hours):
    return CatalogueItem(name, category, tuple(Variant(*v) for v in variants), usage, hours)


CATALOGUE: list[CatalogueItem] = [
    # --- Lighting -------------------------------------------------------------
    _item("LED bulb", "Lighting",
          [("Small (5 W)", 5), ("Standard (9 W)", 9), ("Bright (12 W)", 12), ("Extra bright (18 W)", 18)],
          "Evening only", 6),
    _item("Fluorescent tube", "Lighting",
          [("2 ft (18 W)", 18), ("4 ft (36 W)", 36)], "Evening only", 6),
    _item("Energy-saving bulb (CFL)", "Lighting",
          [("Standard (15 W)", 15), ("Large (23 W)", 23)], "Evening only", 6),
    _item("Incandescent bulb", "Lighting",
          [("60 W", 60), ("100 W", 100)], "Evening only", 6),
    _item("Security / flood light (LED)", "Lighting",
          [("Small (30 W)", 30), ("Medium (50 W)", 50), ("Large (100 W)", 100)], "Evening only", 12),

    # --- Cooling ---------------------------------------------------------------
    _item("Ceiling fan", "Cooling",
          [("Small 36 inch", 50), ("Standard 56 inch", 75), ("Energy-saving (BLDC)", 35)], "Day and evening", 12),
    _item("Standing fan", "Cooling",
          [("16 inch", 55), ("18 inch", 65)], "Day and evening", 10),
    _item("Table fan", "Cooling", [("Standard", 40)], "Day and evening", 8),
    _item("Rechargeable fan (charging)", "Cooling", [("Standard", 25)], "Daytime only", 4),
    _item("Air cooler", "Cooling", [("Standard", 150)], "Day and evening", 8),
    _item("Air conditioner", "Cooling",
          [("1 HP non-inverter", 900, 0.8, 3), ("1 HP inverter", 650, 0.6, 1.2),
           ("1.5 HP non-inverter", 1300, 0.8, 3), ("1.5 HP inverter", 950, 0.6, 1.2),
           ("2 HP non-inverter", 1800, 0.8, 3), ("2 HP inverter", 1300, 0.6, 1.2)],
          "Day and evening", 8),

    # --- Kitchen ---------------------------------------------------------------
    _item("Fridge", "Kitchen",
          [("Mini / bar fridge", 70, 0.45, 3), ("Small single-door", 100, 0.45, 3),
           ("Medium single-door", 150, 0.45, 3), ("Double-door", 200, 0.45, 3),
           ("Large double-door", 250, 0.45, 3), ("Side-by-side", 350, 0.45, 3),
           ("Inverter fridge", 120, 0.35, 1.5)],
          "24 hours", 24),
    _item("Deep freezer", "Kitchen",
          [("Small chest (up to 150 L)", 120, 0.5, 3), ("Medium chest (about 250 L)", 180, 0.5, 3),
           ("Large chest (400 L or more)", 250, 0.5, 3), ("Upright freezer", 200, 0.5, 3),
           ("Inverter freezer", 150, 0.4, 1.5)],
          "24 hours", 24),
    _item("Water dispenser", "Kitchen",
          [("Cold only", 100, 0.5, 2), ("Hot and cold", 500, 0.3, 2)], "Day and evening", 12),
    _item("Microwave", "Kitchen",
          [("Small (700 W)", 700), ("Standard (1000 W)", 1000), ("Large (1500 W)", 1500)], "Daytime only", 0.3),
    _item("Electric kettle", "Kitchen",
          [("Standard (1500 W)", 1500), ("Fast boil (2000 W)", 2000)], "Daytime only", 0.3),
    _item("Blender", "Kitchen",
          [("Standard (350 W)", 350, 1, 2), ("Heavy duty (600 W)", 600, 1, 2)], "Daytime only", 0.2),
    _item("Rice cooker", "Kitchen",
          [("Small (500 W)", 500), ("Large (700 W)", 700)], "Daytime only", 1),
    _item("Electric hot plate", "Kitchen",
          [("Single burner (1000 W)", 1000), ("Double burner (2000 W)", 2000)], "Daytime only", 1),
    _item("Toaster", "Kitchen", [("Standard", 800)], "Daytime only", 0.2),

    # --- Entertainment -----------------------------------------------------------
    _item("Television", "Entertainment",
          [("LED 24 inch", 30), ("LED 32 inch", 50), ("LED 43 inch", 80), ("LED 50 inch", 100),
           ("LED 55 inch", 120), ("LED 65 inch", 150), ("Old CRT (box) TV", 100)],
          "Day and evening", 6),
    _item("Decoder (DStv / GOtv / Startimes)", "Entertainment", [("Standard", 20)], "Day and evening", 6),
    _item("Sound system / home theatre", "Entertainment",
          [("Small (50 W)", 50), ("Large (150 W)", 150)], "Evening only", 3),
    _item("Game console", "Entertainment",
          [("PlayStation / Xbox", 200)], "Evening only", 3),
    _item("Wi-Fi router / MiFi", "Entertainment", [("Standard", 10)], "24 hours", 24),
    _item("Starlink dish", "Entertainment", [("Standard", 75)], "24 hours", 24),

    # --- Office & electronics ----------------------------------------------------
    _item("Phone charging", "Office & electronics",
          [("Standard charger (10 W)", 10), ("Fast charger (25 W)", 25)], "Day and evening", 3),
    _item("Laptop", "Office & electronics",
          [("Small / ultrabook (45 W)", 45), ("Standard (65 W)", 65), ("Gaming (150 W)", 150)],
          "Day and evening", 6),
    _item("Desktop computer", "Office & electronics",
          [("Office desktop with monitor", 200), ("Gaming desktop with monitor", 450)], "Daytime only", 6),
    _item("Printer", "Office & electronics",
          [("Inkjet", 30), ("Laser", 400, 0.3)], "Daytime only", 1),
    _item("Photocopier", "Office & electronics", [("Office photocopier", 1000, 0.3)], "Daytime only", 2),
    _item("CCTV system", "Office & electronics",
          [("4 cameras", 40), ("8 cameras", 80)], "24 hours", 24),
    _item("POS terminal (charging)", "Office & electronics", [("Standard", 10)], "Daytime only", 3),

    # --- Household ---------------------------------------------------------------
    _item("Pressing iron", "Household",
          [("Dry iron (1000 W)", 1000, 0.6), ("Standard (1200 W)", 1200, 0.6), ("Steam iron (2000 W)", 2000, 0.6)],
          "Daytime only", 0.5),
    _item("Washing machine", "Household",
          [("Twin tub", 350, 1, 2), ("Top load", 500, 1, 2), ("Front load", 800, 1, 2)], "Daytime only", 1),
    _item("Water heater", "Household",
          [("Instant (3000 W)", 3000), ("Storage tank (1500 W)", 1500, 0.5)], "Daytime only", 1),
    _item("Hair dryer", "Household",
          [("Handheld (1200 W)", 1200), ("Powerful (1800 W)", 1800)], "Daytime only", 0.3),
    _item("Vacuum cleaner", "Household", [("Standard", 1000, 1, 2)], "Daytime only", 0.3),

    # --- Water pumping -----------------------------------------------------------
    _item("Water pump (surface)", "Water pumping",
          [("0.5 HP", 375, 1, 3), ("0.75 HP", 550, 1, 3), ("1 HP", 750, 1, 3), ("1.5 HP", 1100, 1, 3)],
          "Daytime only", 1),
    _item("Borehole pump (submersible)", "Water pumping",
          [("1 HP", 750, 1, 3), ("1.5 HP", 1100, 1, 3), ("2 HP", 1500, 1, 3)], "Daytime only", 1),

    # --- Business ----------------------------------------------------------------
    _item("Hair clipper", "Business", [("Standard", 15)], "Daytime only", 8),
    _item("Salon hood dryer", "Business", [("Standard", 1000, 0.7)], "Daytime only", 3),
    _item("Display fridge (drinks cooler)", "Business",
          [("Single-door", 250, 0.5, 3), ("Double-door", 400, 0.5, 3)], "24 hours", 24),
    _item("Sewing machine", "Business", [("Electric", 100, 1, 1.5)], "Daytime only", 6),
    _item("Grinding machine (small)", "Business", [("Small (1.5 kW)", 1500, 1, 3)], "Daytime only", 1),

    # --- Medical -----------------------------------------------------------------
    _item("CPAP machine", "Medical", [("Standard", 40)], "Evening only", 8),
    _item("Oxygen concentrator", "Medical", [("5 litre", 300)], "24 hours", 24),
]

BY_NAME = {item.name: item for item in CATALOGUE}
OTHER_APPLIANCE = "Other appliance (not in list)"


def appliance_names() -> list[str]:
    """Sorted list for the searchable dropdown, with 'Other' at the end."""
    return sorted(BY_NAME) + [OTHER_APPLIANCE]


def variant_names(appliance: str) -> list[str]:
    if appliance not in BY_NAME:
        return [CUSTOM_VARIANT]
    return [v.name for v in BY_NAME[appliance].variants] + [CUSTOM_VARIANT]


def get_variant(appliance: str, variant: str) -> Variant | None:
    item = BY_NAME.get(appliance)
    if item is None:
        return None
    return next((v for v in item.variants if v.name == variant), None)


def default_usage(appliance: str) -> tuple[str, float]:
    item = BY_NAME.get(appliance)
    return (item.usage, item.hours) if item else ("Day and evening", 4.0)


def split_hours(preset: str, hours: float) -> tuple[float, float]:
    """Turn a usage preset into (day hours, night hours). Each side is at most 12."""
    if preset == "24 hours":
        return 12.0, 12.0
    if preset == "Daytime only":
        return min(hours, 12.0), 0.0
    if preset == "Evening only":
        return 0.0, min(hours, 12.0)
    # Day and evening: split evenly
    half = min(hours / 2, 12.0)
    return half, half
