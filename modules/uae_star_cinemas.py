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
        datetime.strptime(str(val).strip(), "%Y-%m-%d")
        return True
    except:
        return False


def contains_time(text):
    if not text:
        return False
    return bool(re.search(r"\b\d{1,2}:\d{2}\b", text))

import re

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



def get_time_screen(row):
    hour = None
    hour_idx = None
    date_idx = 0

    # detect date & hour & their positions
    for i, cell in enumerate(row):
        if i==0:
          continue

        cell_str = str(cell).strip()

        # detect HH:MM
        if re.match(r"^\d{1,2}:\d{2}$", cell_str):
            hour = cell_str
            hour_idx = i
            continue

    # extract ticket class (between date and hour)
    screen = ""
    if hour_idx is not None:
        if hour_idx > date_idx:
            mid = row[ 1: hour_idx]
            screen = " ".join(mid).strip()

    return hour, screen






# -------------------------
# HEADER INFO (Cinema + Weekly)
# -------------------------
def extract_header_info(pdf_path):
    cinema = ""
    week_tag = ""

    with pdfplumber.open(pdf_path) as pdf:
        lines = pdf.pages[0].extract_text().splitlines()

        # CINEMA NAME = first non-empty line
        for ln in lines:
            if ln.strip():
                cinema = ln.strip()
                break

        # WEEKLY DETECTION
        for ln in lines:
            L = ln.upper()
            if "SCREENING PERIOD" in L and "TO" in L:
                parts = ln.split()
                # Example: Screening Period 2025-09-11 TO 2025-09-17
                d1 = datetime.strptime(parts[-3], "%Y-%m-%d")
                d2 = datetime.strptime(parts[-1], "%Y-%m-%d")
                week_tag = "Weekly" if (d2 - d1).days > 0 else ""
                break

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

                if ("DISTRIBUTOR REPORT" in ln.upper() or
                    "SCREENING PERIOD" in ln.upper() or
                    "TKT PRICE" in ln.upper() or
                    "ADMITS" in ln.upper() or
                    "TOTAL" in ln.upper() or
                    "DISTRIBUTOR NAME" in ln.upper() or
                    "GENERATED ON" in ln.upper() or
                    ln=="-" or
                    ln==cinema
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
                            temp_show_time, temp_screen= get_time_screen(row)

                          else:

                            if prev_line and ("TKT PRICE" in prev_line.upper() or "MOVIE TOTAL" in prev_line.upper()):
                              if not last_seven_are_numbers(row):
                                current_movie=ln
                                prev_row = fake_table[0]
                                prev_line=ln

                                continue

                          if temp_show_time not in ["", None]: # if there is date, scen and show time skip tehse columns to unify
                              nbr_row = row[3:]

                          #print(nbr_row)
                          show_date   = row[0] if is_date(row[0]) else show_date
                          screen      = temp_screen if temp_screen not in ["", None] else screen
                          show_time   = temp_show_time if temp_show_time not in ["", None] else show_time


                          ticket_type_parts = nbr_row[:-7]      # everything except last 7
                          ticket_type = " ".join(ticket_type_parts)
                          ticket_type=ticket_type.replace(show_time,"")
                          nbr_row = row[-7:] # get last seven columns
                          avg_price   = clean_num(nbr_row[0])
                          admits      = clean_num(nbr_row[1])
                          comps       = clean_num(nbr_row[2])
                          grs         = clean_num(nbr_row[3])
                          vat         = clean_num(nbr_row[4])
                          mtax        = clean_num(nbr_row[5])
                          net         = clean_num(nbr_row[6])

                          #print(f"{show_date}, {screen}, {show_time}, {admits}, {grs}")
                          movie_format = "2D"
                          if "DOLBY" in ticket_type.upper():
                              movie_format = "DOLBY"

                          rows.append([
                              pdf_path,
                              exhibitor,
                              cinema,
                              week_tag,
                              datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                              current_movie,
                              show_date,
                              show_time,
                              screen,
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

#df=fetch_data("/content/drive/MyDrive/Empire/Python/PDFs/Star Wahda.pdf","star")
#df.to_excel("output.xlsx", index=False)
