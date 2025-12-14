

import pdfplumber
import pandas as pd
from datetime import datetime
from openpyxl import load_workbook



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




def process_pdf(pdf_path, excel_path):
    #file_df=pd.DataFrame()
    now_value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # read the mapping sheet
    mapping_df = pd.read_excel(
        excel_path,
        sheet_name="Cinemas Mapping",
        usecols=["Name from File", "Line", "Exhibitor", "Country"]
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
            "File", "Exhibitor", "Cinema", "Week Type", "Extraction Date",
            "Movie", "Date", "Time", "Screen", "Format", "Ticket Type",
            "Admits", "Gross", "Net", "Comp", "Is Summary", "Summary Sessions"
        ]

        file_df["Extraction Date"] = now_value
        file_df["Country"] = cinema_country

        append_to_excel(excel_path, "Raw Data", file_df)

        # Normalize fields
        file_df["Week Type"] = file_df["Week Type"].fillna("").str.strip().str.lower()
        file_df["Is Summary"] = file_df["Is Summary"].fillna(0).astype(int)

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
            "Movie", "Date", "Format"
        ]

        agg_rules = {
            "Admits": "sum",
            "Gross": "sum",
            "Net": "sum",
            "Comp": "sum",
            "Summary Sessions": "sum",
            "Screen": "nunique",
            "Time": "count"
        }

        daily_agg = daily_df.groupby(group_cols).agg(agg_rules).reset_index()
        daily_sum_agg = daily_sum_df.groupby(group_cols).agg(agg_rules).reset_index()
        weekly_agg = weekly_df.groupby(group_cols).agg(agg_rules).reset_index()
        weekly_sum_agg = weekly_sum_df.groupby(group_cols).agg(agg_rules).reset_index()

        # Write results
        append_to_excel(excel_path, "Daily BOR", daily_agg)
        append_to_excel(excel_path, "Daily BOR - Summary", daily_sum_agg)
        append_to_excel(excel_path, "Weekly BOR", weekly_agg)
        append_to_excel(excel_path, "Weekly BOR - Summary", weekly_sum_agg)

    except Exception as e:
        print("Error calling module:", e)
