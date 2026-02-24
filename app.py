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

# =====================================
# PAGE CONFIG
# =====================================
st.set_page_config(
    page_title="Siemens 840D Maintenance Agent",
    page_icon="⚙️",
    layout="wide"
)

# =====================================
# GEMINI INITIALIZATION (LEGACY SAFE)
# =====================================
@st.cache_resource
def initialize_ai():
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("Missing GEMINI_API_KEY in Streamlit secrets.")
        return None

    try:
        genai.configure(
            api_key=st.secrets["GEMINI_API_KEY"]
        )

        # IMPORTANT: use -latest for old keys
        model = genai.GenerativeModel("gemini-1.5-flash-latest")

        return model

    except Exception as e:
        st.error(f"AI Initialization Error: {e}")
        return None

model = initialize_ai()

# =====================================
# DATABASE FUNCTION
# =====================================
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

# =====================================
# PDF RAG FUNCTION (SAFE)
# =====================================
def extract_manual_context(user_query):
    pdf_path = "diagnostics_manual-sinumerik 840d.pdf"

    if not os.path.exists(pdf_path):
        return "Manual file not found."

    context = ""

    try:
        reader = pypdf.PdfReader(pdf_path)

        for i in range(min(len(reader.pages), 50)):
            text = reader.pages[i].extract_text()

            if text and user_query.lower() in text.lower():
                context += text + "\n"

            # Keep token usage small for free tier
            if len(context) > 3000:
                break

        if context.strip() == "":
            return "No relevant section found in first 50 pages."

        return context[:3000]

    except Exception as e:
        return f"PDF read error: {e}"

# =====================================
# UI
# =====================================
st.title("👨‍🔧 Siemens SINUMERIK 840D Intelligence Agent")
st.info("AI-powered maintenance assistant using defect logs + technical manual.")

tab1, tab2 = st.tabs(["💬 AI Troubleshooting", "📊 Database Search"])

# =====================================
# TAB 1 - AI CHAT
# =====================================
with tab1:

    st.subheader("Ask a Maintenance Question")

    user_query = st.text_input(
        "Example: 'How do I fix Alarm 61303?' or 'Analyze product 10'"
    )

    if user_query and model:

        with st.spinner("Analyzing manuals and logs..."):

            # Manual context
            manual_context = extract_manual_context(user_query)

            # DB context
            db_context = ""
            if any(char.isdigit() for char in user_query):
                df = query_factory_db(user_query)
                db_context = df.to_string()

            # Prompt (token optimized)
            prompt = f"""
You are a Senior Siemens SINUMERIK 840D Maintenance Engineer.

Manual Context:
{manual_context}

Database Context:
{db_context}

User Question:
{user_query}

Provide a structured, step-by-step professional remedy.
If an alarm code is mentioned, clearly explain what the technician must inspect.
Keep the response concise and operational.
"""

            try:
                response = model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.2,
                        "max_output_tokens": 800
                    }
                )

                st.chat_message("assistant").write(response.text)

            except Exception as e:
                if "429" in str(e):
                    st.warning("Free tier quota reached. Wait a minute and retry.")
                else:
                    st.error(f"AI Error: {e}")

# =====================================
# TAB 2 - DATABASE SEARCH
# =====================================
with tab2:

    st.subheader("Machine Defect Logs (SQLite)")

    search_id = st.text_input("Enter Product or Defect ID:")

    if search_id:
        results = query_factory_db(search_id)
        st.dataframe(results, use_container_width=True)

# =====================================
# SIDEBAR
# =====================================
with st.sidebar:
    st.header("Project Architecture")
    st.markdown("""
**Data Stack:**
- Python (Streamlit)
- SQLite (Structured Logs)
- PyPDF (Manual Parsing)
- Gemini 1.5 Flash (Legacy Free Tier)

Token-optimized for free quota usage.
""")
