# 📱 T-Mobile Bill Analyzer

A private, local-friendly Streamlit app that parses T-Mobile monthly summary statements, computes per-line totals, and displays shareable QR summaries.

### Features
- Upload monthly PDF bills
- Grouped, formatted per-line cost summaries
- QR code summary generation
- No analytics, no telemetry

### Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Online (Public Access)
Deployed via Streamlit Cloud:
➡️ https://your-app-name.streamlit.app

### No Analytics, No Telemetry
Streamlit will not collect stats from the code. 
If you want to guarantee no usage collection, you can set environment variables:
```bash
export STREAMLIT_TELEMETRY=False
export STREAMLIT_ANALYTICS=False

or in Windows PowerShell:
$env:STREAMLIT_TELEMETRY = "False"
$env:STREAMLIT_ANALYTICS = "False"
```