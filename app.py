import streamlit as st
import pandas as pd
from parser import extract_page2_text, clean_text, parse_bill_summary, compute_summary, generate_qr
import plotly.express as px

# ---------- Streamlit Config ----------
st.set_page_config(
    page_title="T-Mobile Bill Analyzer",
    page_icon="📱",
    layout="wide"
)

# Disable Streamlit analytics & usage stats
st.session_state["_disable_tracking"] = True
st._is_running_with_streamlit = True

st.markdown("""
    <style>
        body { background-color: #fff; color: #000; }
        h1, h2, h3, h4 { color: #E20074 !important; }
        .stButton>button {
            background-color: #E20074;
            color: white;
            border-radius: 10px;
            padding: 0.6em 1.2em;
            font-weight: 600;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📱 T-Mobile Monthly Bill Analyzer")
st.caption("This app runs locally and stores no data. Upload your PDF to generate a per-line cost summary.")

uploaded_file = st.file_uploader("📤 Upload your T-Mobile Monthly Bill Summary Statement PDF", type=["pdf"])

if uploaded_file:
    text = extract_page2_text(uploaded_file)
    text = clean_text(text)
    data = parse_bill_summary(text)
    df = compute_summary(data)
    total = df["final_total"].sum()
    bill_total = data["totals"]["total"]
    
    st.success("✅ Bill summary generated successfully!")
    st.markdown(f"### 💰 Total Bill: **${bill_total:.2f}**")
    st.subheader("📊 Individual Line Breakdown")

    # Columns to hide in UI (but keep in data)
    hidden_cols = ["type", "final_total"]

    # Style: center align & 2-decimal formatting
    def style_table(df):
        styled = (
            df.style
            .format(precision=2, na_rep="-")
            .set_properties(**{"text-align": "center"})
            .hide(axis="index")
        )
        return styled

    grouped = df.groupby("type", sort=False)
    for line_type, group in grouped:
        # Prepare display copy
        display_df = group.drop(columns=hidden_cols)
        display_df = display_df.reset_index(drop=True)
        display_df.index = display_df.index + 1  # index start from 1
        display_df = display_df.rename_axis("#").reset_index()

        # Calculate group subtotal (based on hidden final_total + visible services)
        subtotal = group["final_total"].sum()

        st.markdown(f"### 📱 {line_type} Lines")
        st.dataframe(
            style_table(display_df),
            width="content",
            column_config={"phone": "Phone Number","cost": "Fee ($)"},
            hide_index=True,
        )
        st.markdown(f"<div style='text-align:left; font-weight:600; color:#E20074;'>Subtotal for {line_type}: ${subtotal:.2f}</div>", unsafe_allow_html=True)
        st.markdown("---")
 
    st.markdown(f"### 💰 Grand Total: **${total:.2f}**")
    if bill_total != round(total,2):
        st.warning("💰 Bill total do not match!")

    qr_buf = generate_qr(df)
    st.image(qr_buf, caption="Scan to share summary", width=250)
else:
    st.info("Upload your T-Mobile statement to begin.")
