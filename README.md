# 📱 T-Mobile Bill Analyzer

[![View in Streamlit](https://img.shields.io/badge/Streamlit-Live_App-E20074?logo=streamlit&logoColor=white)](https://tmobile-bill-analyzer.streamlit.app)

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
```
or in Windows PowerShell:
```bash
$env:STREAMLIT_TELEMETRY = "False"
$env:STREAMLIT_ANALYTICS = "False"
```

### 🚀 Deploy on Streamlit Cloud
```bash
Visit https://share.streamlit.io
Click “New App”
Connect your GitHub account
Choose your repo → select the main branch and app.py as the entry point
Click Deploy
```
Streamlit Cloud automatically redeploys when you push to GitHub, but included an Actions workflow makes it explicit and reliable.


