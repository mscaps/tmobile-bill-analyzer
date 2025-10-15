import streamlit as st
import pdfplumber
import re
import pandas as pd
import qrcode
from io import BytesIO

def extract_page2_text(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        if len(pdf.pages) < 2:
            st.error("PDF has fewer than 2 pages.")
            return ""
        text = pdf.pages[1].extract_text()
    return text

def clean_text(text):
    """Normalize spacing and line breaks for regex parsing."""
    # Remove double spaces and merge broken numeric lines
    text = re.sub(r"\s+", " ", text)
    return text

def parse_bill_summary(text):
    """Parse Account, Totals, and line entries from normalized text."""
    summary = {"lines": []}

    # --- Account ---
    acc_pattern = r"Account\s+\$([\d\.]+)\s+-\s+\$([\d\.]+)\s+\$([\d\.]+)"
    acc_match = re.search(acc_pattern, text)
    if acc_match:
        summary["account_plan"] = float(acc_match.group(1))
        summary["account_services"] = float(acc_match.group(2))
    else:
        summary["account_plan"] = summary["account_services"] = 0.0

    # --- Totals ---
    totals_pattern = r"Totals\s+\$([\d\.]+)\s+\$([\d\.]+)\s+\$([\d\.]+)\s+\$([\d\.]+)"
    tmatch = re.search(totals_pattern, text)
    if tmatch:
        summary["totals"] = {
            "plans": float(tmatch.group(1)),
            "equipment": float(tmatch.group(2)),
            "services": float(tmatch.group(3)),
            "grand": float(tmatch.group(4)),
        }

    # --- Individual lines (handles “-” properly) ---
    line_pattern = re.compile(
        r"(\(\d{3}\)\s*\d{3}-\d{4})\s+([A-Za-z]+)\s+\$([\d\.]+)\s+(\$[\d\.]+|-)\s+(\$[\d\.]+|-)\s+\$([\d\.]+)",
        re.IGNORECASE,
    )
    tax = 0.0
    lines = 0
    for m in line_pattern.finditer(text):
        phone, ltype, plan, equip, serv, total = m.groups()
        if ltype.strip() == "Voice":
            lines += 1
            tax += float(plan)
        summary["lines"].append({
            "phone": phone.strip(),
            "type": ltype.strip(),
            "plan": float(plan),
            "equipment": 0.0 if equip == "-" else float(equip.removeprefix('$')),
            "services": 0.0 if serv == "-" else float(serv.removeprefix('$')),
            "total": float(total),
        })
    
    summary["tax_total"] = tax
    summary["total_lines"] = lines
    return summary

def compute_summary(data):
    num_lines = data["total_lines"] #len(data["lines"])
    shared_account = (data["account_plan"] + data["account_services"]) / num_lines
    shared_tax = data["tax_total"] / num_lines

    final_rows = []
    for line in data["lines"]:
        if line["type"] == "Voice":
            total = line["equipment"] + line["services"] + shared_account + shared_tax
        else:
            total = line["total"]
        final_rows.append({
            "phone": line["phone"],
            "type": line["type"],
            "cost": round(total, 2),
            "final_total": round(total, 3),
        })
    return pd.DataFrame(final_rows)

def generate_qr(df):
    text = "T-Mobile Summary\n" + "\n".join(
        [f"{r.phone} ({r.type}): ${r.cost}" for r in df.itertuples()]
    )
    qr = qrcode.QRCode(version=1, box_size=8, border=4)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
