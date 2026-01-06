import pdfplumber
import pandas as pd
import os
from datetime import datetime
import re

screens =["SAFEER PRIME","SCREEN-1","SCREEN-2","SCREEN-3","SCREEN-4","SCREEN-5","SCREEN-6","SCREEN-7","SCREEN-8","SCREEN-9","SCREEN-10"]
ticket_types=["PREMIUM","STANDARD","PRIME"]


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

def detect_time(text):
    pattern = r"^\d{1,2}:\d{2}\s?(AM|PM)$"
    return bool(re.match(pattern, text.strip()))


def detect_screen(line):
    scr_upper = line.upper()
    for scr in screens:
        scr=scr.upper()
        if scr in scr_upper:
            return True
    return False

def detect_ticket_types(line):
    scr_upper = line.upper()
    for scr in ticket_types:
        scr=scr.upper()
        if scr in scr_upper:
            return True
    return False



def detect_page_pattern(text):
    pattern = r"Page\s+\d+\s+of\s+\d+\s*$"
    return bool(re.search(pattern, text))


# -------------------------
# HEADER INFO (Cinema + Weekly)
# -------------------------
def extract_header_info(pdf_path):
    week_tag = ""
    d1= None
    line_index = 0
    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        lines = first_page.extract_text().splitlines() if first_page.extract_text() else []
        #print("date extraction")
        # WEEKLY DETECTION
        for ln in lines:
            if not ln.strip():
              continue  # skip blanks
            
            line_index += 1
        
            if line_index == 2:
                cinema = ln.strip()
                continue
 
            L = ln.upper()
            if "FROM DATE" in L:
                parts = ln.split()
                # Example: Screening Period 2025-09-11 TO 2025-09-17
                d1 = datetime.strptime(parts[3], "%d-%m-%Y").date()
                d2 = datetime.strptime(parts[9], "%d-%m-%Y").date()
                week_tag = "Weekly" if (d2 - d1).days > 1 else ""
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

                if ("FILMWISE" in ln.upper() or
                    "SAFEER" in ln.upper() or
                    "M.TAX" in ln.upper() or
                    "TOTAL OF" in ln.upper() or
                    "GRAND TOTAL" in ln.upper() or
                    "FROM DATE" in ln.upper() or
                    date_and_time_detected(ln) or
                    detect_page_pattern(ln)
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
                          #if is_date(row[0]):
                          #  show_date = row[0]
                          #  continue

                          #detect time
                          if detect_time(ln):
                            show_time= ln.strip()
                            continue

                          #detect movie
                          if not last_six_are_numbers(row) and not detect_screen(ln) and not  detect_ticket_types(ln):
                            current_movie = ln.strip()
                            #print(current_movie)
                            continue

                          #detect  screen
                          if not last_six_are_numbers(row) and detect_screen(ln):
                            current_screen = ln.strip()
                            continue

                          #detect ticket
                          if not last_six_are_numbers(row) and detect_ticket_types(ln):
                            ticket_type = ln.strip()
                            continue



                          row=row[-6:]
                          avg_price   = clean_num(row[1])
                          admits      = clean_num(row[0])
                          comps       = None
                          grs         = clean_num(row[2])
                          vat         = clean_num(row[4])
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

#df=fetch_data("/content/drive/MyDrive/Empire/Python/PDFs/Safeer.pdf","safeer")
#df.to_excel("output.xlsx", index=False)
