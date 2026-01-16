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
           "2D HINDI", "2D TAMIL", "XPERIENCE", "2D TELUGU", "2D MALAYALAM",
           "4DX-2D","4DX-3D", "4DX-4D","IMAX-2D","IMAX-2"
           ]


# -------------------------------
# PAGE OUTPUT COLUMNS
# -------------------------------
OUTPUT_COLUMNS_PAGE = [
    "File", "Exhibitor","Cinema", "Week Type", "Extraction Date","Movie","Date","Time", "Screen" , "Format", "Ticket Type","Admits","Gross","Net", "Comp" ,"Is Summary",   "Summary Sessions"]


# chekc if screen is MAX then format should be MAX 2D or MAX 3D if not already detected
def build_max_label(var1, var2):
    # check if var1 starts with MAX (optionally followed by space and digits)
    if re.match(r'^MAX\s*\d*$', var1, re.IGNORECASE):
        if var2.upper() in ['2D', '3D']:
            print(f"MAX {var2.upper()}")
            return f"MAX {var2.upper()}"
    return var2


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

# detect if weekly file
def get_week_type(filename):
    name = filename.lower()
    if "weekly" in name:
        return "weekly"
    


    return ""



# normalize Date
def normalize_date(d):
    a, b, c = d.split("/")

    # CASE 1 → DD/MM/YY   (year = 2 digits)
    if len(c) == 2:
        day = a
        month = b
        year = "20" + c
        return f"{day.zfill(2)}/{month.zfill(2)}/{year}"

    # CASE 2 → MM/DD/YYYY (year = 4 digits)
    day = b     # second number
    month = a   # first number
    year = c
    return f"{day.zfill(2)}/{month.zfill(2)}/{year}"


def remove_time_and_format(parts, time_token, movie_format):
    parts = parts[:]
    fmt_tokens = movie_format.split()

    # remove time only if it is the first item
    if parts and parts[0] == time_token:
        parts.pop(0)

    # remove movie format only if it starts at index 0
    fmt_len = len(fmt_tokens)
    if parts[:fmt_len] == fmt_tokens:
        parts = parts[fmt_len:]

    return parts


# -------------------------------
# PAGE-1 EXTRACTION
# Reads only the first page
# Extracts the "Summary Table"
# Builds list of movies (movie_list) for page-2 matching
# -------------------------------

# Identify a real data row by checking if the last 4–6 tokens look numeric
def is_data_row(tokens):
    tail = tokens[-6:]
    numeric_count = sum(tok.replace(",", "").replace(".", "").isdigit() for tok in tail)
    return numeric_count >= 2    # real data rows ALWAYS have multiple numeric tail tokens


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

    '''
    for l in lines[:20]:
        m = date_pattern.search(l)
        if m:
            date_value = m.group(0)
            break
    '''

    #dates = re.findall(r"\d{1,2}/\d{1,2}/\d{2,4}", "\n".join(lines[:10]))
    dates = re.findall(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", "\n".join(lines[:10]))

    date_value = dates[0].replace("-", "/") if dates else ""
    if len(dates) >= 2:
        d1 = datetime.strptime(dates[0].replace("-", "/"), "%d/%m/%Y")
        date_value=dates[0].replace("-", "/")
        d2 = datetime.strptime(dates[1].replace("-", "/"), "%d/%m/%Y")
        week_type = "weekly" if (d2 - d1).days > 1 else ""

    # -------------------------------
    # Locate the summary-table region
    # -------------------------------
    try:
        start = next(i for i, l in enumerate(lines) if "Total Box Office" in l)
        end   = next(i for i, l in enumerate(lines) if "Distributor Total" in l)
    except StopIteration:
        return cinema, date_value, [], [] ,[]

    # Detect if Movie Format column exists
    header_line = lines[start+1] if start+1 < len(lines) else ""
    has_format_column = "Movie Format" in header_line

    # Extract table lines
    table_lines = lines[start+2 : end]

    results = []
    movie_names = []

    i = 0

    # -------------------------------
    # Parse each movie summary row
    # -------------------------------
    while i < len(table_lines):

        line = table_lines[i]

        tokens = line.split()

        # -------------- CASE: no Movie Format column (7 tokens)
        if not has_format_column:
            while len(tokens) < 7:
                tokens.append("")

            movie = " ".join(tokens[:-6]).strip()
            movie_format = "2D"  # forced
            sessions     = clean_num(tokens[-6])
            comp         = clean_num(tokens[-5])
            admits       = clean_num(tokens[-4])
            gross        = clean_num(tokens[-3])
            tax          = clean_num(tokens[-2])
            net          = clean_num(tokens[-1])

        # -------------- CASE: Movie Format column exists (8 tokens)
        else:

            while len(tokens) < 8:
                tokens.append("")


            # try to match last 1 to 4 tokens as format
            movie_format = ""
            the_split = tokens[:-6]
            movie_name_tokens = the_split[:]

            for n in range(4, 0, -1):  # try length 4, 3, 2, 1
                if len(the_split) >= n:
                    candidate = " ".join(the_split[-n:])
                    if candidate.upper() in formats:
                        movie_format = candidate
                        movie_name_tokens = the_split[:-n]
                        break

            movie = " ".join(movie_name_tokens).strip()


            sessions     = clean_num(tokens[-6])
            comp         = clean_num(tokens[-5])
            admits       = clean_num(tokens[-4])
            gross        = clean_num(tokens[-3])
            tax          = clean_num(tokens[-2])
            net          = clean_num(tokens[-1])

        # --------------------------------------
        # Merge continuation lines SAFE + CLEAN
        # --------------------------------------
        j = i + 1
        while j < len(table_lines):

            nxt = table_lines[j]
            nxt_tokens = nxt.split()

            # If NOT a data row → continuation of movie title
            if not is_data_row(nxt_tokens):
                movie += " " + " ".join(nxt_tokens)
                j += 1
                continue

            # If real data → stop continuation
            break

        # Store movie name
        movie_names.append(movie)

        # Store result row
        results.append([
            movie, date_value,None,None, movie_format,None,admits, gross, net,comp, 1 , sessions
        ])

        i = j

    return cinema, date_value, results, movie_names,week_type


# ---------------------------------------
# PAGE-2 EXTRACTION MODULE
# Identifies movie → screen → date → time → format → ticket class rows
# Follows all your detection & skipping rules
# ---------------------------------------
def extract_page2_details(pdf_path, movie_list):

    page2_rows = []

    with pdfplumber.open(pdf_path) as pdf:

        current_movie = ""
        current_screen = ""
        current_date = ""
        current_time = ""
        current_format = "2D"


        # Loop from page 2 until last page
        for page_index in range(1, len(pdf.pages)):
            #print("Page 2 started")

            text = pdf.pages[page_index].extract_text() or ""
            lines = text.splitlines()
            #lines = lines[5:] #remove first 5 lines


            skip=1
            for line in lines:
                #print(line)
                #if "Split Movie Format".lower() in line.lower():
                #  skip=0
                #  continue

                #if skip ==1:
                #  continue


                stripped = line.strip()

                skip_phrases = [
                    "Total for Film this Screen",
                    "Day Total",
                    "Movie Format",
                    "Split Movie Format",
                    "Ticket Detail Level",
                    "Detailed Distributors Report",
                    "Vista Entertainment Solutions",
                    "Empire(",
                    "Avg Ticket Price",
                    "Empire International",
                    "EMPIRE ENTERTAINMENT",
                    "Empire International Gulf",
                    "Split Movie Format",
                    "Ticket Prices Admits"
                ]

                if line.strip() == "Empire":
                  continue


                if any(p in stripped for p in skip_phrases):
                    #print("skip")
                    continue

                # Skip purely numeric lines
                if stripped.replace(" ", "").isdigit():
                    #print("skip")
                    continue

                # Date detection
                #print("Date Detection Stated")
                #m = re.search(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b", stripped)
                m = re.search(r"\b(\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2}-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{2,4})\b",
                    stripped,
                  re.IGNORECASE
                )
                if m:
                    #current_date = normalize_date(m.group(0))
                    current_date = m.group(0) 
                    #print("Date:")
                    #print(current_date)
                    continue

                parts = stripped.split()

                # Movie detection (line contains the movie name)
                #print("Movie Deteciton Stareted")
                for mv in movie_list:
                    if mv in stripped:
                        current_movie = mv
                        #print(current_movie)
                        current_screen = stripped.replace(mv, "").strip()
                        ticket_class=""  #reset ticket_class
                        current_format= "2D" #reset current formal
                        #skip=2 #skips the next 2 linese after the movei title
                        #print("movie detected")

                        #print(current_screen)
                        continue

                # Time detection HH:MM
                #print("Hour detetciotn started")
                if len(parts) >= 1 and re.match(r"\d{1,2}:\d{2}", parts[0]):
                    #print("time")
                    current_time = parts[0]



                    # Check token after time for format
                    #Format Detection

                best_match = ""
                for f in formats:
                    if f in line and len(f) > len(best_match):
                        best_match = f

                if best_match:
                    current_format = best_match
                    current_format=build_max_label(current_screen,current_format)  # check if screen is MX and convert format to 2D ror 3D
                    #override curre format if screen name matches one of the formats
                    formats_set = {f.upper() for f in formats}
                    if current_screen and current_screen.upper() in formats_set:
                          current_format = current_screen

                    




                    # FIX: If time appears alone → add zero row
                if len(parts) == 1 and re.match(r"\d{1,2}:\d{2}", parts[0]):
                    page2_rows.append([
                    current_movie,
                    current_date,
                    current_time,
                    current_screen,
                    current_format,
                    None,
                    0,
                    0,
                    0,
                    None,
                    None,
                    None
                    ])
                    continue


                parts=remove_time_and_format(parts, current_time, current_format)

                parts = parts[1:]  #remove the number before the ticket class



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

                #update movei format in case SCREEN X is found intket class
                if "SCREEN X" in ticket_class.upper():
                  current_format = "SCREEN X"



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

                price, admits, gross, tax, net = numeric_tail



                admits = clean_num(admits)
                gross  = clean_num(gross)
                net    = clean_num(net)
                price = clean_num(price)

                # Append ticket row
                page2_rows.append([
                    current_movie,
                    current_date,
                    current_time,
                    current_screen,
                    current_format,
                    ticket_class,
                    0 if gross == 0 else admits,
                    gross,
                    net,
                    admits if gross == 0 else 0,  #"in case price is 0 the put admists in comps and put admits=0
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
    cinema_name, date_value, data_rows_page1, movie_list,week_type = extract_first_page(pdf_path)



    for r in data_rows_page1:
      new_row = [
          f,                                      # File
          exhibitor,                              # Exhibitor
          cinema_name,                            # Cinema
          week_type,                              # Week Type
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Extraction Date
      ]
      new_row.extend(r)
      rows_page1.append(new_row)


    # -------- PAGE 2 ----------
    page2_data = extract_page2_details(pdf_path, movie_list)

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

#df = fetch_data("pp.pdf", "sds")  # df must be your dataframe

#with pd.ExcelWriter("vox_single_output.xlsx") as writer:
#    df.to_excel(writer, sheet_name="Extracted Data", index=False)
#    print("Done. Created file: vox_single_output.xlsx")
