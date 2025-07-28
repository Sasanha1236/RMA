import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
import os
import json

# --- Config ---
st.set_page_config(page_title="RMA Tracker", layout="wide")
st.title("📦 RMA Tracker – ISO 9001 Enhanced")

# --- Email-Based Access Control ---
st.sidebar.title("🔐 Access")
user_email = st.sidebar.text_input("Enter your email to continue:")

CREATORS = {"customerservice@norenthermal.com", "sasanh@norenthermal.com", "rayb@norenthermal.com", "dennisg@norenthermal.com"}
INSPECTORS = {"tiosua@norenthermal.com", "testcam1@norenthermal.com", "danield@norenthermal.com", "sasanh@norenthermal.com", "dennisg@norenthermal.com"}
REVIEWERS = {"sasanh@norenthermal.com", "dennisg@norenthermal.com"}

if user_email in CREATORS:
    role = "Request for Return"
elif user_email in INSPECTORS:
    role = "Inspection and Disposition"
elif user_email in REVIEWERS:
    role = "Final Review"
else:
    st.error("❌ You do not have permission to access this system.")
    st.stop()

st.sidebar.success(f"Access granted: {role}")

# --- Constants ---
CSV_FILE = "rma_log.csv"
EXCEL_FILE = "rma_log.xlsx"
os.makedirs("uploaded_docs", exist_ok=True)

# --- RMA ID Generator ---
def generate_rma_id():
    now = datetime.now()
    timestamp = now.strftime("%y%m")
    unique_part = str(uuid.uuid4())[:3].upper()
    return f"RMA-{timestamp}{unique_part}"

# --- Load RMA Data ---
def load_rma_data():
    try:
        return pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        return pd.DataFrame(columns=[
            "RMA ID", "Date Created", "Customer", "Product", "Serial Number",
            "PO Number", "SO Number", "Hazardous Location", "Reason Codes", "Notes",
            "Status", "Created By", "Inspected By", "Reviewed By", "Attached Document",
            "Date Received", "Inspection Document", "Cause Note", "Inspection Outcome",
            "QA Certified", "CAPA Required", "CAPA ID", "Change Log"
        ])

df = load_rma_data()

# --- Save RMA Data ---
def save_rma_data(df):
    df.to_csv(CSV_FILE, index=False)
    df.to_excel(EXCEL_FILE, index=False)

# --- Request for Return ---
if role == "Request for Return":
    with st.form("rma_form"):
        st.subheader("🔍 RMA Submission")

        customer = st.text_input("Customer Name")
        product = st.text_input("Product / Unit ID")
        serial_number = st.text_input("Serial Number (S/N) (optional)")
        date_created = datetime.now().strftime("%Y-%m-%d %H:%M")
        po_number = st.text_input("PO#")
        so_number = st.text_input("SO#")
        hazardous = st.radio("Is this a Hazardous Location Unit?", ["No", "Yes"])
        reasons = st.text_area("Enter Reason Codes or Description")
        notes = st.text_area("Additional Notes (optional)")
        uploaded_file = st.file_uploader("Attach a Document (optional)", type=["pdf", "png", "jpg", "jpeg", "docx"])
        submit = st.form_submit_button("Submit RMA")

    if submit:
        if not customer or not product or not reasons:
            st.warning("Please complete all required fields.")
        else:
            rma_id = generate_rma_id()
            doc_path = ""
            if uploaded_file:
                doc_path = os.path.join("uploaded_docs", f"{rma_id}_{uploaded_file.name}")
                with open(doc_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

            entry = {
                "RMA ID": rma_id,
                "Date Created": date_created,
                "Customer": customer,
                "Product": product,
                "Serial Number": serial_number,
                "PO Number": po_number,
                "SO Number": so_number,
                "Hazardous Location": hazardous,
                "Reason Codes": reasons,
                "Notes": notes,
                "Status": "Submitted",
                "Created By": user_email,
                "Inspected By": "",
                "Reviewed By": "",
                "Attached Document": doc_path,
                "Date Received": "",
                "Inspection Document": "",
                "Cause Note": "",
                "Inspection Outcome": "",
                "QA Certified": "No",
                "CAPA Required": "No",
                "CAPA ID": "",
                "Change Log": "[]"
            }

            df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
            save_rma_data(df)
            st.success(f"✅ RMA Submitted Successfully! ID: {rma_id}")

# --- Inspection and Disposition ---
if role == "Inspection and Disposition":
    st.subheader("🔧 Inspection Workflow")
    if not df.empty:
        df["Label"] = df["RMA ID"] + " – " + df["Customer"] + " – " + df["Product"]
        selected_label = st.selectbox("Select RMA to Inspect", df["Label"])
        row = df[df["Label"] == selected_label].index[0]

        with st.form("inspect_form"):
            date_received = st.date_input("Date RMA Received", datetime.today())
            insp_doc = st.file_uploader("Upload Inspection Document", type=["pdf", "jpg", "png", "docx"], key="insp")
            cause_note = st.text_area("Cause / Findings")
            outcome = st.selectbox("Disposition Outcome", ["", "Disposition", "Repaired", "Replaced", "Rejected"])
            capa_required = st.radio("CAPA Required?", ["No", "Yes"])
            capa_id = st.text_input("CAPA ID (if applicable)")
            submit_insp = st.form_submit_button("Submit Inspection")

        if submit_insp:
            df.at[row, "Date Received"] = date_received.strftime("%Y-%m-%d")
            df.at[row, "Cause Note"] = cause_note
            df.at[row, "Inspection Outcome"] = outcome
            df.at[row, "Inspected By"] = user_email
            df.at[row, "CAPA Required"] = capa_required
            df.at[row, "CAPA ID"] = capa_id
            df.at[row, "Status"] = "Inspected"
            if insp_doc:
                insp_path = os.path.join("uploaded_docs", f"{df.at[row, 'RMA ID']}_insp_{insp_doc.name}")
                with open(insp_path, "wb") as f:
                    f.write(insp_doc.getbuffer())
                df.at[row, "Inspection Document"] = insp_path
            save_rma_data(df)
            st.success("Inspection data saved.")

# --- Final Review ---
if role == "Final Review":
    st.subheader("🔎 Final QA Review")
    pending = df[df["Status"] == "Inspected"]
    if not pending.empty:
        pending["Label"] = pending["RMA ID"] + " – " + pending["Customer"] + " – " + pending["Product"]
        selected_label = st.selectbox("Select RMA to Review", pending["Label"])
        row = pending[pending["Label"] == selected_label].index[0]

        with st.form("qa_form"):
            qa_certify = st.checkbox("I certify this RMA has been reviewed in accordance with quality procedures.")
            mark_complete = st.checkbox("Mark this RMA as Completed")
            submit_qa = st.form_submit_button("Submit QA Review")

        if submit_qa:
            df.at[row, "Reviewed By"] = user_email
            df.at[row, "QA Certified"] = "Yes" if qa_certify else "No"
            if mark_complete:
                df.at[row, "Status"] = "Completed"
            save_rma_data(df)
            st.success("QA Review submitted.")

# --- RMA Records ---
st.markdown("---")
st.subheader("📋 All RMA Records")
status_filter = st.selectbox("Filter by Status", ["All"] + df["Status"].dropna().unique().tolist())
filtered_df = df if status_filter == "All" else df[df["Status"] == status_filter]
st.dataframe(filtered_df.drop(columns=["Label"], errors="ignore"))
