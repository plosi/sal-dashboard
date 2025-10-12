import polars as pl
from .db import get_db_connection
import xlsxwriter
import fastexcel
import os

excel_file = os.path.join(os.getcwd(),"data","database.xlsx")
db_file = os.path.join(os.getcwd(),"data","db.duckdb")


def import_excel_to_db(file_path: str):
    # Read the excel file
    wb = fastexcel.read_excel(file_path)
    
    # Make a dictionary of dataframes
    dfs = {}
    for sheet in wb.sheet_names:
        dfs.update({f"{sheet}":wb.load_sheet(sheet).to_polars()})

    # Get a database connection
    conn = get_db_connection()
  
    # Iterate over each sheet and import into the database
    for sheet, df in dfs.items():
        # Register the dataframe as a temporary table
        conn.register("tmp_df", df)
        # Create or replace the table in the database
        conn.execute(f"CREATE OR REPLACE TABLE {sheet.lower()} AS SELECT * FROM tmp_df")

    # Commit and close the connection
    conn.commit()
    conn.close()

def ensure_sequences():
    """
    Ensures all ID sequences exist and are aligned with table data.
    If missing, creates them from scratch.
    """
    conn = get_db_connection()
    seqs = {
        "advisors": "advisors_id_seq",
        "departments": "departments_id_seq",
        "calendar": "calendar_id_seq",
        "timesheet": "timesheet_id_seq",
        "construction_risk_matrix": "matrix_id_seq",
        "proposals": "proposals_id_seq",
        "country_focals": "country_focals_id_seq"
    }

    for table, seq in seqs.items():
        # 1️⃣ Get current max(id)
        max_id = conn.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table}").fetchone()[0]
        next_val = int(max_id) + 1

        # 2️⃣ Check if sequence exists
        exists = conn.execute(
            f"SELECT COUNT(*) FROM duckdb_sequences() WHERE sequence_name = '{seq}'"
        ).fetchone()[0] > 0

        # 3️⃣ Drop and recreate if needed
        if exists:
            conn.execute(f"DROP SEQUENCE {seq}")
            print(f"🔁 Recreated existing sequence {seq}")
        else:
            print(f"🆕 Created new sequence {seq}")

        conn.execute(f"CREATE SEQUENCE {seq} START {next_val}")
        conn.execute(f"ALTER TABLE {table} ALTER COLUMN id SET DEFAULT nextval('{seq}')")

    print("✅ All sequences exist and are synced to current data.")


def export_db_to_excel(file_path: str):
    # Get a database connection
    conn = get_db_connection()

    # Fetch all table names from the database
    tables = conn.execute("SHOW TABLES").pl()["name"].to_list()
    print(tables)
    
    # Write each table to a separate sheet in the Excel file
    with xlsxwriter.Workbook(file_path) as wb:
        for table in tables:
            df = conn.execute(f"SELECT * FROM {table}").pl()
            df.write_excel(workbook=wb, worksheet=table)
    
    # Commit and close the connection
    conn.commit()
    conn.close()


# Example usage:
# export_db_to_excel("from_polars.xlsx")
# import_excel_to_db(excel_file)
# ensure_sequences()