"""Builds a branded PDF quote from a sizing result."""
import io
from datetime import date

import matplotlib
matplotlib.use("Agg")  # draw charts without opening a window
import matplotlib.pyplot as plt
from fpdf import FPDF

from sizing import Appliance

ORANGE = (230, 126, 34)
DARK = (40, 40, 40)
GREY = (120, 120, 120)


def naira(amount: float) -> str:
    # The built-in PDF fonts have no ₦ symbol, so we write NGN
    return f"NGN {amount:,.0f}"


def coverage_chart(monthly_check) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(8, 2.8))
    ax.bar(monthly_check.index, monthly_check["production_kwh_day"], color="#f0ad4e", label="Solar production")
    ax.axhline(monthly_check["need_kwh_day"].iloc[0], color="#d9534f", linestyle="--", label="Your daily need")
    ax.set_ylabel("kWh per day")
    ax.set_title("Expected solar production in Kaduna, month by month")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=8, frameon=False)
    fig.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=150)
    plt.close(fig)
    buffer.seek(0)
    return buffer


def build_quote(result: dict, appliances: list[Appliance], business: dict, customer: str, quote_no: str) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Header
    pdf.set_fill_color(*ORANGE)
    pdf.rect(0, 0, 210, 28, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_xy(12, 8)
    pdf.cell(0, 8, business["name"] or "Solar Installer")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(12, 17)
    pdf.cell(0, 6, " | ".join(x for x in [business.get("phone"), business.get("location")] if x))

    pdf.set_text_color(*DARK)
    pdf.set_xy(12, 34)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Solar System Quote", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Quote no: {quote_no}    Date: {date.today():%d %B %Y}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Prepared for: {customer or 'Customer'}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    # Recommended system
    section(pdf, "Recommended system")
    rows = [
        ("Solar panels", f"{result['panel_count']} x {result['panel_watts']}W ({result['pv_kw']:.2f} kW)"),
        ("Batteries", f"{result['battery_count']} x {result['battery_unit']} {result['battery_type']} ({result['battery_kwh']} kWh)"),
        ("Inverter", f"{result['inverter_kva']} kVA, {result['system_volts']}V system"),
        ("Charge controller", f"{result['controller_amps']}A MPPT"),
    ]
    table(pdf, rows, widths=(55, 131))
    pdf.ln(2)

    # Customer load
    section(pdf, "Your appliances")
    pdf.set_font("Helvetica", "B", 9)
    for header, w in zip(["Appliance", "Watts", "Qty", "Day hrs", "Night hrs", "Wh/day"], [66, 24, 16, 24, 26, 30]):
        pdf.cell(w, 7, header, border="B")
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for a in appliances:
        for value, w in zip([a.name, f"{a.watts:g}", a.quantity, f"{a.day_hours:g}", f"{a.night_hours:g}", f"{a.daily_wh:,.0f}"],
                            [66, 24, 16, 24, 26, 30]):
            pdf.cell(w, 5, str(value))
        pdf.ln()
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 7, f"Total: {result['daily_kwh']} kWh per day ({result['night_kwh']} kWh at night), "
                   f"peak load {result['peak_w']:,.0f} W", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    # Price
    section(pdf, "Price")
    rows = [(item, naira(cost)) for item, cost in result["costs"].items()]
    table(pdf, rows, widths=(130, 56), align_right=True)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(130, 9, "TOTAL")
    pdf.cell(56, 9, naira(result["total_cost"]), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    # Why this size
    section(pdf, "Why this size?")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5,
        f"This system is designed for {result['design_month']}, the least sunny month in Kaduna "
        f"({result['sun_hours']} kWh/m2/day on average, from 10 years of NASA satellite data). "
        "Systems sized for average sunshine often run out of power during the rainy season. "
        "Sizing for the worst month means your power keeps running all year.")
    pdf.ln(2)
    pdf.image(coverage_chart(result["monthly_check"]), w=160, x=25)

    pdf.set_auto_page_break(auto=False)
    pdf.set_y(-14)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 5, "Solar data: NASA POWER (power.larc.nasa.gov). Quote valid for 14 days. Prices may change with exchange rates.",
             align="C")

    return bytes(pdf.output())


def section(pdf: FPDF, title: str) -> None:
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*ORANGE)
    pdf.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*DARK)


def table(pdf: FPDF, rows: list[tuple[str, str]], widths: tuple[int, int], align_right: bool = False) -> None:
    pdf.set_font("Helvetica", "", 10)
    for label, value in rows:
        pdf.cell(widths[0], 6, label, border="B")
        pdf.cell(widths[1], 6, value, border="B", align="R" if align_right else "L", new_x="LMARGIN", new_y="NEXT")
