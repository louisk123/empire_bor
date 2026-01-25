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
        return 0.0
    s = str(x).strip()
    if s == "":
        return 0.0
    return float(s.replace(",", "."))


#extrac the comps only and injetc them later on in any of the itmings

def extract_comps_array(pdf_path):
    comps_array = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()

            for table in tables:
                for row in table:
                    # normalize row
                    if not row:
                        continue

                    # screen summary row:
                    # first two columns are None
                    if row[0] is None and row[1] is None:
                        comp_value = row[3]

                        if comp_value and str(comp_value).strip().isdigit():
                            comps_array.append(int(comp_value))
                        else:
                            comps_array.append(0)

                        break  # only first summary row per table

    return comps_array





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
    comps_arr = extract_comps_array(pdf_path)
    new_screen=True
    new_screen_line=0


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
            lines = lines[1:] #remove first 1 lines

            for line in lines:

                stripped = line.strip()


                skip_phrases = [
                    "Daily Collection",
                    "EMPIRE INTERNATIONAL",
                    "Screen Total",
                    "Amt.(inc.VAT)",
                    "Net Amount"

                ]


                # break if Distributor Total
                if "Distributor Total" in stripped:
                    #print("Distributor Total")
                    break

                if any(p in stripped for p in skip_phrases):
                    #print("skip")
                    continue
                
                if re.search(r"\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\s*,\s*[A-Za-z]+\b", line):  #skip if has date format: eg 15 January 2026 , Thursday
                    continue


                #detect Movie
                # detect Movie (first valid line only)
                if its_movie:
                    current_movie = stripped
                    #print("current_movie:",current_movie)
                    its_movie = False
                    continue


                if "Movie Total" in stripped:
                    its_movie = True
                    #print("new movie will commence")
                    continue

                if re.search(r"\b\d{1,2}:\d{2}\s?(am|pm)\b", stripped, re.IGNORECASE):
                    # extract date dd/mm/yyyy
                    date_match = re.search(r"\b\d{2}/\d{2}/\d{4}\b", stripped)
                    current_date = date_match.group() if date_match else ""



                    # extract time
                    time_match = re.search(r"\b\d{1,2}:\d{2}\s?(am|pm)\b", stripped, re.IGNORECASE)
                    current_time = time_match.group() if time_match else ""
                    #print(current_date,current_time)


                    parts = stripped.split()

                    # defaults
                    admits = 0
                    net = 0
                    gross = 0
                    
                    #attach the cmops to teh first time
                    if new_screen==True:
                      comps = comps_arr[new_screen_line] if new_screen_line < len(comps_arr) else 0
                      new_screen_line=new_screen_line+1
                      new_screen=False
                    else:
                      comps = 0
                    
                    

                    if len(parts) == 3:  #show without admissions
                        #print("Show iwhtout addmission")
                        admits = 0
                        gross = 0
                        net = 0

                    else:

                        # CASE 1: pure comps (exactly 5 parts, last 2 equal digits)
                        if (
                            len(parts) == 5
                            and parts[-1].isdigit()
                            and parts[-2].isdigit()
                            and parts[-1] == parts[-2]
                        ):
                            admits = clean_num(parts[-1]) # it will be eliminatted later on
                            gross = 0
                            net=0
                            #do not consider comps are they are beign considered in the total

                        # CASE 2: normal admits calculation
                        elif len(parts) >= 5 and parts[3].isdigit():
                            #print("normal row")
                            net=clean_num(parts[-1])
                            gross=clean_num(parts[-4])


                            admits = clean_num(int(parts[3]))


                else:
                    current_screen = stripped
                    new_screen=True
                    #print("current_screen",current_screen)
                    continue


                admits = admits - comps if comps is not None else admits

                #print("rows added")

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

#with pd.ExcelWriter("bcc_single_output.xlsx") as writer:
#    df.to_excel(writer, sheet_name="Extracted Data", index=False)
#    print("Done. Created file: bcc_single_output.xlsx")


