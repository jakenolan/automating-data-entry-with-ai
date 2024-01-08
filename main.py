# Imports
from pypdf import PdfReader
from openai import OpenAI
import streamlit as st
import json
import time

# Initial setup
if "OPENAI_API_KEY" not in st.session_state:
        st.session_state["OPENAI_API_KEY"] = ""
if "history" not in st.session_state:
    st.session_state["history"] = []
if "view_history" not in st.session_state:
    st.session_state["view_history"] = False
if "viewing_history_entry" not in st.session_state:
    st.session_state["viewing_history_entry"] = {}
if "pdf_uploader_int" not in st.session_state:
    st.session_state["pdf_uploader_int"] = 0

# Side menu
with st.sidebar:
    # OpenAI API key section
    if st.session_state["OPENAI_API_KEY"] == "":
        with st.form(key="openai_api_key_form"):
            st.subheader("🔑 OpenAI API Key")
            st.session_state["OPENAI_API_KEY"] = st.text_input("OpenAI API Key", label_visibility="collapsed", key="openai_api_key", type="password")
            submit_button, needs_key_button = st.columns(spec=[1, 1])
            with submit_button:
                api_key_submitted = st.form_submit_button("Save key", type="primary")
            with needs_key_button:
                st.link_button("Need a key?", "https://platform.openai.com/account/api-keys")
            if api_key_submitted:
                st.rerun()
    else:
        with st.form(key="openai_api_key_form"):
            st.subheader("🔑 OpenAI API Key")
            st.success("API key saved!")
            new_key_requested = st.form_submit_button("Change key")
            if new_key_requested:
                st.session_state["OPENAI_API_KEY"] = ""
                st.rerun()
    # History section
    st.markdown("# 📑 History")
    for entry in st.session_state["history"]:
        with st.form(key=entry["file_name"]):
            st.subheader(entry["file_name"])
            col1, col2, col3 = st.columns(spec=[3, 4, 3])
            with col1:
                delete_button_submitted = st.form_submit_button("Delete")
            with col2:
                download_button_submitted = st.form_submit_button("Download")
            with col3:
                view_button_submitted = st.form_submit_button("View")
        if delete_button_submitted:
            for to_delete_entry in st.session_state["history"]:
                if to_delete_entry["file_name"] == entry["file_name"]:
                    st.session_state["history"].remove(entry)
                    st.rerun()
        if download_button_submitted:
            with open(f"{entry['file_name']}.json", "w") as f:
                json.dump(entry["json"], f)
            st.session_state["view_history"] = True
            st.session_state["viewing_history_entry"] = entry
            st.session_state["pdf_uploader_int"] += 1
            st.rerun()
        if view_button_submitted:
            st.session_state["view_history"] = True
            st.session_state["viewing_history_entry"] = entry
            st.session_state["pdf_uploader_int"] += 1
            st.rerun()

# Upload window
st.title("📚 PDF Data Extractor")
st.divider()
uploaded_file = st.file_uploader("Upload a PDF", type="pdf", key=f"pdf_uploader_{st.session_state['pdf_uploader_int']}")
if uploaded_file:
    st.session_state["view_history"] = False
    st.session_state["viewing_history_entry"] = {}
    st.success("PDF uploaded successfully!")
st.divider()

# pdf to text handling
def pdf_to_text(uploaded_file):
    try:
        pdf_content = {}
        reader = PdfReader(uploaded_file)
        for i in range(len(reader.pages)):
            raw_text = reader.pages[i].extract_text()
            pdf_content[f"page_{i}"] = raw_text
        print(pdf_content)
        return pdf_content
    except Exception as e:
        st.error(e)
        return

# OpenAI handling
client = OpenAI(api_key=st.session_state["OPENAI_API_KEY"])
def organize_data_with_openai(uploaded_file):
    try:
        pdf_content = pdf_to_text(uploaded_file)
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
                {"role": "user", "content": f"Optimally organize this text data in JSON: {pdf_content}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(e)
        return
    
# Duplicate renaming
def rename_duplicate(file_name, json, first):
    if first:
        file_name = file_name + "_0"
        json["file_name"] = file_name
    else:
        original_name, num = file_name.rsplit("_", 1)
        file_name = f"{original_name}_{int(num) + 1}"
        json["file_name"] = file_name
    update_history(file_name, json, first=False)

# History handling
def update_history(file_name, json, first=True):
    if not st.session_state["history"]:
        st.session_state["history"].append({"file_name": file_name, "json": json})
        return
    if st.session_state["history"]:
        for entry in st.session_state["history"]:
            if entry["file_name"] == file_name:
                rename_duplicate(file_name, json, first)
                return
        st.session_state["history"].append({"file_name": file_name, "json": json})

# Output window
if uploaded_file:
    for x in range(0, 2):
        with st.spinner("Extracting data..."):
            organized_data = organize_data_with_openai(uploaded_file)
        if organized_data:
            try:
                valid_data = json.loads(organized_data)
            except Exception as e:
                st.error("Invalid data returned from OpenAI API.")
                st.error("Retrying...")
                time.sleep(3)
        else:
            st.error("OpenAI API error.")
            st.error("Please try re-uploading the PDF.")
            break
        if valid_data:
            file_name = uploaded_file.name.rsplit(".", 1)[0]
            update_history(file_name, valid_data)
            st.session_state["pdf_uploader_int"] += 1
            st.session_state["view_history"] = True
            st.session_state["viewing_history_entry"] = st.session_state["history"][-1]
            st.rerun()
            break
        else:
            st.error("Data extraction failed.")
            st.error("Please try re-uploading the PDF.")
            break
elif st.session_state["view_history"] and st.session_state["viewing_history_entry"] in st.session_state["history"]:
    st.header(st.session_state["viewing_history_entry"]["file_name"])
    st.json(st.session_state["viewing_history_entry"]["json"])