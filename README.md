# 📦 Home Inventory

A colorful Streamlit dashboard for tracking household items, backed by a live Google Sheet.

## How it works

- **Google Sheet = the database.** Edit quantities, add rows, or change locations in the
  "Home Inventory" sheet and the dashboard picks it up within ~10 minutes.
- **Streamlit = the pretty face.** Reads the sheet with a service account and renders
  KPIs, a low-stock shopping list, charts, and a searchable table.

## Columns in the sheet

| Column     | Meaning                                              |
|------------|------------------------------------------------------|
| Item       | Name of the thing                                    |
| Category   | Kitchen, Tools, Electronics, …                       |
| Quantity   | How many you have                                    |
| Reorder At | Shopping-list alert level — `0` means "don't track"  |
| Location   | Where it lives                                       |
| Notes      | Anything useful                                      |

An item shows up under "Running low" when `Quantity <= Reorder At` (and `Reorder At > 0`).

## Adding and updating items

Use the **➕ Add a new item** and **🔄 Update quantity** forms right in the app —
they write straight to the sheet and the dashboard refreshes instantly.
(This needs the service account to have **Editor** access to the sheet,
and the app requests the full `spreadsheets` OAuth scope.)

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Without Google credentials configured, the app shows the demo data from `sample_data.csv`.

## Deploy (Streamlit Community Cloud)

1. Push this folder to a public GitHub repo.
2. On share.streamlit.io → New app → pick the repo, main file `app.py`.
3. In the app's **Secrets**, add:
   ```toml
   sheet_id = "YOUR_SHEET_ID"

   [gcp_service_account]
   # paste the service-account JSON key fields here
   ```
   The Google Sheet must be shared (Viewer) with the service account's email.
4. Deploy — no code changes needed.
