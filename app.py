"""
Home Inventory Dashboard
========================
A colorful Streamlit web app that reads your home inventory from a
Google Sheet and turns it into a beautiful dashboard — now with forms
to add items and update quantities right from the app.

WHAT YOU'LL LEARN FROM THIS FILE
- Same skeleton as before: setup -> styling -> data -> UI
- @st.cache_resource: reuse the Google API client instead of
  re-authenticating on every rerun (compare with @st.cache_data for data)
- st.form: grouping widgets so the app only reruns on Submit, not on
  every keystroke
- Writing to Google Sheets: ws.append_row() and ws.update_cell()
- st.cache_data.clear() + st.rerun(): refresh the dashboard after a write
- Demo-mode guard: forms only appear when the live sheet is connected
"""

import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------------------------------------------------------------
# 1. PAGE SETUP
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Home Inventory",
    page_icon="📦",
    layout="wide",
)

# ---------------------------------------------------------------------------
# 2. CUSTOM STYLING
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .app-header {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        border-radius: 20px;
        padding: 2rem;
        color: white;
        margin-bottom: 1.5rem;
    }
    .app-header h1 { color: white !important; margin: 0; }
    .app-header p { color: #eafff3 !important; margin: 0.3rem 0 0 0; }
    .kpi-card {
        border-radius: 16px;
        padding: 1.2rem 1.4rem;
        color: white;
        box-shadow: 0 4px 14px rgba(0,0,0,0.12);
    }
    .kpi-card .kpi-label { font-size: 0.85rem; opacity: 0.9; }
    .kpi-card .kpi-value { font-size: 1.9rem; font-weight: 700; margin-top: 0.2rem; }
    .kpi-1 { background: linear-gradient(135deg, #11998e, #38ef7d); }
    .kpi-2 { background: linear-gradient(135deg, #667eea, #764ba2); }
    .kpi-3 { background: linear-gradient(135deg, #f093fb, #f5576c); }
    .kpi-4 { background: linear-gradient(135deg, #f6d365, #fda085); }
    </style>
    """,
    unsafe_allow_html=True,
)

PALETTE = [
    "#11998e", "#667eea", "#f093fb", "#f6d365",
    "#4facfe", "#f5576c", "#38ef7d", "#a18cd1",
]

# Full read/write scope — the app now edits the sheet, not just reads it
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# ---------------------------------------------------------------------------
# 3. GOOGLE SHEETS CONNECTION
#    - @st.cache_resource keeps ONE API client for the whole session
#    - If secrets are missing (local demo), ws stays None and the app
#      falls back to sample_data.csv with the forms disabled
# ---------------------------------------------------------------------------
@st.cache_resource
def get_worksheet():
    import gspread
    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES,
    )
    client = gspread.authorize(creds)
    return client.open_by_key(st.secrets["sheet_id"]).sheet1


try:
    ws = get_worksheet()
    LIVE = True
except Exception:
    ws = None
    LIVE = False


@st.cache_data(ttl=600)
def load_data() -> pd.DataFrame:
    if LIVE:
        df = pd.DataFrame(ws.get_all_records())
    else:
        df = pd.read_csv("sample_data.csv")
        st.info("👀 Showing demo data — connect your Google Sheet (see README) to see your own inventory.")

    df["Quantity"] = pd.to_numeric(df["Quantity"])
    df["Reorder At"] = pd.to_numeric(df["Reorder At"])
    # Derived column: True when stock has hit (or passed) the reorder point.
    # Reorder At = 0 means "one-off item, don't track" (e.g. a ladder).
    df["Low Stock"] = (df["Quantity"] <= df["Reorder At"]) & (df["Reorder At"] > 0)
    return df


df = load_data()

# ---------------------------------------------------------------------------
# 4. HEADER
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="app-header">
        <h1>📦 Home Inventory</h1>
        <p>Everything you own, searchable in one place.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 5. SIDEBAR FILTERS
# ---------------------------------------------------------------------------
st.sidebar.header("🎛️ Filters")

search = st.sidebar.text_input("🔍 Search items", placeholder="e.g. batteries")

categories = st.sidebar.multiselect(
    "Categories",
    options=sorted(df["Category"].unique()),
    default=sorted(df["Category"].unique()),
)

locations = st.sidebar.multiselect(
    "Locations",
    options=sorted(df["Location"].unique()),
    default=sorted(df["Location"].unique()),
)

filtered = df[
    df["Category"].isin(categories) & df["Location"].isin(locations)
]
if search:
    filtered = filtered[
        filtered["Item"].str.contains(search, case=False, na=False)
        | filtered["Notes"].str.contains(search, case=False, na=False)
    ]

if filtered.empty:
    st.warning("Nothing matches those filters — try widening them.")
    st.stop()

# ---------------------------------------------------------------------------
# 6. KPI CARDS
# ---------------------------------------------------------------------------
low_stock = filtered[filtered["Low Stock"]]

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.markdown(
    f'<div class="kpi-card kpi-1"><div class="kpi-label">Items tracked</div>'
    f'<div class="kpi-value">{len(filtered)}</div></div>',
    unsafe_allow_html=True,
)
kpi2.markdown(
    f'<div class="kpi-card kpi-2"><div class="kpi-label">Total units</div>'
    f'<div class="kpi-value">{int(filtered["Quantity"].sum())}</div></div>',
    unsafe_allow_html=True,
)
kpi3.markdown(
    f'<div class="kpi-card kpi-3"><div class="kpi-label">Categories</div>'
    f'<div class="kpi-value">{filtered["Category"].nunique()}</div></div>',
    unsafe_allow_html=True,
)
kpi4.markdown(
    f'<div class="kpi-card kpi-4"><div class="kpi-label">⚠️ Low stock</div>'
    f'<div class="kpi-value">{len(low_stock)}</div></div>',
    unsafe_allow_html=True,
)

st.write("")

# ---------------------------------------------------------------------------
# 7. ADD / UPDATE FORMS
#    st.form batches the widgets: nothing reruns until Submit is pressed.
#    After a write we clear the data cache and rerun so the KPIs, charts
#    and table update instantly.
# ---------------------------------------------------------------------------
st.subheader("✏️ Manage inventory")

if not LIVE:
    st.info("🔒 Connect your Google Sheet to enable adding and updating items.")
else:
    form_left, form_right = st.columns(2)

    with form_left:
        with st.form("add_item", clear_on_submit=True):
            st.markdown("**➕ Add a new item**")
            new_name = st.text_input("Item name")
            new_category = st.text_input("Category", placeholder="Kitchen, Tools, …")
            new_qty = st.number_input("Quantity", min_value=0, step=1, value=1)
            new_reorder = st.number_input(
                "Reorder at (0 = don't track)", min_value=0, step=1, value=1
            )
            new_location = st.text_input("Location", placeholder="e.g. Garage")
            new_notes = st.text_input("Notes (optional)")
            add_submitted = st.form_submit_button("Add item", type="primary")

        if add_submitted:
            if not new_name.strip():
                st.error("Give the item a name first.")
            else:
                ws.append_row(
                    [new_name.strip(), new_category.strip(), int(new_qty),
                     int(new_reorder), new_location.strip(), new_notes.strip()],
                    value_input_option="USER_ENTERED",
                )
                st.cache_data.clear()
                st.success(f"Added **{new_name.strip()}** ✓")
                st.rerun()

    with form_right:
        with st.form("update_qty"):
            st.markdown("**🔄 Update quantity**")
            item_choice = st.selectbox("Item", options=sorted(df["Item"].unique()))
            new_quantity = st.number_input("New quantity", min_value=0, step=1)
            update_submitted = st.form_submit_button("Update quantity", type="primary")

        if update_submitted:
            # Sheet row = DataFrame position + 2 (header row + 1-based indexing)
            match = df.index[df["Item"] == item_choice].tolist()
            ws.update_cell(match[0] + 2, 3, int(new_quantity))  # column C = Quantity
            st.cache_data.clear()
            st.success(f"**{item_choice}** is now at {int(new_quantity)} ✓")
            st.rerun()

# ---------------------------------------------------------------------------
# 8. LOW STOCK — the "shopping list" section
# ---------------------------------------------------------------------------
if not low_stock.empty:
    st.subheader("⚠️ Running low — shopping list")
    st.dataframe(
        low_stock[["Item", "Category", "Quantity", "Reorder At", "Location"]].sort_values("Quantity"),
        use_container_width=True,
        hide_index=True,
    )

# ---------------------------------------------------------------------------
# 9. CHARTS
# ---------------------------------------------------------------------------
by_category = (
    filtered.groupby("Category", as_index=False)["Quantity"].sum().sort_values("Quantity")
)
by_location = (
    filtered.groupby("Location", as_index=False).size().rename(columns={"size": "Items"})
    .sort_values("Items")
)

left, right = st.columns(2)

with left:
    st.subheader("📊 Units by category")
    fig_bar = px.bar(
        by_category, x="Quantity", y="Category", orientation="h",
        color="Category", color_discrete_sequence=PALETTE,
        text_auto=".2s",
    )
    fig_bar.update_layout(showlegend=False, height=380)
    st.plotly_chart(fig_bar, use_container_width=True)

with right:
    st.subheader("🗺️ Items by location")
    fig_bar2 = px.bar(
        by_location, x="Items", y="Location", orientation="h",
        color="Location", color_discrete_sequence=PALETTE,
        text_auto=".2s",
    )
    fig_bar2.update_layout(showlegend=False, height=380)
    st.plotly_chart(fig_bar2, use_container_width=True)

# ---------------------------------------------------------------------------
# 10. FULL TABLE
# ---------------------------------------------------------------------------
st.subheader("📋 Everything")
st.dataframe(
    filtered[["Item", "Category", "Quantity", "Reorder At", "Location", "Notes"]].sort_values("Item"),
    use_container_width=True,
    hide_index=True,
)

st.caption("Built with Streamlit 💛 — edits you make here land in the Google Sheet instantly.")
