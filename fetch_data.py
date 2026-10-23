"""Download daily solar irradiance and temperature for Kaduna from NASA POWER.

Saves the result to data/kaduna_daily.csv so the rest of the project can work offline.
"""
from pathlib import Path

import pandas as pd
import requests

# Kaduna city centre
LATITUDE = 10.5105
LONGITUDE = 7.4165

START = "20150101"
END = "20241231"

# ALLSKY_SFC_SW_DWN = solar energy reaching the ground, clouds included (kWh/m²/day)
# T2M = air temperature at 2 metres (°C)
PARAMETERS = "ALLSKY_SFC_SW_DWN,T2M"

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
OUTPUT = Path(__file__).parent / "data" / "kaduna_daily.csv"


def fetch() -> pd.DataFrame:
    params = {
        "parameters": PARAMETERS,
        "community": "RE",  # "Renewable Energy" community → irradiance comes in kWh/m²/day
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start": START,
        "end": END,
        "format": "JSON",
    }
    response = requests.get(URL, params=params, timeout=120)
    response.raise_for_status()
    data = response.json()["properties"]["parameter"]

    df = pd.DataFrame(
        {
            "irradiance_kwh_m2": data["ALLSKY_SFC_SW_DWN"],
            "temp_c": data["T2M"],
        }
    )
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df.index.name = "date"

    # NASA marks missing days with -999
    df = df.mask(df <= -999)
    return df


if __name__ == "__main__":
    df = fetch()
    OUTPUT.parent.mkdir(exist_ok=True)
    df.to_csv(OUTPUT)
    print(f"Saved {len(df)} days to {OUTPUT}")
    print(f"Missing values: {df.isna().sum().to_dict()}")
    print(df.head())
