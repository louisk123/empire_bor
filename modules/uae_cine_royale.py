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
        datetime.strptime(str(val).strip(), "%d/%m/%Y")
        return True
    except:
        return False


def contains_time(text):
    if not text:
        return False
    pattern = r"\b\d{1,2}\.\d{2}\s?(?:AM|PM|am|pm)\b"
    return bool(re.search(pattern, text))





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


def get_time_screen(ln):
    #print(ln)
    import re
    time_pattern = r"\b\d{1,2}\.\d{2}\s?(?:AM|PM|am|pm)\b"

    m = re.search(time_pattern, ln)
    if not m:
        return None, ln.strip()

    hour = m.group(0)
    screen = ln.replace(hour, "").strip()

    return hour, screen







# -------------------------
# HEADER INFO (Cinema + Weekly)
# -------------------------
def extract_header_info(pdf_path):
    cinema = ""
    movie = ""
    week_tag=""
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text() or ""
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            cinema = lines[0]
        for l in lines:
            L = l.upper()
            fmt = "%d/%m/%Y"
            if L.startswith("FROM :"):
              from_date = l.split()[-2]   # extract 11/09/2025
              d1 = datetime.strptime(from_date, fmt)


            if L.startswith("TO :"):
              to_date = l.split()[-2]     # extract 18/09/202
              d2 = datetime.strptime(to_date, fmt)
              diff = (d2 - d1).days
              week_tag = "Weekly" if diff > 1 else ""

            if "DISTRIBUTOR : EMPIRE" in L:
                movie = l.split(":",1)[1].strip() if ":" in l else l
                movie=movie.replace("DISTRIBUTOR : EMPIRE", "")
                break



    return cinema, movie, week_tag


# -------------------------
# EXTRACT PDF TABLES
# -------------------------
def extract_pdf(pdf_path,exhibitor):

    cinema, current_movie, week_tag = extract_header_info(pdf_path)
    rows = []
    prev_row = None
    show_date   = None
    screen      = None
    show_time   = None
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

                if ("P.O.BOX 0" in ln.upper() or
                    "TEL : FAX:" in ln.upper() or
                    "FILM INCOME REPORT" in ln.upper() or
                    "ADMITS" in ln.upper() or
                    "FROM :" in ln.upper() or
                    "TO :" in ln.upper() or
                    "AMT(INC" in ln.upper() or
                    "IPLAITI" in ln.upper() or
                    "TOTAL OF" in ln.upper() or
                    "COLLECTION CHECK LIST" in ln.upper() or
                    "GRAND TOTAL" in ln.upper() or
                    "DISTRIBUTOR : EMPIRE" in ln.upper()
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
                          
                          if contains_time(ln):
                            show_time, screen =get_time_screen(ln)


                        


                          ticket_type_parts = nbr_row[:-6]      # everything except last 6
                          ticket_type = " ".join(ticket_type_parts)
                          nbr_row = row[-6:] # get last seven columns
                          admits      = clean_num(nbr_row[0])
                          comps       = None
                          grs         = clean_num(nbr_row[1])
                          net         = clean_num(nbr_row[5])

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

#df=fetch_data("/content/drive/MyDrive/Empire/Python/PDFs/cine.pdf","cine royale")
#df.to_excel("output.xlsx", index=False)
