

import pdfplumber
import pandas as pd
import re
from datetime import datetime
from openpyxl import load_workbook
from rapidfuzz import process, fuzz



# Import all modules ONCE
from modules import (
    vox,
    galaxy,
    safeer,
    shaab,
    star_cinemas,
    cine_royale,
    truth,
    truth_weekly
)



module_map = {
    "Star Cinemas": star_cinemas,
    "Cinepolis": vox,
    "Vox": vox,
    "Reel": vox,
    "NOVO": vox,
    "Cinemacity": vox,
    "Roxy": vox,
    "Cine Royale": cine_royale,
    "Galaxy": galaxy,
    "Truth": truth,
    "Truth Weekly": truth_weekly,
    "Shaab": shaab,
    "Safeer": safeer
}

def add_cinema_movie_format_date(df):
    df["Cinema_Movie_Format_Date"] = (df["Cinema"].astype(str) + " | " + df["Movie Mapped"].astype(str) + " | " + df["Format"].astype(str) + " | " +df["Date"].astype(str))
    return df



def find_last_real_row(ws):
    """
    Finds the last row that contains *any* data.
    It works even if there are empty rows in the middle.
    """
    last = 0
    for idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if any(v not in (None, "") for v in row):  # row has at least one value
            last = idx
    return last


def append_to_excel(excel_path, sheet_name, new_df):
    if len(new_df) == 0:
        #print("⚠️ new_df is EMPTY → nothing to append")
        return

    wb = load_workbook(excel_path)
    ws = wb[sheet_name]

    # find first free row
    last_row = find_last_real_row(ws)
    start_row = last_row + 1

    # write dataframe without overwriting anything
    for r_idx, row in new_df.iterrows():
        for c_idx, value in enumerate(row, start=1):
            ws.cell(row=start_row + r_idx, column=c_idx, value=value)

    wb.save(excel_path)
    #print("✔ Appended", len(new_df), "rows")


def get_sheet_name(row):

    week = row["Week Type"]
    summ = row["Is Summary"]




    if (week == "" or pd.isna(week)) and summ != 1:
        return "Daily BOR"
    if (week == "" or pd.isna(week)) and summ == 1:
        return "Daily BOR - summary"
    if week == "weekly" and summ != 1:
        return "Weekly BOR"
    if week == "weekly" and summ == 1:
        return "Weekly BOR - summary"
    return "Daily BOR"

def normalize_title(s):
    if not s or pd.isna(s):
        return ""
    s = s.lower()
    s = re.sub(r"\[.*?\]", "", s)      # remove [Arabic], [Japanese], etc.
    s = re.sub(r"[^a-z0-9 ]", " ", s)  # remove punctuation
    s = re.sub(r"\s+", " ", s).strip()
    return s


def map_movie(name, movie_list, threshold=80):
    if not name or pd.isna(name):
        return name

    name_norm = normalize_title(name)

    # Build normalized lookup once per call
    norm_to_original = {
        normalize_title(m): m for m in movie_list
    }

    match = process.extractOne(
        name_norm,
        norm_to_original.keys(),
        scorer=fuzz.token_set_ratio
    )

    if match and match[1] >= threshold:
        return norm_to_original[match[0]]

    # If confidence is low, keep original
    return name

def screen_rule(g):
    valid_screens = (
        g.dropna(subset=["Screen", "Time"])
         .groupby("Screen")["Time"]
         .nunique()
    )
    n = (valid_screens >= 3).sum()
    return n if n > 0 else 1


def fix_dates(file_df):

    flip_exhibitors = {"Cinepolis", "Vox", "Reel", "NOVO", "Cinemacity", "Roxy"}
    slash_exhibitors = {"Galaxy", "Truth", "Truth Weekly", "Shaab", "Safeer"}

    # ensure string
    file_df["Date"] = file_df["Date"].astype(str)

    # 1) replace - with / for slash exhibitors
    mask_slash = file_df["Exhibitor"].isin(slash_exhibitors)
    file_df.loc[mask_slash, "Date"] = file_df.loc[mask_slash, "Date"].str.replace("-", "/", regex=False)

    # 2) flip day/month for flip exhibitors when not summary
    mask_flip = (
        file_df["Exhibitor"].isin(flip_exhibitors) &
        (file_df["Is Summary"] != 1)
    )

    # split and reassemble safely
    date_parts = file_df.loc[mask_flip, "Date"].str.split("/", expand=True)
    file_df.loc[mask_flip, "Date"] = (
        date_parts[1] + "/" + date_parts[0] + "/" + date_parts[2]
    )
    return file_df



def process_pdf(pdf_path, excel_path):


    #file_df=pd.DataFrame()
    now_value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # read the mapping sheet
    mapping_df = pd.read_excel(
        excel_path,
        sheet_name="Cinemas Mapping",
        usecols=["Name from File", "Line", "Exhibitor", "Country"]
    )
    movies_df = pd.read_excel(
        excel_path,
        sheet_name="Movies",
        usecols=["BOR Movie Name"]
    )
    
    
    movie_list = (
        movies_df["BOR Movie Name"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text() or ""
            first_line = text.split("\n")[0].strip()
    except:
        # print("Could not read:", pdf_path)
        return

    # Find matching cinema
    cinema_found = None
    cinema_country = None
    exhibitor = None
    first_line_upper = first_line.upper()

    for _, row in mapping_df.iterrows():

        if first_line_upper == "AL MARIAH MALL ABU DHABHI":
            first_line_upper = first_line_upper + " " + text.split("\n")[1].strip().upper()

        cinema_name = str(row["Name from File"]).upper()
        if cinema_name in first_line_upper:
            cinema_found = cinema_name
            cinema_country = row["Country"]
            exhibitor = row["Exhibitor"]
            break

    if cinema_found is None:
        print("No cinema match for:", pdf_path)
        return

    # Call correct module
    module = module_map[exhibitor]

    try:
        file_df = module.fetch_data(pdf_path, exhibitor)

        if file_df is None or len(file_df) == 0:
            print("Empty df, skipping:", pdf_path)
            return

        # Fix column names
        file_df.columns = [
                    "File", "Exhibitor","Cinema", "Week Type", "Extraction Date",
                    "Movie","Date","Time","Screen","Format","Ticket Type",
                    "Admits","Gross","Net","Comp","Is Summary","Summary Sessions"
          ]

        file_df["Extraction Date"] = now_value
        file_df["Country"] = cinema_country
        
        file_df["Movie Mapped"] = file_df["Movie"].apply(
            lambda x: map_movie(x, movie_list)
        )

        file_df=fix_dates(file_df)
        EXPECTED_ORDER = [
              "File","Exhibitor","Cinema","Week Type","Extraction Date",
              "Movie","Movie Mapped","Date","Time","Screen","Format",
              "Ticket Type","Admits","Gross","Net","Comp",
              "Is Summary","Summary Sessions","Country"
              ]

        file_df = file_df.reindex(columns=EXPECTED_ORDER)

        append_to_excel(excel_path, "Raw Data", file_df)

        # Normalize fields
        file_df["Week Type"] = file_df["Week Type"].fillna("").str.strip().str.lower()
        file_df["Is Summary"] = file_df["Is Summary"].fillna(0).astype(int)

        #compute number of screens
        group_cols = [
                  "File","Exhibitor","Cinema","Week Type","Extraction Date",
              "Movie","Movie Mapped","Date",
              "Is Summary","Country","Format"
        ]

        screen_counts = file_df.groupby(group_cols).apply(screen_rule)

        file_df["Screen_Calc"] = (
                  file_df
                  .set_index(group_cols)
                  .index
                  .map(screen_counts)
)

        
        
        
        
        # --------------------------
        # SPLIT DATA
        # --------------------------

        daily_df = file_df[
            (file_df["Week Type"] != "weekly") &
            (file_df["Is Summary"] != 1)
        ]

        daily_sum_df = file_df[
            (file_df["Week Type"] != "weekly") &
            (file_df["Is Summary"] == 1)
        ]

        weekly_df = file_df[
            (file_df["Week Type"] == "weekly") &
            (file_df["Is Summary"] != 1)
        ]

        weekly_sum_df = file_df[
            (file_df["Week Type"] == "weekly") &
            (file_df["Is Summary"] == 1)
        ]

        # --------------------------
        # AGGREGATIONS
        # --------------------------

        group_cols = [
            "Country", "File", "Exhibitor", "Cinema", "Extraction Date",
            "Movie","Movie Mapped", "Date", "Format"
        ]

        agg_rules = {
            "Admits": "sum",
            "Gross": "sum",
            "Net": "sum",
            "Comp": "sum",
            "Summary Sessions": "sum",
            "Screen_Calc": "max",
            "Time": "nunique"
        }

        daily_agg = daily_df.groupby(group_cols).agg(agg_rules).reset_index()
        daily_sum_agg = daily_sum_df.groupby(group_cols).agg(agg_rules).reset_index()
        weekly_agg = weekly_df.groupby(group_cols).agg(agg_rules).reset_index()
        weekly_sum_agg = weekly_sum_df.groupby(group_cols).agg(agg_rules).reset_index()
        
        daily_agg = add_cinema_movie_format_date(daily_agg)
        daily_sum_agg = add_cinema_movie_format_date(daily_sum_agg)
        weekly_agg = add_cinema_movie_format_date(weekly_agg)
        weekly_sum_agg = add_cinema_movie_format_date(weekly_sum_agg)



        # Write results
        append_to_excel(excel_path, "Daily BOR", daily_agg)
        append_to_excel(excel_path, "Daily BOR - Summary", daily_sum_agg)
        append_to_excel(excel_path, "Weekly BOR", weekly_agg)
        append_to_excel(excel_path, "Weekly BOR - Summary", weekly_sum_agg)

    except Exception as e:
        print("Error calling module:", e)
