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
import pypdf

# --- PAGE CONFIG ---
st.set_page_config(page_title="Factory Helper Agent", page_icon="⚙️", layout="wide")

# --- SECRETS & AI SETUP ---
# You'll set this key in the Streamlit Cloud sidebar settings
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Missing GEMINI_API_KEY. Please add it to Streamlit Secrets.")

# --- DATA FUNCTIONS ---
def query_db(search_term):
    """Search for defects by ID or Type in the SQLite DB."""
    conn = sqlite3.connect('factory_data.db')
    query = f"SELECT * FROM defects WHERE defect_id='{search_term}' OR product_id='{search_term}'"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def get_ai_response(prompt, context_data):
    """Send user query and data context to Gemini."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    full_prompt = f"Context from Manuals/Data: {context_data}\n\nUser Question: {prompt}"
    response = model.generate_content(full_prompt)
    return response.text

# --- USER INTERFACE ---
st.title("👨‍🔧 Maintenance Helper Agent")
st.markdown("Get machine maintenance data and troubleshooting advice directly from the official manuals.")

tab1, tab2 = st.tabs(["💬 AI Helper", "📊 Machine Data"])

with tab1:
    st.subheader("Ask the Expert")
    query = st.text_input("Example: 'What is the remedy for Alarm 27001?' or 'Explain defect 4'")
    
    if query:
        with st.spinner("Analyzing manuals..."):
            # Simple simulation: In a real app, you'd extract PDF text here
            # For the demo, we use the enriched data we built
            answer = get_ai_response(query, "Reference: SINUMERIK 840D sl Diagnostics Manual")
            st.chat_message("assistant").write(answer)

with tab2:
    st.subheader("Defect Database")
    search = st.text_input("Search by Defect or Product ID")
    if search:
        data = query_db(search)
        st.dataframe(data)