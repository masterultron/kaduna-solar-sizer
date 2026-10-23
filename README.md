# Kaduna Solar Sizer

Sizing off-grid solar systems for homes and small businesses in Kaduna, Nigeria — using real NASA satellite solar data instead of guesswork.

## Why
Grid power in Nigeria is unreliable, so many households and businesses buy solar systems. Most systems are sized by rough rule-of-thumb, which leads to oversized (wasted money) or undersized (batteries die at night) installations.

## What it does (in progress)
1. **Data:** downloads daily solar irradiance for Kaduna from NASA POWER and analyses it month by month.
2. **Sizing engine:** turns a customer's appliance list into panel, battery and inverter sizes, designed for the worst (least sunny) month.
3. **Installer app:** a web tool for solar installers to size a system and generate a quote in minutes.

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Data source
NASA POWER Project (https://power.larc.nasa.gov/) — free, public satellite-derived solar and weather data.
