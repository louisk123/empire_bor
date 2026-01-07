
import pdfplumber
import pandas as pd
import os
from datetime import datetime
import re


# -------------------------
# CLEAN NUMBER
# -------------------------
def clean_num(x):
    if x is None:
        return 0
    x = str(x).replace(",", "").strip()
    try:
        return float(x)
    except:
        return 0

def is_date(val):
    try:
        datetime.strptime(str(val).strip(), "%d-%m-%Y")
        return True
    except:
        return False


def contains_time(text):
    if not text:
        return False
    return bool(re.search(r"\b\d{1,2}:\d{2}(?:\s?[APMapm]{2})?\b", text))

def date_and_time_detected(text):
    if not text:
        return False

    # Time patterns: 6:30, 06:30, 6:30 PM, 6:30AM
    time_pattern = r"\b\d{1,2}:\d{2}(?:\s?[APMapm]{2})?\b"

    # Date patterns: 2025-09-16 or 2025/09/16
    date_pattern = r"\b\d{4}[-/]\d{2}[-/]\d{2}\b"

    has_time = bool(re.search(time_pattern, text))
    has_date = bool(re.search(date_pattern, text))

    return has_time and has_date




def last_col_is_digit(row):
    if not row:
        return False

    last = str(row[-1]).replace(",", "").strip()
    return last.replace(".", "", 1).isdigit()

def last_six_are_numbers(row):
    if len(row) < 6:
        return False

    last6 = row[-6:]

    for x in last6:
        if x is None:
            return False
        s = str(x).replace(",", "").strip()
        if not s.replace(".", "", 1).isdigit():  # allow one decimal
            return False
    return True


def extract_time(text):
    match = re.search(r"\b\d{1,2}:\d{2}\s*(AM|PM)\b", text, re.IGNORECASE)
    if match:
        # clean spaces: "4:00 PM" → "4:00PM"
        return match.group().replace(" ", "").upper()
    return None



def detect_page_pattern(text):
    pattern = r"^Page\s+\d+\s+of\s+\d+$"
    return bool(re.match(pattern, text.strip()))

# -------------------------
# HEADER INFO (Cinema + Weekly)
# -------------------------
def extract_header_info(pdf_path):
    cinema = "AL SHAAB"
    week_tag = ""
    d1= None
    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        lines = first_page.extract_text().splitlines() if first_page.extract_text() else []
        # WEEKLY DETECTION
        for ln in lines:
            L = ln.upper()
            if "REPORT FROM" in L:
                parts = ln.split()
                # Example: Screening Period 2025-09-11 TO 2025-09-17
                d1 = datetime.strptime(parts[3], "%d-%m-%Y").strftime("%d-%m-%Y")
                d2 = datetime.strptime(parts[9], "%d-%m-%Y").strftime("%d-%m-%Y")
            
                week_tag = "Weekly" if (
                    datetime.strptime(parts[9], "%d-%m-%Y") -
                    datetime.strptime(parts[3], "%d-%m-%Y")
                ).days > 1 else ""
                break

    return cinema, week_tag, d1


# -------------------------
# EXTRACT PDF TABLES
# -------------------------
def extract_pdf(pdf_path,exhibitor):

    cinema, week_tag , show_date  = extract_header_info(pdf_path)
    rows = []

    current_movie = None
    current_screen= None
    ticket_type = None
    show_date= None
    show_time= None


    with pdfplumber.open(pdf_path) as pdf:
        for pidx, page in enumerate(pdf.pages, start=1):
            lines = page.extract_text().splitlines() if page.extract_text() else []
            fake_table = []
            for ln in lines:
                ln = ln.strip()
                if not ln:
                    continue
                # skip garbage / header lines

                # split respecting multiple spaces and keep empty slots
                parts = ln.replace("\t", " ").split(" ")
                parts = [p for p in parts if p != ""]  # collapse extra spaces
                #print(parts)
                fake_table=[]
                fake_table.append(parts)

                if ("AL SHAAB" in ln.upper() or
                    "TRN:" in ln.upper() or
                    "DISTRIBUTOR SHOW REPORT" in ln.upper() or
                    "REPORT FROM" in ln.upper() or
                    "MUNICIPAL" in ln.upper() or
                    "AMT" in ln.upper() or
                    "REPORT FROM" in ln.upper() or
                    "TAX 10%" in ln.upper() or
                    "TOTAL OF :" in ln.upper() or
                    "GRAND TOTAL" in ln.upper() or
                    "PRINTED ON :" in ln.upper() #or
                    #detect_page_pattern(ln)
                   ):
                      continue

                # feed the rest of your script with fake rows
                for row in fake_table:
                        if not row:
                            continue

                        # ----------------------------------
                        # Extract ROW DATA
                        # ----------------------------------

                        try:

                          #detect date
                          if "DATE :" in ln:
                            show_date = row[2]
                            continue

                          #detect time
                          temp_time= extract_time(ln)
                          if temp_time is not None:
                            show_time= temp_time
                            ticket_type= " ".join(row[1:-6]).strip()


                          #detect movie
                          if "FILM :" in ln:
                            current_movie = ln.strip().replace("FILM : ", "").replace("DISTRIBUTOR :", "").replace("Empire Films", "").strip()
                            #print(current_movie)
                            continue

                          #detect  screen
                          if "SCREEN :" in ln:
                            current_screen = ln.strip().replace("SCREEN : ", "")
                            continue



                          row=row[-6:]
                          avg_price   = clean_num(row[1])
                          admits      = clean_num(row[0])
                          comps       = None
                          grs         = clean_num(row[4])
                          vat         = clean_num(row[2])
                          mtax        = clean_num(row[3])
                          net         = clean_num(row[5])

                          #print(f"{show_date}, {screen}, {show_time}, {admits}, {grs}")
                          movie_format = "2D"

                          rows.append([
                              pdf_path,
                              exhibitor,
                              cinema,
                              week_tag,
                              datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                              current_movie,
                              show_date,
                              show_time,
                              current_screen,
                              movie_format,
                              ticket_type,
                              admits,
                              grs,
                              net,
                              comps,
                              None,
                              None
                          ])
                        except Exception:
                          prev_row = row
                          prev_line=ln
                          continue


                        prev_row = row
                        prev_line=ln

    return rows


# -------------------------
# MAIN FUNCTION
# -------------------------

def fetch_data(pdf_path,exhibitor):
  all_rows = []
  all_rows.extend(extract_pdf(pdf_path,exhibitor))
  columns = [
      "File", "Exhibitor","Cinema", "Week Type", "Extraction Date","Movie","Date","Time", "Screen" , "Format", "Ticket Type","Admits","Gross","Net", "Comp" ,"Is Summary",   "Summary Sessions"]
  df = pd.DataFrame(all_rows, columns=columns)
  return df

#df=fetch_data("/content/drive/MyDrive/Empire/Python/PDFs/shaab.pdf","shaab")
#df.to_excel("output.xlsx", index=False)

