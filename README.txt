PSDA — Personal Stock Data Analyzer

Requirements: Python 3.10+ recommended

1. Unzip this folder and open it in PyCharm or a terminal.
2. Create a fresh Python virtual environment (optional but recommended):
   python3 -m venv .venv
   source .venv/bin/activate  (macOS/Linux)
   .venv\Scripts\activate  (Windows)
3. Install dependencies:
   python -m pip install -r requirements.txt
4. Run:
   python main.py
5. In your browser, open http://127.0.0.1:5001

If port 5001 is occupied, edit the port at the bottom of main.py.
The included stocks.db is a sample/current local database; remove it if sharing its saved records is not intended.
