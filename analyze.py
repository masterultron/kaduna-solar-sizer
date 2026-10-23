"""Monthly solar analysis for Kaduna.

Reads data/kaduna_daily.csv (from fetch_data.py), averages it by month,
finds the worst (least sunny) month and saves a chart to outputs/.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "kaduna_daily.csv"
OUTPUTS = ROOT / "outputs"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    monthly = df.groupby(df.index.month).agg(
        irradiance_kwh_m2=("irradiance_kwh_m2", "mean"),
        irradiance_min=("irradiance_kwh_m2", "min"),
        temp_c=("temp_c", "mean"),
    )
    monthly.index = MONTHS
    return monthly.round(2)


def plot(monthly: pd.DataFrame, path: Path) -> None:
    worst = monthly["irradiance_kwh_m2"].idxmin()
    colors = ["#d9534f" if m == worst else "#f0ad4e" for m in monthly.index]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(monthly.index, monthly["irradiance_kwh_m2"], color=colors)
    ax.bar_label(bars, fmt="%.2f", padding=3, fontsize=9)
    ax.axhline(monthly["irradiance_kwh_m2"].mean(), color="grey", linestyle="--", linewidth=1,
               label=f"Yearly average: {monthly['irradiance_kwh_m2'].mean():.2f}")
    ax.set_title("Average daily solar energy in Kaduna, Nigeria (NASA POWER, 2015–2024)")
    ax.set_ylabel("kWh per m² per day")
    ax.set_ylim(0, monthly["irradiance_kwh_m2"].max() * 1.15)
    ax.legend(loc="lower left")
    ax.text(0.99, 0.97, f"Worst month: {worst} (red) — systems are sized for this",
            transform=ax.transAxes, ha="right", va="top", fontsize=9, color="#d9534f")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    df = pd.read_csv(DATA, index_col="date", parse_dates=True)
    monthly = monthly_summary(df)

    OUTPUTS.mkdir(exist_ok=True)
    monthly.to_csv(OUTPUTS / "kaduna_monthly.csv")
    plot(monthly, OUTPUTS / "kaduna_monthly_sunshine.png")

    print(monthly)
    worst = monthly["irradiance_kwh_m2"].idxmin()
    best = monthly["irradiance_kwh_m2"].idxmax()
    print(f"\nBest month:  {best} ({monthly.loc[best, 'irradiance_kwh_m2']} kWh/m²/day)")
    print(f"Worst month: {worst} ({monthly.loc[worst, 'irradiance_kwh_m2']} kWh/m²/day)")
    print(f"Yearly average: {monthly['irradiance_kwh_m2'].mean():.2f} kWh/m²/day")
