"""Appliance list for the app: pick from the catalogue in a pop-up, edit or delete rows."""
import uuid

import streamlit as st

from appliances import (
    CUSTOM_VARIANT, OTHER_APPLIANCE, USAGE_PRESETS,
    appliance_names, default_usage, get_variant, split_hours, variant_names,
)
from sizing import Appliance

def K(name: str) -> str:
    """Widget key for the pop-up form. Bumping the revision gives the form fresh, empty widgets."""
    return f"f{st.session_state.get('form_rev', 0)}_{name}"


# --- Form state helpers --------------------------------------------------------
def _items() -> list[dict]:
    if "items" not in st.session_state:
        st.session_state["items"] = []
    return st.session_state["items"]


def _clear_form() -> None:
    """Start the pop-up form from scratch (drops the old widgets' values)."""
    rev = st.session_state.get("form_rev", 0)
    for key in [k for k in st.session_state if str(k).startswith(f"f{rev}_")]:
        st.session_state.pop(key, None)
    st.session_state["form_rev"] = rev + 1


def _apply_variant_defaults() -> None:
    """When the type/size changes, fill in its watts."""
    variant = get_variant(st.session_state.get(K("appliance")), st.session_state.get(K("variant")))
    if variant is not None:
        st.session_state[K("watts")] = float(variant.watts)


def _on_appliance_change() -> None:
    """When the appliance changes, pick its first type/size and its usual usage."""
    appliance = st.session_state.get(K("appliance"))
    if not appliance:
        return
    st.session_state[K("variant")] = variant_names(appliance)[0]
    usage, hours = default_usage(appliance)
    st.session_state[K("usage")] = usage
    st.session_state[K("hours")] = float(hours)
    day, night = split_hours(usage, hours)
    st.session_state[K("day")], st.session_state[K("night")] = day, night
    if appliance == OTHER_APPLIANCE:
        st.session_state[K("watts")] = 100.0
    else:
        _apply_variant_defaults()


def _load_into_form(item: dict) -> None:
    _clear_form()
    st.session_state.update({
        K("appliance"): item["appliance"], K("custom_name"): item["custom_name"], K("variant"): item["variant"],
        K("watts"): float(item["watts"]), K("qty"): int(item["qty"]), K("usage"): item["usage"],
        K("hours"): float(item["hours"]), K("day"): float(item["day"]), K("night"): float(item["night"]),
        K("note"): item["note"],
    })


def _display_name(item: dict) -> str:
    return item["custom_name"] if item["appliance"] == OTHER_APPLIANCE else item["appliance"]


def to_appliance(item: dict) -> Appliance:
    variant = get_variant(item["appliance"], item["variant"])
    return Appliance(
        name=_display_name(item), watts=float(item["watts"]), quantity=int(item["qty"]),
        day_hours=float(item["day"]), night_hours=float(item["night"]),
        duty=variant.duty if variant else 1.0, surge=variant.surge if variant else 1.0,
        variant="" if item["variant"] == CUSTOM_VARIANT else item["variant"], note=item["note"].strip(),
    )


def _usage_text(item: dict) -> str:
    return f"{item['usage']} · {item['day']:g} h day / {item['night']:g} h night"


# --- Pop-up form -----------------------------------------------------------------
@st.dialog("Appliance", width="large")
def appliance_dialog(edit_id: str | None = None) -> None:
    items = _items()
    if st.session_state.pop("form_just_added", None):
        st.success(f"Added {st.session_state.pop('form_added_label', 'appliance')}. Add the next one below.",
                   icon=":material/check_circle:")

    st.session_state.setdefault(K("qty"), 1)
    start = {} if K("appliance") in st.session_state else {"index": None}
    appliance = st.selectbox("Appliance", appliance_names(), key=K("appliance"), **start,
                             placeholder="Start typing to search, e.g. fridge", on_change=_on_appliance_change)
    if not appliance:
        st.caption("Pick an appliance to continue.")
        return

    custom_name = ""
    if appliance == OTHER_APPLIANCE:
        custom_name = st.text_input("Appliance name", key=K("custom_name"), placeholder="e.g. Popcorn machine")

    variant = st.selectbox("Type / size", variant_names(appliance), key=K("variant"), on_change=_apply_variant_defaults)

    c1, c2 = st.columns(2)
    watts = c1.number_input("Watts (each)", min_value=1.0, step=5.0, format="%g", key=K("watts"),
                            help="Filled in from the type/size. Change it if the label on the appliance says otherwise.")
    qty = c2.number_input("Quantity", min_value=1, step=1, key=K("qty"))

    usage = st.selectbox("Usage", USAGE_PRESETS, key=K("usage"))
    if usage == "Custom":
        c3, c4 = st.columns(2)
        day = c3.number_input("Daytime hours", 0.0, 12.0, step=0.5, format="%g", key=K("day"), help="Runs straight from the panels")
        night = c4.number_input("Night hours", 0.0, 12.0, step=0.5, format="%g", key=K("night"), help="Runs from the battery")
        hours = day + night
    elif usage == "24 hours":
        hours = 24.0
        day, night = split_hours(usage, hours)
        st.caption("12 h during the day and 12 h at night.")
    else:
        hours = st.number_input("Hours per day", 0.1, 24.0, step=0.5, format="%g", key=K("hours"))
        day, night = split_hours(usage, hours)
        st.caption(f"{day:g} h during the day, {night:g} h at night.")

    # Duplicate check: same appliance already in the list?
    same = [it for it in items if it["appliance"] == appliance and it["id"] != edit_id
            and (appliance != OTHER_APPLIANCE or it["custom_name"].strip().lower() == custom_name.strip().lower())]
    same_variant = [it for it in same if it["variant"] == variant and variant != CUSTOM_VARIANT]
    note_required = bool(same) and not same_variant
    note = st.text_input("Brand / note" + (" (required)" if note_required else " (optional)"), key=K("note"),
                         placeholder="e.g. Samsung, kitchen")

    blocked = False
    existing_notes = {}
    if same_variant:
        target = same_variant[0]
        st.warning(f"**{_display_name(target)} ({variant})** is already in the list. "
                   "To add more of the same, increase its quantity instead.", icon=":material/warning:")
        if st.button(f"Increase quantity by {int(qty)}", icon=":material/add_circle:", type="primary"):
            target["qty"] = int(target["qty"]) + int(qty)
            _clear_form()
            st.rerun()
        blocked = True
    elif note_required:
        name = _display_name(same[0])
        if not note.strip():
            st.warning(f"You already have a **{name}** in this list. Add a brand or note "
                       "(e.g. \"Samsung, kitchen\") so the customer can tell them apart.", icon=":material/warning:")
            blocked = True
        for it in same:
            if not it["note"].strip():
                existing_notes[it["id"]] = st.text_input(
                    f"Brand / note for your existing {name} ({it['variant']}) (required)",
                    key=K(f"existing_note_{it['id']}"), placeholder="e.g. LG, living room")
                if not existing_notes[it["id"]].strip():
                    blocked = True

    if appliance == OTHER_APPLIANCE and not custom_name.strip():
        blocked = True
    if hours <= 0:
        st.warning("Usage must be more than 0 hours.", icon=":material/warning:")
        blocked = True

    item = {
        "id": edit_id or uuid.uuid4().hex, "appliance": appliance, "custom_name": custom_name.strip(),
        "variant": variant, "watts": float(watts), "qty": int(qty), "usage": usage, "hours": float(hours),
        "day": float(day), "night": float(night), "note": note.strip(),
    }

    def save() -> None:
        for item_id, value in existing_notes.items():
            next(it for it in items if it["id"] == item_id)["note"] = value.strip()
        if edit_id:
            index = next(i for i, it in enumerate(items) if it["id"] == edit_id)
            items[index] = item
        else:
            items.append(item)

    if edit_id:
        if st.button("Save changes", icon=":material/save:", type="primary", disabled=blocked, width="stretch"):
            save()
            _clear_form()
            st.rerun()
    elif not same_variant:
        b1, b2 = st.columns(2)
        if b1.button("Add", icon=":material/add:", type="primary", disabled=blocked, width="stretch"):
            save()
            _clear_form()
            st.rerun()
        if b2.button("Add another", icon=":material/playlist_add:", disabled=blocked, width="stretch"):
            save()
            _clear_form()
            st.session_state["form_just_added"] = True
            st.session_state["form_added_label"] = to_appliance(item).label
            st.rerun(scope="fragment")


@st.dialog("Clear all appliances?")
def clear_all_dialog() -> None:
    st.write("This removes every appliance from the list. It can't be undone.")
    c1, c2 = st.columns(2)
    if c1.button("Clear all", icon=":material/delete_sweep:", type="primary", width="stretch"):
        st.session_state["items"] = []
        st.rerun()
    if c2.button("Cancel", width="stretch"):
        st.rerun()


# --- The list on the page --------------------------------------------------------
ADD_BOX_CSS = """
<style>
.st-key-add_box button {
    border: 2px dashed #e67e22; background: transparent; min-height: 3.2rem; color: #e67e22; font-weight: 600;
}
.st-key-add_box button:hover { background: rgba(230, 126, 34, 0.08); border-color: #e67e22; color: #e67e22; }
/* Keep each appliance card on one line on phones: text on the left, icons on the right */
[class*="st-key-approw_"] div[data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 0.25rem; }
[class*="st-key-approw_"] div[data-testid="stColumn"] { min-width: 0 !important; }
[class*="st-key-approw_"] div[data-testid="stColumn"]:not(:first-child) { flex: 0 0 2.2rem !important; width: 2.2rem !important; }
</style>
"""


def appliance_section() -> list[Appliance]:
    items = _items()
    st.markdown(ADD_BOX_CSS, unsafe_allow_html=True)

    head_left, head_right = st.columns([4, 1])
    head_left.subheader("1. Customer's appliances")
    if items and head_right.button("Clear all", icon=":material/delete_sweep:", width="stretch"):
        clear_all_dialog()

    for it in list(items):
        app = to_appliance(it)
        with st.container(border=True, key=f"approw_{it['id']}"):
            text, edit_col, delete_col = st.columns([10, 1, 1], vertical_alignment="center")
            details = ", ".join(x for x in [app.variant, app.note] if x)
            text.markdown(
                f"**{app.name}**" + (f" · {details}" if details else "")
                + f"  \n:gray[{it['watts']:g} W × {it['qty']} · {_usage_text(it)} · **{app.daily_wh:,.0f} Wh/day**]"
            )
            if edit_col.button(":material/edit:", key=f"edit_{it['id']}", help="Edit", type="tertiary"):
                _load_into_form(it)
                appliance_dialog(it["id"])
            if delete_col.button(":material/delete:", key=f"del_{it['id']}", help="Delete row", type="tertiary"):
                st.session_state["items"] = [x for x in items if x["id"] != it["id"]]
                st.rerun()

    if st.button("Click to add an appliance", icon=":material/add:", key="add_box", width="stretch"):
        _clear_form()
        appliance_dialog(None)

    return [to_appliance(it) for it in items]
