""" import streamlit as st
import google.generativeai as genai
import sqlite3

# 1. SETUP: Securely get your Gemini Key from Streamlit Secrets
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("🤖 Siemens 840D Intelligence Agent")

# 2. DATA ACCESS: Function to query your SQLite DB
def get_defect_info(product_id):
    conn = sqlite3.connect('factory_data.db')
    query = f"SELECT * FROM defects WHERE product_id = {product_id}"
    result = conn.execute(query).fetchone()
    conn.close()
    return result

# 3. INTERFACE: Simple user input
user_input = st.chat_input("Ask about a product ID or a Siemens Alarm...")

if user_input:
    # Logic to route the question
    if "product" in user_input.lower():
        # Query SQL and then ask Gemini to explain the result
        data = get_defect_info(10) # Example ID
        response = model.generate_content(f"Explain this factory defect record: {data}")
        st.write(response.text) """
import streamlit as st
import google.generativeai as genai
import sqlite3
import pandas as pd
import pypdf
import os

# =============================
# 1. PAGE CONFIG
# =============================
st.set_page_config(
    page_title="Siemens 840D Maintenance Agent",
    page_icon="⚙️",
    layout="wide"
)

# =============================
# 2. AI INITIALIZATION (STABLE)
# =============================
@st.cache_resource
def initialize_ai():
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("Missing GEMINI_API_KEY in Streamlit secrets.")
        return None

    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-1.5-flash")
        return model
    except Exception as e:
        st.error(f"AI Initialization Error: {e}")
        return None

model = initialize_ai()

# =============================
# 3. DATABASE FUNCTION
# =============================
def query_factory_db(search_term):
    if not os.path.exists("factory_data.db"):
        return pd.DataFrame({"Error": ["Database file not found."]})

    try:
        conn = sqlite3.connect("factory_data.db")
        query = """
        SELECT * FROM defects 
        WHERE defect_id = ? OR product_id = ?
        """
        df = pd.read_sql(query, conn, params=(search_term, search_term))
        conn.close()

        if df.empty:
            return pd.DataFrame({"Result": ["No matching records found."]})

        return df

    except Exception as e:
        return pd.DataFrame({"Error": [str(e)]})

# =============================
# 4. PDF MANUAL RAG FUNCTION
# =============================
def extract_manual_context(user_query):
    pdf_path = "diagnostics_manual-sinumerik 840d.pdf"

    if not os.path.exists(pdf_path):
        return "Manual file not found on server."

    context = ""

    try:
        reader = pypdf.PdfReader(pdf_path)

        for i in range(min(len(reader.pages), 50)):
            text = reader.pages[i].extract_text()

            if text and user_query.lower() in text.lower():
                context += text + "\n"

            if len(context) > 4000:
                break

        if context.strip() == "":
            return "No relevant section found in first 50 pages."

        return context[:4000]

    except Exception as e:
        return f"Error reading PDF: {e}"

# =============================
# 5. UI
# =============================
st.title("👨‍🔧 Siemens SINUMERIK 840D Intelligence Agent")
st.info("This agent connects SQL Defect Logs with Siemens Technical Manuals.")

tab1, tab2 = st.tabs(["💬 AI Troubleshooting", "📊 Database Search"])

# =============================
# TAB 1 - AI CHAT
# =============================
with tab1:

    st.subheader("Ask a Maintenance Question")

    user_query = st.text_input(
        "Example: 'How do I fix Alarm 61303?' or 'Analyze product 10'"
    )

    if user_query:

        if not model:
            st.warning("AI model not initialized.")
        else:
            with st.spinner("Analyzing manuals and logs..."):

                # Step 1: Manual Context
                manual_context = extract_manual_context(user_query)

                # Step 2: Database Context
                db_context = ""
                if any(char.isdigit() for char in user_query):
                    df = query_factory_db(user_query)
                    db_context = df.to_string()

                # Step 3: Prompt Engineering
                prompt = f"""
You are a Senior Siemens SINUMERIK 840D Maintenance Engineer.

Manual Context:
{manual_context}

Database Context:
{db_context}

User Question:
{user_query}

Instructions:
- Provide a professional and practical remedy.
- If an alarm code is referenced, explain step-by-step what the technician should inspect.
- Keep the answer structured and operational.
"""

                try:
                    response = model.generate_content(prompt)

                    # Safe response extraction
                    output = getattr(response, "text", None)

                    if not output:
                        output = str(response)

                    st.chat_message("assistant").write(output)

                except Exception as e:
                    if "429" in str(e):
                        st.warning("Quota reached. Please wait and retry.")
                    else:
                        st.error(f"AI Error: {e}")

# =============================
# TAB 2 - DATABASE VIEW
# =============================
with tab2:

    st.subheader("Machine Defect Logs (SQLite)")

    search_id = st.text_input("Enter Product or Defect ID:")

    if search_id:
        results = query_factory_db(search_id)
        st.dataframe(results, use_container_width=True)

# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.header("Project Architecture")
    st.markdown("""
**Data Stack:**
- Python (Streamlit)
- SQLite (Structured Logs)
- PyPDF (Unstructured Manuals)
- Gemini 1.5 Flash (RAG Engine)

Optimized for factory-floor mobile browser use.
""")
