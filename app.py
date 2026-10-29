"""The Solar Sizer — web app for solar installers.

Run locally with:  streamlit run app.py
"""
from datetime import datetime

import pandas as pd
import streamlit as st

from appliance_ui import appliance_section
from quote_pdf import build_quote, coverage_chart
from sizing import BATTERIES, DEFAULT_PRICES, load_monthly_sun, size_system

st.set_page_config(page_title="The Solar Sizer", page_icon=":material/wb_sunny:", layout="wide")

# --- Sidebar: installer settings --------------------------------------------
with st.sidebar:
    st.header("Your business")
    business = {
        "name": st.text_input("Business name", "Sunrise Solar Kaduna"),
        "phone": st.text_input("Phone", "+234 800 000 0000"),
        "location": st.text_input("Location", "Kaduna, Nigeria"),
    }

    st.header("Equipment")
    battery_type = st.selectbox("Battery type", list(BATTERIES))
    panel_watts = st.select_slider("Panel size (W)", options=[300, 400, 450, 500, 550, 600], value=550)
    backup_nights = st.slider("Nights of battery backup", 1.0, 3.0, 1.0, 0.5)

    st.header("Your prices (₦)")
    prices = {
        "panel": st.number_input("Per panel", value=DEFAULT_PRICES["panel"], step=5_000),
        "battery_lithium_per_kwh": st.number_input("Lithium battery, per kWh", value=DEFAULT_PRICES["battery_lithium_per_kwh"], step=10_000),
        "battery_lead_acid": st.number_input("Lead-acid battery, each", value=DEFAULT_PRICES["battery_lead_acid"], step=10_000),
        "inverter_per_kva": st.number_input("Inverter, per kVA", value=DEFAULT_PRICES["inverter_per_kva"], step=10_000),
        "controller_per_amp": st.number_input("Charge controller, per amp", value=DEFAULT_PRICES["controller_per_amp"], step=500),
        "installation_pct": st.slider("Installation & accessories (%)", 0, 40, int(DEFAULT_PRICES["installation_pct"] * 100)) / 100,
    }

# --- Main: customer load -----------------------------------------------------
st.title(":material/wb_sunny: The Solar Sizer")
st.caption("Size a solar system and send a quote in 2 minutes — designed for Kaduna's least sunny month, "
           "using 10 years of NASA satellite data.")

customer = st.text_input("Customer name", placeholder="e.g. Mallam Musa, Barnawa")

appliances = appliance_section()

if not appliances:
    st.info("Add the customer's appliances to size a system.", icon=":material/info:")
    st.stop()

monthly = load_monthly_sun()
result = size_system(appliances, battery_type, panel_watts, backup_nights, prices=prices, monthly=monthly)

# --- Results -----------------------------------------------------------------
st.subheader("2. Recommended system")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Solar panels", result["panel_count"], f"{panel_watts}W each · {result['pv_kw']:.2f} kW", delta_color="off")
c2.metric("Batteries", result["battery_count"], f"{result['battery_unit']} · {result['battery_kwh']} kWh", delta_color="off")
c3.metric("Inverter", f"{result['inverter_kva']} kVA", f"{result['system_volts']}V system", delta_color="off")
c4.metric("Charge controller", f"{result['controller_amps']} A", "MPPT", delta_color="off")

st.write(f"Daily use **{result['daily_kwh']} kWh** ({result['night_kwh']} kWh at night) · "
         f"peak load **{result['peak_w']:,.0f} W** · designed for **{result['design_month']}** "
         f"({result['sun_hours']} kWh/m²/day)")

left, right = st.columns([3, 2])
with left:
    st.markdown("**Production vs. need, month by month**")
    st.image(coverage_chart(result["monthly_check"]))

    average_design = size_system(appliances, battery_type, panel_watts, backup_nights,
                                 design_month="Apr", prices=prices, monthly=monthly)
    aug_cover = average_design["monthly_check"].loc[result["design_month"], "coverage_pct"]
    if average_design["panel_count"] < result["panel_count"]:
        st.warning(f"A system sized for sunny April ({average_design['panel_count']} panels) would only cover "
                   f"**{aug_cover:.0f}%** of this customer's need in {result['design_month']}. "
                   f"This design adds {result['panel_count'] - average_design['panel_count']} panel(s) to prevent that.")

with right:
    st.markdown("**Price**")
    costs = pd.DataFrame({"Item": result["costs"].keys(), "Cost (₦)": [f"{v:,.0f}" for v in result["costs"].values()]})
    st.dataframe(costs, hide_index=True, width="stretch")
    st.markdown(f"### Total: ₦{result['total_cost']:,.0f}")

# --- Quote -------------------------------------------------------------------
st.subheader("3. Send the quote")
quote_no = f"Q-{datetime.now():%y%m%d-%H%M}"
pdf = build_quote(result, appliances, business, customer, quote_no)
st.download_button("Download PDF quote", pdf, icon=":material/download:", file_name=f"solar_quote_{quote_no}.pdf",
                   mime="application/pdf", type="primary")

st.divider()
st.caption("Solar data: NASA POWER, Kaduna (10.51°N, 7.42°E), 2015–2024. Estimates only — "
           "a site visit should confirm roof space, shading and wiring.")
