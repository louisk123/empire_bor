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


def clean_movie_title(text):
    return re.sub(r"\bweek\b.*", "", text, flags=re.IGNORECASE).strip()

def parse_showtime_line(ln):
    ln_upper = ln.upper()


    # extract date (dd-mm-yyyy)
    date_match = re.search(r"\d{2}-\d{2}-\d{4}", ln)
    show_date = date_match.group() if date_match else None

    # extract time (11:00 am / 11:00am / 11:00 AM)
    time_match = re.search(r"\b\d{1,2}:\d{2}\s*(AM|PM)\b", ln, re.IGNORECASE)
    if time_match:
        show_time = time_match.group().replace(" ", "").upper()
    else:
        show_time = None

    # extract screen after "@"
    screen_match = re.search(r"@\s*(.*)$", ln)
    current_screen = screen_match.group(1).strip() if screen_match else None

    return show_date, show_time, current_screen


# -------------------------
# HEADER INFO (Cinema + Weekly)
# -------------------------
def extract_header_info(pdf_path):
    cinema=""
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text() or ""
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            cinema = lines[0]
    week_tag = "weekly"

    return cinema, week_tag


# -------------------------
# EXTRACT PDF TABLES
# -------------------------
def extract_pdf(pdf_path,exhibitor):

    cinema, week_tag   = extract_header_info(pdf_path)
    rows = []

    current_movie = None
    current_screen= None
    ticket_type = None
    show_date= None
    show_time= None


    with pdfplumber.open(pdf_path) as pdf:
        start = None
        for pidx, page in enumerate(pdf.pages, start=1):
            lines = page.extract_text().splitlines() if page.extract_text() else []
            fake_table = []
            for idx, ln in enumerate(lines):
                ln = ln.strip()
                if not ln:
                    continue
                # skip garbage / header lines

                if pidx==1 and idx<5:
                  continue

                #detect movie
                if pidx==1 and idx==5:
                  current_movie=ln.strip()




                # split respecting multiple spaces and keep empty slots
                parts = ln.replace("\t", " ").split(" ")
                parts = [p for p in parts if p != ""]  # collapse extra spaces
                #print(parts)
                fake_table=[]
                fake_table.append(parts)

                if "UP TO DATE STATEMENT" in ln.upper():
                  return rows

                if ("AL MARIAH MALL" in ln.upper() or
                    "DAILY COLLECTION REPORT" in ln.upper() or
                    "DETAILED DISTRIBUTORS REPORT" in ln.upper() or
                    "EMPIRE CINEMAS" in ln.upper() or
                    "NO. OF SESSIONS" in ln.upper() or
                    "ADMIN RATE" in ln.upper() or
                    "DIST SHARE" in ln.upper() or
                    "DAY TOTAL" in ln.upper() or
                    "GRAND TOTAL" in ln.upper() or
                    "MOVIECLICKS" in ln.upper() #or
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

                          if start== None and row[0]=="Total":
                            start= True
                            continue

                          if start==None:
                            continue


                          #skip total
                          value = row[1].replace(",", "").strip()


                          if len(row) > 2 and row[0].strip().upper() == "TOTAL" and value.replace(".", "", 1).isdigit():
                              continue


                          # detect "SHOW TIME" DAT and CURRENT SCREEN
                          if "Show Time"  in ln:
                            show_date, show_time, current_screen = parse_showtime_line(ln)
                            continue

                          ticket_type =  " ".join(row[:-8]).strip()
                          row=row[-6:]
                          avg_price   = clean_num(row[0])
                          admits      = clean_num(row[1])
                          comps       = None
                          grs         = clean_num(row[2])
                          vat         = clean_num(row[4])
                          mtax        = clean_num(row[5])
                          net         = clean_num(row[3])

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

#df=fetch_data("/content/drive/MyDrive/Empire/Python/PDFs/truth_weekly.pdf","truth weekly")
#df.to_excel("output.xlsx", index=False)