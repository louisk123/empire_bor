import pdfplumber
import pandas as pd
import os
from datetime import datetime
import re



#FORMATS

formats = ["2D", "3D", "4D", "IMAX 3D", "IMAX", "ATMOS", "MX4D", "DOLBY", "4DX",
           "3D ARABIC", "2D ARABIC", "2D FRENCH", "3D FRENCH", "4DX 3D",
           "MAX 2D", "ADJ 2D", "ADJ 3D", "ATMOS 3D", "ADJ 2D AR", "ADJ 4DX",
           "SCREEN X", "MAX 3D", "IMAX LASER 3D", "MX4D 3D", "IMAX LASER 2D",
           "4D E MOTION", "4D E MOTION 3D", "2D JAPANESE", "ICE", "SPHERA",
           "4DX-2D", "4DX-3D", "4DX-4D","IMAX-2D","IMAX-2"
           ]


# -------------------------------
# PAGE OUTPUT COLUMNS
# -------------------------------
OUTPUT_COLUMNS_PAGE = [
    "File", "Exhibitor","Cinema", "Week Type", "Extraction Date","Movie","Date","Time", "Screen" , "Format", "Ticket Type","Admits","Gross","Net", "Comp" ,"Is Summary",   "Summary Sessions"]


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

    week_type=""
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text() or ""

    # Split into lines
    lines = [l.strip() for l in text.splitlines()]

    # Cinema name = always line 0
    cinema = lines[0] if lines else ""

    # -------------------------------
    # Extract first date DD/MM/YYYY
    # -------------------------------
    date_value = ""
    date_pattern = re.compile(r"\b\d{2}/\d{2}/\d{2,4}\b")


    dates = re.findall(r"\d{1,2}/\d{1,2}/\d{2,4}", "\n".join(lines[:10]))
    date_value = dates[0] if dates else ""
    if len(dates) >= 2:
        d1 = datetime.strptime(dates[0], "%d/%m/%Y")
        date_value=dates[0]
        d2 = datetime.strptime(dates[1], "%d/%m/%Y")
        week_type = "weekly" if (d2 - d1).days > 1 else ""


    return cinema, date_value,week_type


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
        current_date = ""
        current_time = ""
        current_format = "2D"


        # Loop from page 1 until last page
        for page_index in range(0, len(pdf.pages)):

            text = pdf.pages[page_index].extract_text() or ""
            lines = text.splitlines()
            lines = lines[1:] #remove first 1 line

            skip=0
            for line in lines:
 
                if skip==1:
                  if stripped.replace(" ", "").replace(".", "").isdigit():
                    skip = 0
                  continue

                stripped = line.strip()
                if stripped == "Totals":
                    skip=1
                    continue
                

                skip_phrases = [
                    "Distributors Report by Film",
                    "Ticket Type",
                    "Distributors Report by Film",
                    "C:\VISTA\ReportFiles",
                    "Total for Film this Screen",
                    "Day Total",
                    "Movie Format",
                    "Split Movie Format",
                    "Ticket Detail Level",
                    "Detailed Distributors Report",
                    "Vista Entertainment Solutions",
                    "Empire(",
                    "Avg Ticket Price",
                    "EMPIRE ENTERTAINMENT",
                    "Split Movie Format",
                    "Ticket Prices Admits",
                ]


                if any(p in stripped for p in skip_phrases):
                    continue

                # Skip purely numeric lines
                if stripped.replace(" ", "").isdigit():
                    continue

                #Detect movie name and format
                mo = re.search(r"Film\s*:\s*([A-Z0-9 ()\-:'&]+?)\s*Format\s*:\s*([A-Z0-9]+)",stripped,re.IGNORECASE)

                if mo:
                    current_movie = mo.group(1).strip()
                    fmt = mo.group(2).strip().upper()
                    current_format = "2D" if fmt == "DEFAULT" else fmt
                    continue
                
                #replace Days of week with ""
                stripped = re.sub(r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|After Midnight)\b", "", stripped, flags=re.IGNORECASE).strip()
               

                m = re.search(r"\b(\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2}-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{2,4})\b",
                    stripped,
                  re.IGNORECASE
                )
                if m:
                    current_date = m.group(0)
                    continue

                parts = stripped.split()


                # Check if last 5 tokens are numeric fields
                numeric_tail = parts[-5:]

                # Must contain exactly 5 tokens
                if len(numeric_tail) != 5:
                    continue
                #if all zeros skip
                if all(t in ["0", "0.0", "0.00"] or t == 0 for t in numeric_tail):
                    continue


                 #ticket class
                ticket_class=parts[:-5]
                ticket_class=" ".join(ticket_class).strip()


                # Validate each of the 5 numeric fields
                is_numeric_tail = True
                for x in numeric_tail:
                    cleaned = x.replace(",", "")
                    if cleaned.replace(".", "").isdigit():
                        continue
                    is_numeric_tail = False
                    break

                if not is_numeric_tail:
                    continue

                admits, netprice, net, grossprice, gross = numeric_tail



                admits = clean_num(admits)
                gross  = clean_num(gross)
                net    = clean_num(net)
                price = clean_num(grossprice)
               



                # Append ticket row
                page2_rows.append([
                    current_movie,
                    current_date,
                    current_time,
                    current_screen,
                    current_format,
                    ticket_class,
                    0 if price == 0 else admits,
                    gross,
                    net,
                    admits if price == 0 else 0,  #"in case price is 0 the put admists in comps and put admits=0
                    None,
                    None


                ])

    return page2_rows

# ---------------------------------------
# MAIN LOOP — Processes all PDFs
# Runs PAGE-1 extraction + PAGE-2 extraction
# ---------------------------------------


def fetch_data(pdf_path,exhibitor):

    rows_page1 = []
    rows_page2 = []

    f = os.path.basename(pdf_path)           # file name only
    #week_type = get_week_type(f)

    # -------- PAGE 1 ----------
    cinema_name, date_value,week_type = extract_first_page(pdf_path)


    # -------- PAGE 2 ----------
    page2_data = extract_page2_details(pdf_path)

    for idx, r in enumerate(page2_data, start=1):
      new_row = [
          f,                                      # File
          exhibitor,                              # Exhibitor
          cinema_name,                            # Cinema
          week_type,                              # Week Type
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Extraction Date
      ]
      new_row.extend(r)
      rows_page2.append(new_row)
      #print(idx, rows_page2)



    # -------- EXPORT TO EXCEL --------
    all_rows = rows_page1 + rows_page2
    #df = pd.DataFrame(all_rows, columns=OUTPUT_COLUMNS_PAGE)
    df = pd.DataFrame(all_rows)

    return df

#df = fetch_data("pp.PDF", "sds")  # df must be your dataframe

#with pd.ExcelWriter("vox_single_output.xlsx") as writer:
#    df.to_excel(writer, sheet_name="Extracted Data", index=False)
#    print("Done. Created file: vox_single_output.xlsx")


