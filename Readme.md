python -m venv venv // python3 -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
venv\Scripts\activate // source venv/bin/activate
pip install streamlit pandas openpyxl pdfplumber
streamlit run app.py