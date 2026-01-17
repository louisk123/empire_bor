import pdfplumber
import pandas as pd
import os
from datetime import datetime
import re



# -------------------------------
# PAGE OUTPUT COLUMNS
# -------------------------------
#OUTPUT_COLUMNS_PAGE = [
#    "File", "Exhibitor","Cinema", "Week Type", "Extraction Date","Movie","Date","Time", "Screen" , "Format", "Ticket Type","Admits","Gross","Net", "Comp" ,"Is Summary",   "Summary Sessions"]


# -------------------------------
# Number cleaner — converts numeric strings into floats
# Handles empty strings safely
# -------------------------------
def clean_num(x):
    x = x.replace(",", "").strip()
    if x == "" or x is None:
        return 0
    try:
        return float(x)
    except:
        return 0





# -------------------------------
# PAGE-1 EXTRACTION
# Reads only the first page
# Extracts the "Summary Table"
# Builds list of movies (movie_list) for page-2 matching
# -------------------------------




def extract_first_page(pdf_path):


    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text() or ""

    # Split into lines
    lines = [l.strip() for l in text.splitlines()]

    # Cinema name = always line 0
    date_line = lines[3] if lines else ""
    date = re.search(r"\b\d{2}/\d{2}/\d{4}\b", date_line).group(0)
    return date


# ---------------------------------------
# PAGE-2 EXTRACTION MODULE
# Identifies movie → screen → date → time → format → ticket class rows
# Follows all your detection & skipping rules
# ---------------------------------------
def extract_page2_details(pdf_path,cinema_map,extract_date,current_date):

    page2_rows = []
    cinema_totals = {f"{v} TOTAL" for v in cinema_map.keys()}


    with pdfplumber.open(pdf_path) as pdf:

        current_cinema=""
        current_movie = ""
        current_time = ""
        current_format = "2D"
        comps=""
        formats=[]


        # Loop from page 1 until last page
        for page_index in range(0, len(pdf.pages)):

            text = pdf.pages[page_index].extract_text() or ""
            lines = text.splitlines()
            lines = lines[1:] #remove first 1 line


            for line in lines:

                stripped = line.strip()
                
                #break is  reached summary line
                if stripped == "Film Summary":
                  break

                is_phrases =[
                    "Head Office",
                    "Distributor Daily Box Office",
                    "Empire",
                    "Cinescape",
                    "Cinescape Total",
                    "Total"

                ]

                has_word = [
                    "Head Office",
                    "Business Date",
                    "Gross Box Office",
                   "Number Admits",
                    "Distributor Daily Box Office",
                    "HOReportFiles",
                    "Vista Entertainment Solutions Ltd",
                    "Cinescape Total"

                ]


                if any(p in stripped for p in has_word):
                    continue

                if stripped in is_phrases:
                    continue
                if any(ct.upper() in stripped.upper() for ct in cinema_totals):
                    continue



                #detect cinema
                key = stripped.strip()
                if key.upper() in cinema_map:
                  current_cinema = key
                  continue

                #Detect movie name and format
                parts = stripped.split()
                if parts and parts[-1].isdigit():  # skip if format i there but empty admits
                  continue
                if len(parts) >= 4 and re.match(r"^KD\d{1,3}(?:,\d{3})*(?:\.\d+)?$", parts[-1]):
                    if parts[0]=="Total":
                      continue
                    # extract values
                    gross = float(parts[-1].replace("KD", "").replace(",", ""))
                    comps = clean_num(parts[-3])
                    admits = clean_num(parts[-4])

                    # everything before that is format
                    current_format = " ".join(parts[:-5]).strip()
                    formats.append(current_format)
          

                else:
                    # no KD amount → treat whole line as movie name
                    current_movie = stripped
                    nbr_screens = 1
                    formats=[]
                    continue

                net    = None





                # Append ticket row
                page2_rows.append([

                    current_cinema,
                    None,
                    extract_date,
                    current_movie,
                    current_date,
                    None,
                    None,
                    current_format,
                    None,
                    admits,
                    gross,
                    net,
                    comps,
                    None,
                    None


                ])

    return page2_rows

# ---------------------------------------
# MAIN LOOP — Processes all PDFs
# Runs PAGE-1 extraction + PAGE-2 extraction
# ---------------------------------------


def fetch_data(pdf_path,exhibitor,cinema_map):


    rows_page2 = []

    f = os.path.basename(pdf_path)           # file name only
    #week_type = get_week_type(f)

    # -------- PAGE 1 ----------
    date_value = extract_first_page(pdf_path)

    extract_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")



    # -------- PAGE 2 ----------
    page2_data = extract_page2_details(pdf_path,cinema_map,extract_date,date_value)
    print(page2_data)


    for idx, r in enumerate(page2_data, start=0):
      new_row = [
          f,                                      # File
          exhibitor,                              # Exhibitor
      ]
      new_row.extend(r)
      rows_page2.append(new_row)



    # -------- EXPORT TO EXCEL --------
    all_rows = rows_page2
    #df = pd.DataFrame(all_rows, columns=OUTPUT_COLUMNS_PAGE)
    df = pd.DataFrame(all_rows)

    return df

'''
cinema_map = {
    "1954 Film House": "1954 FILM HOUSE",
    "Cinescape 360": "360 CINEMA",
    "Cinescape Al Assima": "AL ASSIMA",
    "Cinescape Avenues": "AVENUES",
    "Cinescape Al-Bairaq": "BAIRAQ",
    "Cinescape Khiran": "KHIRAN",
    "Cinescape Al-Kout": "KOUT",
    "Cinescape Warehouse": "WAREHOUSE",
    "Cinescape Al-Fanar": "FANAR",
    "Cinescape Muhallab": "MUHALLAB"
}




df = fetch_data("pp.PDF", "sds",cinema_map)  # df must be your dataframe

with pd.ExcelWriter("vox_single_output.xlsx") as writer:
    df.to_excel(writer, sheet_name="Extracted Data", index=False)
    print("Done. Created file: vox_single_output.xlsx")
'''


