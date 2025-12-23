import streamlit as st
import pandas as pd
import tempfile
import os
from openpyxl import load_workbook
from bor_main import process_pdf  

st.title("Empire BOR Extraction System")
st.write("Upload one Excel file, multiple PDF files, and optional BOR Excel files.")

# --------------------------
# UPLOAD EXCEL OUTPUT FILE
# --------------------------
excel_file = st.file_uploader(
    "Upload Excel Output File",
    type=["xlsx"]
)

# --------------------------
# UPLOAD PDF FILES
# --------------------------
pdf_files = st.file_uploader(
    "Upload PDF Files",
    type=["pdf"],
    accept_multiple_files=True
)

# --------------------------
# UPLOAD BOR EXCEL FILES (OPTIONAL)
# --------------------------
bor_excel_files = st.file_uploader(
    "Upload BOR Files (Excel)",
    type=["xlsm", "xlsx"],
    accept_multiple_files=True
)

# --------------------------
# RUN PROCESSING
# --------------------------
if st.button("Start Processing"):

    if not excel_file:
        st.error("Please upload an Excel file.")
        st.stop()

    if not pdf_files:
        st.error("Please upload at least one PDF.")
        st.stop()

    # Save Excel temporarily
    temp_excel = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    temp_excel.write(excel_file.read())
    temp_excel.close()
    temp_excel_path = temp_excel.name

    st.success("Excel loaded successfully.")

    # --------------------------
    # PROCESS PDF FILES
    # --------------------------
    progress = st.progress(0)
    total = len(pdf_files)

    for idx, pdf in enumerate(pdf_files, start=1):
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_pdf.write(pdf.read())
        temp_pdf.close()
        temp_pdf_path = temp_pdf.name

        process_pdf(temp_pdf_path, temp_excel_path)

        os.remove(temp_pdf_path)
        progress.progress(idx / total)

    # --------------------------
    # COPY DATA FROM BOR FILES (ONCE)
    # --------------------------
    if bor_excel_files:
        wb_target = load_workbook(temp_excel_path)
        ws_target = wb_target["Data From BOR"]
        
        start_row = ws_target.max_row + 1
        
        for bor_file in bor_excel_files:
            tmp_bor = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            tmp_bor.write(bor_file.read())
            tmp_bor.close()
            tmp_bor_path = tmp_bor.name
        
            wb_bor = load_workbook(tmp_bor_path, data_only=True)
            ws_bor = wb_bor["Data"]
        
            for row in ws_bor.iter_rows(min_row=2, max_col=16, values_only=True):
                ws_target.append(row)
        
            os.remove(tmp_bor_path)
        
        wb_target.save(temp_excel_path)



    st.success("Processing complete!")

    # --------------------------
    # DOWNLOAD RESULT
    # --------------------------
    with open(temp_excel_path, "rb") as f:
        st.download_button(
            label="Download Updated Excel",
            data=f,
            file_name="Updated_BOR_Output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    os.remove(temp_excel_path)
