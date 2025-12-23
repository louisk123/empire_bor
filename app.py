import streamlit as st
import pandas as pd
import tempfile
import os
from bor_main import process_pdf  

st.title("Empire BOR Extraction System")

st.write("Upload one Excel file and several PDF files to process them.")

# --------------------------
# UPLOAD EXCEL FILE
# --------------------------
excel_file = st.file_uploader("Upload Excel Output File", type=["xlsx"])

# --------------------------
# UPLOAD MULTIPLE PDF FILES
# --------------------------
pdf_files = st.file_uploader("Upload PDF Files", type=["pdf"], accept_multiple_files=True)

# --------------------------
# UPLOAD BOR EXCEL FILES
# --------------------------
bor_excel_files = st.file_uploader(
    "Upload BOR Files (Excel)",
    type=["xlsm"],
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

        #copy data frrom BOR
        if bor_excel_files:
            wb_target = load_workbook(temp_excel_path)
            ws_target = wb_target["Data From BOR"]
        
            # start after last non-empty row
            start_row = ws_target.max_row + 1
        
            for bor_file in bor_excel_files:
                tmp_bor = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                tmp_bor.write(bor_file.read())
                tmp_bor_path = tmp_bor.name
        
                df_bor = pd.read_excel(tmp_bor_path, sheet_name=0)
                df_bor = df_bor.iloc[:, :11]   # first 11 columns
                df_bor = df_bor.iloc[1:]        # skip header row
        
                for _, row in df_bor.iterrows():
                    for c_idx, value in enumerate(row, start=1):
                        ws_target.cell(row=start_row, column=c_idx, value=value)
                    start_row += 1
        
                os.remove(tmp_bor_path)
        
            wb_target.save(temp_excel_path)


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
