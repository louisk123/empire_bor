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
    if x is None:
        return 0
    x = str(x).replace(",", "").strip()
    if x == "":
        return 0
    try:
        return float(x)
    except:
        return 0

                    # helper to detect numeric money
def is_money(x):
    return re.match(r"^[\d,]+(\.\d+)?$", x)




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
    cinema = lines[0].strip()

    return cinema


# ---------------------------------------
# PAGE-2 EXTRACTION MODULE
# Identifies movie → screen → date → time → format → ticket class rows
# Follows all your detection & skipping rules
# ---------------------------------------
def extract_page2_details(pdf_path):

    page2_rows = []

    with pdfplumber.open(pdf_path) as pdf:

        current_movie = ""
        current_screen = ""
        current_time = ""
        current_date=""
        current_format = "2D"
        ticket_class=""
        its_movie = True

        # Loop from page 1 until last page
        for page_index in range(0, len(pdf.pages)):

            text = pdf.pages[page_index].extract_text() or ""
            lines = text.splitlines()
            lines = lines[5:] #remove first 5 lines

            for line in lines:

                stripped = line.strip()


                skip_phrases = [
                    "QATAR BAHRAIN CINEMA",
                    "EMPIRE INTERNATIONAL",
                    "Screen Total"
                ]


                # break if Distributor Total
                if "Distributor Total" in stripped:
                    break

                if any(p in stripped for p in skip_phrases):
                    continue

  
                #detect Movie
                # detect Movie (first valid line only)
                if its_movie:
                    current_movie = stripped
                    its_movie = False
                    continue


                if "Movie Total" in stripped:
                    its_movie = True
                    continue

                if re.search(r"\b\d{1,2}:\d{2}\s?(am|pm)\b", stripped, re.IGNORECASE):
                    # extract date dd/mm/yyyy
                    date_match = re.search(r"\b\d{2}/\d{2}/\d{4}\b", stripped)
                    current_date = date_match.group() if date_match else ""
                    

                    # extract time
                    time_match = re.search(r"\b\d{1,2}:\d{2}\s?(am|pm)\b", stripped, re.IGNORECASE)
                    current_time = time_match.group() if time_match else ""
                    

                    parts = stripped.split()

                    # defaults
                    admits = 0
                    net = 0
                    gross = 0
                    comps = 0

                    # last part = money → net & gross
                    if is_money(parts[-1]):
                        net = float(parts[-1].replace(",", ""))
                        gross = net
                        

                    # part -1 = admits
                    if parts[-2].isdigit():
                        admits = int(parts[-2])
                        

                    # 4th from last logic for comps
                    if len(parts) >= 4 and parts[3].isdigit():
                      total_admits = int(parts[3])
                      comps =  total_admits - admits

                else:
                    current_screen = stripped
                    continue








                # Append ticket row
                page2_rows.append([
                    current_movie,
                    current_date,
                    current_time,
                    current_screen,
                    current_format,
                    ticket_class,
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


def fetch_data(pdf_path,exhibitor):


    rows_page2 = []

    f = os.path.basename(pdf_path)           # file name only


    # -------- PAGE 1 ----------
    cinema_name = extract_first_page(pdf_path)


    # -------- PAGE 2 ----------
    page2_data = extract_page2_details(pdf_path)
    print(page2_data)

    for idx, r in enumerate(page2_data, start=1):
      new_row = [
          f,                                      # File
          exhibitor,                              # Exhibitor
          cinema_name,                            # Cinema
          None,                              # Week Type
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Extraction Date
      ]
      new_row.extend(r)
      rows_page2.append(new_row)
      #print(idx, rows_page2)



    # -------- EXPORT TO EXCEL --------
    all_rows =  rows_page2
    #df = pd.DataFrame(all_rows, columns=OUTPUT_COLUMNS_PAGE)
    df = pd.DataFrame(all_rows)

    return df

#df = fetch_data("t.pdf", "sds")  # df must be your dataframe

#with pd.ExcelWriter("qbc_single_output.xlsx") as writer:
#    df.to_excel(writer, sheet_name="Extracted Data", index=False)
#    print("Done. Created file: qbc_single_output.xlsx")


