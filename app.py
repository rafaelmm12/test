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

# --- PAGE CONFIG ---
st.set_page_config(page_title="Factory Helper Agent", page_icon="⚙️", layout="wide")

# --- SECRETS & AI SETUP ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.sidebar.error("⚠️ Missing API Key in Secrets!")

# --- DATA FUNCTIONS ---
def extract_pdf_context(query):
    """Simple search to find relevant pages in the PDF manual."""
    context = ""
    try:
        # We'll prioritize the Diagnostics Manual for error codes
        reader = pypdf.PdfReader("diagnostics_manual-sinumerik 840d.pdf")
        # To save tokens, we only send pages that mention the user's query
        for page in reader.pages[:100]: # Limit to first 100 pages for performance
            text = page.extract_text()
            if query.lower() in text.lower():
                context += text + "\n"
                if len(context) > 5000: break # Don't overload the prompt
    except Exception as e:
        context = "Error reading manuals: " + str(e)
    return context

def query_db(search_term):
    conn = sqlite3.connect('factory_data.db')
    # Use parameterized query to prevent SQL injection
    query = "SELECT * FROM defects WHERE defect_id = ? OR product_id = ?"
    df = pd.read_sql(query, conn, params=(search_term, search_term))
    conn.close()
    return df

def get_ai_response(prompt, context_data):
    # Using 'gemini-1.5-flash' with the models/ prefix is the most stable
    model = genai.GenerativeModel('models/gemini-1.5-flash')
    full_prompt = f"Use this manual context: {context_data}\n\nAnswer this: {prompt}"
    response = model.generate_content(full_prompt)
    return response.text

# --- USER INTERFACE ---
st.title("👨‍🔧 Maintenance Helper Agent")

tab1, tab2 = st.tabs(["💬 AI Helper", "📊 Machine Data"])

with tab1:
    st.subheader("Technical Troubleshooting")
    query = st.text_input("Ask about an alarm code or defect procedure:")
    
    if query:
        with st.spinner("Searching manuals and generating solution..."):
            manual_context = extract_pdf_context(query)
            answer = get_ai_response(query, manual_context)
            st.chat_message("assistant").write(answer)

with tab2:
    st.subheader("Defect Database")
    search = st.text_input("Enter Defect ID or Product ID")
    if search:
        data = query_db(search)
        if not data.empty:
            st.dataframe(data)
        else:
            st.warning("No records found.")
