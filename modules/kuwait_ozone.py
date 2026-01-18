import pdfplumber
import pandas as pd
import os
from datetime import datetime
import re



def fetch_data(pdf_path,exhibitor):

  df_raw = pd.read_excel(pdf_path, engine="openpyxl", header=None)

  # metadata (same as you had)
  cinema = str(df_raw.iloc[6, 1]).strip()
  movie = str(df_raw.iloc[7, 1]).strip()
  show_date = df_raw.iloc[6, 4]
  show_date = pd.to_datetime(show_date, errors="coerce").strftime("%d/%m/%Y")
  extraction_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  FORMAT_DEFAULT="2D"

  # find header cell "Ticket Type"
  mask = df_raw.astype(str).apply(lambda col: col.str.strip().str.upper()).eq("TICKET TYPE")
  header_pos = mask.stack()
  header_pos = header_pos[header_pos].index.tolist()

  if not header_pos:
      raise ValueError("Could not find 'Ticket Type' header in the sheet.")

  header_row, start_col = header_pos[0]

  # take 8 columns starting from Ticket Type, and rows after the header
  table = df_raw.iloc[header_row + 1:, start_col:start_col + 8].copy()

  table.columns = [
      "Ticket Type",
      "Unit Price in KD",
      "Seat Count",
      "SCREEN NUMBER",
      "SHOW TIME",
      "ADMISSION",
      "VIP",
      "GROSS BOX OFFICE"
  ]

  table = table.dropna(subset=["Ticket Type"])
  table = table[~table["Ticket Type"].astype(str).str.upper().str.contains("TOTAL")]

#    "File", "Exhibitor","Cinema", "Week Type", "Extraction Date","Movie","Date","Time", "Screen" , "Format", "Ticket Type","Admits","Gross","Net", "Comp" ,"Is Summary",   "Summary Sessions"]


  # build rows
  final_df = pd.DataFrame([
      [
          pdf_path,                                      # File
          exhibitor,                              # Exhibitor
          cinema,                            # Cinema
          None,                              # Week Type
          extraction_date,  # Extraction Date
          movie,
          show_date,
          table.loc[i, "SHOW TIME"],
          table.loc[i, "SCREEN NUMBER"],
          FORMAT_DEFAULT,
          table.loc[i, "Ticket Type"],
          table.loc[i, "ADMISSION"] if pd.notna(table.loc[i, "ADMISSION"]) else 0,
          table.loc[i, "GROSS BOX OFFICE"] if pd.notna(table.loc[i, "GROSS BOX OFFICE"]) else 0,
          None,
          None,
          None,
          None
          
      ]
      for i in table.index
  ])


  return final_df

#df = fetch_data("pp.xlsx", "sds")  # df must be your dataframe

#with pd.ExcelWriter("ozone_single_output.xlsx") as writer:
#    df.to_excel(writer, sheet_name="Extracted Data", index=False)
#    print("Done. Created file: ozone_single_output.xlsx")


