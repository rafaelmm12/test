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
import google.genai as genai
import sqlite3
import pandas as pd
import pypdf
import os

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Siemens 840D Maintenance Agent", 
    page_icon="⚙️", 
    layout="wide"
)

# --- 2. AI SETUP & MODEL DISCOVERY ---
def initialize_ai():
    """Configures Gemini and finds the best available model for your API key."""
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("Missing GEMINI_API_KEY. Please add it to Streamlit Secrets.")
        return None

    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    try:
        # Automatically find a model your key has access to
        available_models = [m.name for m in genai.list_models() 
                           if 'generateContent' in m.supported_generation_methods]
        
        # Priority list (Flash is best for free tier quotas)
        priority = ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest', 'models/gemini-pro']
        
        for model_path in priority:
            if model_path in available_models:
                return genai.GenerativeModel(model_path)
        
        return genai.GenerativeModel(available_models[0])
    except Exception as e:
        st.error(f"Failed to initialize AI: {e}")
        return None

model = initialize_ai()

# --- 3. DATA ENGINEERING FUNCTIONS ---
def query_factory_db(search_term):
    """Queries the local SQLite database for defect records."""
    try:
        conn = sqlite3.connect('factory_data.db')
        # Search by either Defect ID or Product ID
        query = "SELECT * FROM defects WHERE defect_id = ? OR product_id = ?"
        df = pd.read_sql(query, conn, params=(search_term, search_term))
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame({"Error": [str(e)]})

def extract_manual_context(query):
    """Searches the PDF for keywords to provide context to the AI (RAG)."""
    pdf_path = "diagnostics_manual-sinumerik 840d.pdf"
    if not os.path.exists(pdf_path):
        return "Manual file not found on server."
    
    context = ""
    try:
        reader = pypdf.PdfReader(pdf_path)
        # Scan first 50 pages for the query (keeps it fast and saves tokens)
        for i in range(min(len(reader.pages), 50)):
            text = reader.pages[i].extract_text()
            if query.lower() in text.lower():
                context += text + "\n"
                if len(context) > 4000: break # Token safety limit
        return context if context else "No specific match found in manual text."
    except Exception as e:
        return f"Error reading PDF: {e}"

# --- 4. USER INTERFACE ---
st.title("👨‍🔧 Siemens SINUMERIK 840D Intelligence Agent")
st.info("This agent connects your SQL Defect Logs with Siemens Technical Manuals.")

tab1, tab2 = st.tabs(["💬 AI Troubleshooting", "📊 Database Search"])

with tab1:
    st.subheader("Ask a Maintenance Question")
    user_query = st.text_input("Example: 'How do I fix Alarm 61303?' or 'Analyze product 10'")
    
    if user_query:
        if model:
            with st.spinner("Analyzing manuals and logs..."):
                # Step 1: Get data from PDF
                manual_data = extract_manual_context(user_query)
                
                # Step 2: Get data from SQL if a number is mentioned
                db_context = ""
                if any(char.isdigit() for char in user_query):
                    db_context = str(query_factory_db(user_query).to_dict())

                # Step 3: Generate Response
                prompt = f"""
                You are a Senior Maintenance Engineer. 
                Manual Context: {manual_data}
                Database Context: {db_context}
                
                User Question: {user_query}
                
                Provide a professional remedy. If a specific alarm code is found, 
                explain exactly what the worker should check on the machine.
                """
                try:
                    response = model.generate_content(prompt)
                    st.chat_message("assistant").write(response.text)
                except Exception as e:
                    if "429" in str(e):
                        st.warning("Quota reached. Please wait 30 seconds.")
                    else:
                        st.error(f"AI Error: {e}")
        else:
            st.warning("AI Model not initialized. Check your API Key.")

with tab2:
    st.subheader("Machine Defect Logs (SQLite)")
    search_id = st.text_input("Enter Product or Defect ID:")
    if search_id:
        results = query_factory_db(search_id)
        st.table(results)

# --- 5. SIDEBAR PORTFOLIO INFO ---
with st.sidebar:
    st.header("Project Architecture")
    st.markdown("""
    **Data Stack:**
    - **Python** (Streamlit)
    - **SQLite** (Structured Logs)
    - **PyPDF** (Unstructured Manuals)
    - **Gemini 1.5 Flash** (RAG Engine)
    
    *Note: This app is optimized for mobile browser use on the factory floor.*
    """)


