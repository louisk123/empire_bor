import streamlit as st
import pandas as pd
import tempfile
import os
from bor_main import process_pdf  

st.title("Empire BOR Extraction System")

st.write("Upload one Excel f
ile and several PDF files to process them.")

# --------------------------
# UPLOAD EXCEL FILE
# --------------------------
excel_file = st.file_uploader("Upload Excel Output File", type=["xlsx"])

# --------------------------
# UPLOAD MULTIPLE PDF FILES
# --------------------------
pdf_files = st.file_uploader("Upload PDF Files", type=["pdf"], accept_multiple_files=True)

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
    temp_excel_path = temp_excel.name

    st.success("Excel loaded successfully.")

    # Process each PDF
    progress = st.progress(0)
    total = len(pdf_files)

    for idx, pdf in enumerate(pdf_files, start=1):
        # Create a temp file for this PDF
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_pdf.write(pdf.read())
        temp_pdf_path = temp_pdf.name

        # Call your main function
        process_pdf(temp_pdf_path, temp_excel_path)

        # Remove PDF temp
        os.remove(temp_pdf_path)

        progress.progress(idx / total)

    st.success("Processing complete!")

    # After all PDFs processed → return updated Excel to user
    with open(temp_excel_path, "rb") as f:
        st.download_button(
            label="Download Updated Excel",
            data=f,
            file_name="Updated_BOR_Output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # Cleanup Excel temp as well
    os.remove(temp_excel_path)
