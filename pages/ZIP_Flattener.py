import io
import os
import zipfile
from collections import defaultdict
import streamlit as st

st.set_page_config(page_title="ZIP Flattener", page_icon="🗜️")

st.title("ZIP Flattener")
st.caption("Upload a ZIP, flatten all files into one ZIP, auto-rename duplicates.")

uploaded = st.file_uploader("Upload ZIP file", type=["zip"])

def flatten_zip_bytes(zip_bytes: bytes) -> bytes:
    name_counter = defaultdict(int)
    out_buf = io.BytesIO()

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zin, \
         zipfile.ZipFile(out_buf, "w", zipfile.ZIP_DEFLATED) as zout:

        for info in zin.infolist():
            if info.is_dir():
                continue

            original_name = os.path.basename(info.filename)
            base, ext = os.path.splitext(original_name)

            count = name_counter[original_name]
            name_counter[original_name] += 1

            new_name = original_name if count == 0 else f"{base}_{count}{ext}"

            with zin.open(info) as f:
                zout.writestr(new_name, f.read())

    out_buf.seek(0)
    return out_buf.getvalue()

if uploaded:
    if st.button("Flatten ZIP"):
        try:
            out_bytes = flatten_zip_bytes(uploaded.read())
            out_name = uploaded.name.replace(".zip", "_flattened.zip")

            st.success("ZIP flattened successfully")

            st.download_button(
                label="Download flattened ZIP",
                data=out_bytes,
                file_name=out_name,
                mime="application/zip",
            )

        except zipfile.BadZipFile:
            st.error("Invalid ZIP file")
        except Exception as e:
            st.error(str(e))
