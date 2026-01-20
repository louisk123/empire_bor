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
    cinema = (
    lines[0]
    .replace("Distributors by Film and Ticket Type", "")
    .strip()
)

    # -------------------------------
    # Extract first date DD/MM/YYYY
    # -------------------------------
    date_value = ""

    m = re.search(r"\d{1,2}\s+[A-Za-z]+\s+\d{4}", lines[2])
    if m:
        date_value = datetime.strptime(
            m.group(), "%d %B %Y"
      ).strftime("%d/%m/%Y")

    week_type = "weekly"


    return cinema, date_value,week_type


# ---------------------------------------
# PAGE-2 EXTRACTION MODULE
# Identifies movie → screen → date → time → format → ticket class rows
# Follows all your detection & skipping rules
# ---------------------------------------
def extract_page2_details(pdf_path,current_date):

    page2_rows = []

    with pdfplumber.open(pdf_path) as pdf:

        current_movie = ""
        current_screen = ""
        current_time = ""
        current_format = "2D"
        ticket_class=""


        # Loop from page 1 until last page
        for page_index in range(0, len(pdf.pages)):

            text = pdf.pages[page_index].extract_text() or ""
            lines = text.splitlines()
            lines = lines[5:] #remove first 5 lines


            for line in lines:

                stripped = line.strip()


                skip_phrases = [
                    "Distributors by Film and Ticket Type",
                    "Vista Entertainment Solutions Ltd",
                    "REPORT DATE RANGE",
                    "Empire Film Distribution",
                    "GROSS TOTAL",
                    "Empire Film Distribution total"
                ]


                if any(p in stripped for p in skip_phrases):
                    continue

                parts = stripped.split()

                if len(parts) >= 6 and re.match(r"^[\d,]+(\.\d+)?$", parts[-1]):
                  gross = clean_num(parts[-1])
                  net = clean_num(parts[-3])
                  admits = clean_num(parts[-4])
                  current_movie = " ".join(parts[:-6])

                else:
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
                    0,  #"in case price is 0 the put admists in comps and put admits=0
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
    page2_data = extract_page2_details(pdf_path,date_value)

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
    all_rows =  rows_page2
    #df = pd.DataFrame(all_rows, columns=OUTPUT_COLUMNS_PAGE)
    df = pd.DataFrame(all_rows)

    return df

#df = fetch_data("t.pdf", "sds")  # df must be your dataframe

#with pd.ExcelWriter("ozone_single_output.xlsx") as writer:
#    df.to_excel(writer, sheet_name="Extracted Data", index=False)
#    print("Done. Created file: ozone_single_output.xlsx")


