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
    # Defining line types to ignore other text after the phone number
    LINE_TYPES = ["Voice", "Wearable", "Mobile Internet", "Digits", "Tablet", "Other", "Watch"]
    type_regex = "(" + "|".join(LINE_TYPES) + ")"

    money_field = r"(\$[\d\.]+|-)"
    plan_field = r"\s?([-]?\$[\d\.]+)\s?"  # to consider negative values
    # decreasing the column count as we explictly including the plan field and
    # using the plan field regex for totals as it may contain negative values 
    line_pattern = re.compile(
        r"(\(\d{3}\)\s*\d{3}-\d{4})\s+(.*?)" + type_regex + plan_field + 
        r"\s?".join([money_field] * (col_count-1)) + plan_field,
        re.IGNORECASE
    )
    
    # identify lines to be ignored but include in calculation
    IGNORE_KEYWORDS = ["old number","port out","replaced"]
    tax = 0.0
    voice_lines = 0
    lines = []
    for match in line_pattern.finditer(text):
        phone, etxt, ltype, *values = match.groups()
        ignore = any(k in etxt.lower() for k in IGNORE_KEYWORDS)
        entry = {"phone": phone, "type": ltype, "ignore": ignore}
        for h, v in zip(headers[1:], values):
            v = 0.0 if v in ("-", "None", None, "") else float(v.replace("$", ""))
            entry[h.lower()] = v
        lines.append(entry)

        if ltype.strip() == "Voice":
            if not ignore:
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
        if line["ignore"]:
            continue

        if line["type"] == "Voice":
            total = line["total"] - line["plans"] + account_share + tax_share
        else:
            total = line["total"]

        individual_line = {}
        for k, v in line.items():
            if k not in ["plans","services", "total", "ignore"]:
                individual_line[k] = v
        
        individual_line["cost"] = round(total, 2)
        individual_line["final_total"] = round(total, 3)
        final_rows.append(individual_line)

    return pd.DataFrame(final_rows)

def generate_qr(df):
    """Generate QR text grouped by line type, with per-type totals."""
    # Sort/group by Type
    grouped = df.sort_values(by=["type", "phone"])
    grouped_lines = []
    grouped_lines.append("T-Mobile Bill Summary\n")  

    for t, sub in grouped.groupby("type"):
        grouped_lines.append(f"{t} Lines:")
        for _, r in sub.iterrows():
            safe_line = r["phone"]
            # safe_line = re.sub(r'\D', '', safe_line)
            safe_line = safe_line.replace("(", "").replace(")", "").replace(" ", "-")  # non-breaking hyphen
            safe_line = safe_line.replace(" ", "")  # tidy up spaces
            safe_line = f"x{safe_line}"  # add prefix to avoid number-first parsing
            grouped_lines.append(f"  {safe_line}: ${r['cost']}")
        grouped_lines.append("")  # blank line between types

    text = "\n".join(grouped_lines).strip()

    qr = qrcode.QRCode(version=2, box_size=8, border=4, error_correction=qrcode.constants.ERROR_CORRECT_Q)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
