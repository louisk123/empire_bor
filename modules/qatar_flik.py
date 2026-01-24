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




def is_number(x):
    return x.replace(",", "").replace(".", "").isdigit()

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
    cinema = lines[3].replace("Selection", "").strip()

    # extract dates
    line = lines[2]

    found = re.findall(r"\d{4}-\d{2}-\d{2}", line)

    if len(found) == 2:
        start = datetime.strptime(found[0], "%Y-%m-%d")
        end = datetime.strptime(found[1], "%Y-%m-%d")
        weekly = 1 if (end - start).days > 2 else None
    else:
        weekly = None


    return cinema, weekly


# ---------------------------------------
# PAGE-2 EXTRACTION MODULE
# Identifies movie → screen → date → time → format → ticket class rows
# Follows all your detection & skipping rules
# ---------------------------------------
def extract_page2_details(pdf_path):

    page2_rows = []

    with pdfplumber.open(pdf_path) as pdf:

        current_movie = ""
        current_time = ""
        current_date=""
        current_format = "2D"
        ticket_class=""
        screen_type = None

  
        # Loop from page 1 until last page
        for page_index in range(0, len(pdf.pages)):

            text = pdf.pages[page_index].extract_text() or ""
            lines = text.splitlines()
            lines = lines[6:] #remove first 6 lines

            for line in lines:
                admits = None
                gross = None
                net = None
                stripped = line.strip()

                skip_phrases = [
                    "Ticket Types Per Title",
                    "Created 20",
                    "Screen Total"
                ]



                if any(p in stripped for p in skip_phrases):
                    continue
                
                parts = stripped.split()
                date_idx=None

                #skip if has total
                if (
                      parts
                      and parts[0].lower() == "total"
                      and parts[-1].replace(",", "").replace(".", "").isdigit()
                  ):
                      continue
                
                #skip if total
                if len(parts) == 2 and all(is_number(p) for p in parts):
                    continue

    
                date_idx = next(
                (i for i, p in enumerate(parts) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p)),
                None
                )

                if date_idx is not None:
                    current_date = parts[date_idx]   # keep original format
                    movie_parts = parts[:date_idx]

                    # detect format
                    for p in movie_parts:
                        m = re.search(r"(2D|3D|4D|4DX)", p, re.IGNORECASE)
                        if m:
                            current_format = m.group(1).upper()

                    # clean movie title
                    current_movie = " ".join(movie_parts)
                    current_movie = re.sub(
                        r"\(?\b(2D|3D|4D|4DX)\b(\s+(EN|AR|JA|HI))?\)?",
                        "",
                        current_movie,
                        flags=re.IGNORECASE
                    )
                    current_movie = re.sub(r"\s+", " ", current_movie).strip()
                    

                # check if line has time like 21:10
                for i, p in enumerate(parts):
                    if re.fullmatch(r"\d{2}:\d{2}", p):
                        current_time = p

                        # gross = last part
                        gross = clean_num(parts[-1])
                        net=gross

                        # admits = third from last
                        admits = clean_num(parts[-3])

                        # screen type = parts after time up to last 3
                        screen_type = " ".join(parts[i+1:-3]).strip()
     
                if len(parts) == 3 and all(is_number(p) for p in parts):
                    gross = clean_num(parts[-1])
                    admits = clean_num(parts[-3])
                    net=gross



                # Append ticket row
                page2_rows.append([
                    current_movie,
                    current_date,
                    current_time,
                    screen_type,
                    current_format,
                    ticket_class,
                    admits,
                    gross,
                    net,
                    None,
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
    cinema_name, weekly = extract_first_page(pdf_path)


    # -------- PAGE 2 ----------
    page2_data = extract_page2_details(pdf_path)
    print(page2_data)

    for idx, r in enumerate(page2_data, start=1):
      new_row = [
          f,                                      # File
          exhibitor,                              # Exhibitor
          cinema_name,                            # Cinema
          weekly,                              # Week Type
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

#df = fetch_data("p.pdf", "sds")  # df must be your dataframe

#with pd.ExcelWriter("flik_single_output.xlsx") as writer:
#    df.to_excel(writer, sheet_name="Extracted Data", index=False)
#    print("Done. Created file: flik_single_output.xlsx")


