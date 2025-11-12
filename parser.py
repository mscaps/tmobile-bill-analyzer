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
    return re.sub(r"\s+", " ", text.strip())

def parse_bill_summary(text):
    """
    Dynamically parse 'This Bill Summary' based on detected column headers.
    Returns: dict with 'columns', 'account', 'totals', 'lines', 'total_tax', 'voice_lines'
    """
    # Locate the 'This Bill Summary' table
    summary_start = text.find("THIS BILL SUMMARY")
    if summary_start == -1:
        raise ValueError("Couldn't locate 'THIS BILL SUMMARY' section.")
    text = text[summary_start:]

    # --- Detect header dynamically ---
    header_match = re.search(r"Line Type (.+?) Total", text)
    if not header_match:
        raise ValueError("Could not detect header columns.")
    header_section = header_match.group(1).strip()

    # Normalize & merge multi-word headers
    raw_headers = header_section.split()
    merged_headers = []
    i = 0
    while i < len(raw_headers):
        word = raw_headers[i]
        if i < len(raw_headers) - 1 and raw_headers[i].lower() == "one-time" and raw_headers[i+1].lower() == "charges":
            merged_headers.append("One-time charges")
            i += 2
        else:
            merged_headers.append(word)
            i += 1

    headers = ["Line Type"] + merged_headers + ["Total"]
    
    # Normalize for regex use
    col_count = len(headers) - 2  # excluding Line Type & Total
    
    # --- Extract Account & Totals rows --- 
    account_pattern = r"Account\s+" + r"(\$[\d\.]+|-)\s+" * col_count + r"(\$[\d\.]+|-)\s+"
    totals_pattern = r"Totals\s+" + r"(\$[\d\.]+|-)\s+" * col_count + r"(\$[\d\.]+|-)\s+"

    acc_match = re.search(account_pattern, text)
    tot_match = re.search(totals_pattern, text)
    account_line = acc_match.group(0) if acc_match else ""
    totals_line = tot_match.group(0) if tot_match else ""
    
    # --- Extract all phone lines ---
    # Handles variable columns and optional dashes
    money_field = r"(\$[\d\.]+|-)"
    line_pattern = re.compile(
        r"(\(\d{3}\)\s*\d{3}-\d{4})\s+([A-Za-z]+)\s+" + r"\s+".join([money_field] * (col_count)) + r"\s+(\$[\d\.]+|-)\s+",
        re.IGNORECASE
    )
    
    tax = 0.0
    voice_lines = 0
    lines = []
    for match in line_pattern.finditer(text):
        phone, ltype, *values = match.groups()
        values = [0.0 if v == "-" else float(v.replace("$", "")) for v in values]
        entry = {"phone": phone, "type": ltype}
        for h, v in zip(headers[1:], values):
            entry[h.lower()] = v
        lines.append(entry)

        if ltype.strip() == "Voice":
            voice_lines += 1
            tax += entry["plans"]

    # --- Parse totals ---
    totals_values = [0.0 if x == "-" else float(x.replace("$", "")) for x in re.findall(r"(\$[\d\.]+|-)\s+", totals_line)]
    totals_dict = dict((h.lower(),v) for h,v in zip(headers[1:], totals_values))

    # --- Parse account ---
    acc_values = [0.0 if x == "-" else float(x.replace("$", "")) for x in re.findall(r"(\$[\d\.]+|-)\s+", account_line)]
    account_dict = dict((h.lower(),v) for h,v in zip(headers[1:], acc_values))

    return {
        "columns": headers,
        "account": account_dict,
        "totals": totals_dict,
        "lines": lines,
        "tax_total": tax,
        "voice_lines": voice_lines
    }

def compute_summary(parsed):
    num_lines = parsed["voice_lines"]
    account_share = parsed["account"]["total"] / num_lines if num_lines else 0
    tax_share = parsed["tax_total"] / num_lines
    
    final_rows = []
    for line in parsed["lines"]:
        if line["type"] == "Voice":
            total = line["total"] - line["plans"] + account_share + tax_share
        else:
            total = line["total"]

        individual_line = {}
        for k, v in line.items():
            if k not in ["plans","services", "total"]:
                individual_line[k] = v
        
        individual_line["cost"] = round(total, 2)
        individual_line["final_total"] = round(total, 3)
        final_rows.append(individual_line)

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
