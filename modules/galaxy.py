import pdfplumber
import pandas as pd
import os
from datetime import datetime
import re

screens =["Screen 1","Screen 2","Screen 3","Screen 4","Screen 5","Screen 6","Screen 7","Screen 8","Screen 9","Screen 10","Screen 11","Screen 12","Screen 13","Screen 14","Screen 15"]


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

def last_seven_are_numbers(row):
    if len(row) < 7:
        return False

    last7 = row[-7:]

    for x in last7:
        if x is None:
            return False
        s = str(x).replace(",", "").strip()
        if not s.replace(".", "", 1).isdigit():  # allow one decimal
            return False

    return True





def detect_screen_and_movie(line):
    line_upper = line.upper()
    for scr in screens:
        scr=scr.upper()
        if scr in line_upper:
            screen = scr
            movie = line_upper.replace(scr, "").strip()
            return screen, movie
    return None, None

def is_only_aed_and_numbers(text):
    if not text:
        return False

    # remove spaces to simplify
    t = text.strip()

    # must contain AED
    if "AED" not in t.upper():
        return False

    # allow: A E D digits dot comma space
    cleaned = re.sub(r"[AEDaed0-9.,\s]", "", t)

    # if ANY other character remains, reject
    return cleaned == ""



# -------------------------
# HEADER INFO (Cinema + Weekly)
# -------------------------
def extract_header_info(pdf_path):
    cinema = ""
    week_tag = ""

    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        lines = first_page.extract_text().splitlines() if first_page.extract_text() else []

        '''
        # CINEMA NAME = first non-empty line
        for ln in lines:
            if ln.strip():
                cinema = ln.strip()
                break


        # WEEKLY DETECTION
        for ln in lines:
            L = ln.upper()
            if "Ticket Detail Level" in L:
                parts = ln.split()
                # Example: Screening Period 2025-09-11 TO 2025-09-17
                d1 = datetime.strptime(parts[-3], "%d-%m-%Y")
                d2 = datetime.strptime(parts[-8], "%d-%m-%Y")
                week_tag = "weekly" if (d2 - d1).days > 1 else ""
                break

                Weekly Distributor Report
        '''
        cinema = lines[0] if len(lines) > 0 else ""
        if len(lines) > 1 and "weekly distributor report".lower() in lines[1].lower():
          week_tag = "weekly"

    return cinema, week_tag


# -------------------------
# EXTRACT PDF TABLES
# -------------------------
def extract_pdf(pdf_path,exhibitor):

    cinema, week_tag = extract_header_info(pdf_path)
    rows = []

    current_movie = ""
    prev_row = None
    show_date   = None
    screen      = None
    show_time   = None
    prev_line= None # Initialize prev_line
    previous_row = None # Initialize previous_row

    with pdfplumber.open(pdf_path) as pdf:
        for pidx, page in enumerate(pdf.pages, start=1):
            lines = page.extract_text().splitlines() if page.extract_text() else []
            # skip first rows depending on page
            if pidx == 1:
              skip_n = 6
            else:
              skip_n = 4

            lines = lines[skip_n:]   # remove first N lines

            fake_table = []
            for ln in lines:
                ln = ln.strip()
                if not ln:
                    continue
                # skip garbage / header lines

                # split respecting multiple spaces and keep empty slots
                parts = ln.replace("\t", " ").split(" ")
                parts = [p for p in parts if p != ""]  # collapse extra spaces
                fake_table=[]
                fake_table.append(parts)

                if ("TICKETTYPE" in ln.upper() or
                    "WEEKLY DISTRIBUTOR REPORT" in ln.upper() or
                    "GRAND TOTAL" in ln.upper() or
                    "DAY TOTAL" in ln.upper() or
                    "TOTAL FOR FILM THIS SCREEN" in ln.upper() or
                    ln==cinema or
                    date_and_time_detected(ln)==True or
                    is_only_aed_and_numbers(ln)==True
                ):
                      prev_line=ln
                      prev_row = fake_table[0]
                      continue

                # feed the rest of your script with fake rows
                for row in fake_table:
                        if not row:
                            prev_row = row
                            prev_line=ln
                            continue

                        # ----------------------------------
                        # Extract ROW DATA
                        # ----------------------------------

                        try:
                          temp_show_time = None
                          temp_screen= None
                          nbr_row= row
                          if is_date(row[0]):
                            show_date = row[0]
                            continue

                          if contains_time(row[0]):
                            show_time= row[0]
                            continue

                          #detect movie and screen
                          screen, movie_name = detect_screen_and_movie(ln)


                          if screen:
                            current_movie = movie_name
                            current_screen = screen
                            continue


                          ticket_type=" ".join(row[1:-7])
                          row=row[-7:]
                          avg_price   = clean_num(row[0].replace("AED",""))
                          admits      = clean_num(row[2])
                          comps       = clean_num(row[1])
                          grs         = clean_num(row[3].replace("AED",""))
                          vat         = clean_num(row[4].replace("AED",""))
                          mtax        = clean_num(row[5].replace("AED",""))
                          net         = clean_num(row[6].replace("AED",""))

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

#df=fetch_data("pp1.pdf","galaxy")
#df.to_excel("output.xlsx", index=False)
