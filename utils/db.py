import duckdb
import polars as pl
# from pathlib import Path
import os

# DB_PATH = Path("data/db.duckdb")
DB_PATH = os.path.join(os.getcwd(),"data","db.duckdb")

def get_db_connection():
    return duckdb.connect(database=str(DB_PATH), read_only=False)


def initialize_db():
    conn = get_db_connection()

    conn.execute("""
    CREATE SEQUENCE IF NOT EXISTS advisors_id_seq START 1;
    
    CREATE TABLE IF NOT EXISTS advisors (
        id INTEGER PRIMARY KEY DEFAULT nextval('advisors_id_seq'),
        department_code TEXT NOT NULL,
        name TEXT NOT NULL,
        short_name TEXT NOT NULL,
        role TEXT,
        email TEXT,
        active BOOLEAN DEFAULT TRUE,
        country_code TEXT,
        colour TEXT(7)
    );
    """)

    conn.execute("""
    CREATE SEQUENCE IF NOT EXISTS departments_id_seq START 1;
    
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY DEFAULT nextval('departments_id_seq'),
        name TEXT NOT NULL,
        code TEXT NOT NULL,
        icon TEXT
    );
    """)

    conn.execute("""
    CREATE SEQUENCE IF NOT EXISTS calendar_id_seq START 1;
    
    CREATE TABLE IF NOT EXISTS calendar (
        id INTEGER PRIMARY KEY DEFAULT nextval('calendar_id_seq'),
        department_code TEXT NOT NULL,
        advisor_short_name TEXT NOT NULL,
        start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        event_name TEXT NOT NULL,
        notes TEXT
    );
    """)

    conn.execute("""
    CREATE SEQUENCE IF NOT EXISTS timesheet_id_seq START 1;
    
    CREATE TABLE IF NOT EXISTS timesheet (
        id INTEGER PRIMARY KEY DEFAULT nextval('timesheet_id_seq'),
        department_code TEXT NOT NULL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        country_name TEXT NOT NULL,
        sal_attendees TEXT NOT NULL,
        country_attendees TEXT NOT NULL,
        support_name TEXT NOT NULL,
        description TEXT,
        hours FLOAT DEFAULT 1.0
    );
    """)

    conn.execute("""
    CREATE SEQUENCE IF NOT EXISTS matrix_id_seq START 1;
    
    CREATE TABLE IF NOT EXISTS construction_risk_matrix (
        id INTEGER PRIMARY KEY DEFAULT nextval('matrix_id_seq'),
        country_name TEXT NOT NULL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        score INT NOT NULL,
        description TEXT,
        remarks TEXT
    );
    """)

    conn.execute("""
    CREATE SEQUENCE IF NOT EXISTS proposals_id_seq START 1;
    
    CREATE TABLE IF NOT EXISTS proposals (
        id INTEGER PRIMARY KEY DEFAULT nextval('proposals_id_seq'),
        department_code TEXT NOT NULL,
        type TEXT NOT NULL,
        country_name TEXT NOT NULL,
        donor TEXT,
        date_submission TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        result BOOLEAN DEFAULT FALSE,
        sal_support TEXT,
        country_focal TEXT,
        description TEXT
    );
    """)

    conn.execute("""
    CREATE SEQUENCE IF NOT EXISTS country_focals_id_seq START 1;
    
    CREATE TABLE IF NOT EXISTS country_focals (
        id INTEGER PRIMARY KEY DEFAULT nextval('country_focals_id_seq'),
        department_code TEXT NOT NULL,
        name TEXT NOT NULL,
        country_name TEXT NOT NULL,
        role TEXT,
        email TEXT
    );
    """)

    conn.execute("""   
    CREATE TABLE IF NOT EXISTS countries (
        iso_alpha3_code TEXT(3) PRIMARY KEY,
        name TEXT NOT NULL,
        continent TEXT NOT NULL
    );
    """)

    conn.execute("""   
    CREATE TABLE IF NOT EXISTS events (
        name TEXT NOT NULL,
        description TEXT,
        colour TEXT(7)
    );
    """)

    conn.execute("""   
    CREATE TABLE IF NOT EXISTS support (
        category TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        colour TEXT(7)
    );
    """)

    conn.commit()
    conn.close()


# # ----------------------------
# # Helper: check if row exists
# # ----------------------------
# def row_exists(table: str, where: str) -> bool:
#     conn = get_db_connection()
#     result = conn.execute(f"SELECT COUNT(*) as c FROM {table} WHERE {where}").fetchone()[0]
#     conn.close()
#     return result > 0

# ---------------------------------------------
# CRUD FUNCTIONS (Polars-based with validation)
# ---------------------------------------------

# CREATE
def insert_row(table: str, row: dict):
    # Remove 'id' if it exists in the row dict, so that it auto-increments
    row = {k: v for k, v in row.items() if k != 'id'}

    conn = get_db_connection()
    cols = ", ".join(row.keys())
    placeholders = ", ".join(["?"] * len(row))
    sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
    conn.execute(sql, list(row.values()))
    conn.close()

# READ
def read_table(table: str, where: str=None) -> pl.DataFrame:
    conn = get_db_connection()
    sql = f"SELECT * FROM {table}"
    if where:
        sql += f" WHERE {where}"
    # Return a Polars DataFrame
    df = conn.execute(sql).pl()
    conn.close()
    return df
    

# UPDATE
def update_row(table: str, updates: dict, where: str):
    conn = get_db_connection()
    set_clause = ", ".join([f"{col} = ?" for col in updates.keys()])
    sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
    conn.execute(sql, list(updates.values()))
    conn.close()

# DELETE
def delete_row(table: str, where: str):
    conn = get_db_connection()
    sql = f"DELETE FROM {table} WHERE {where}"
    conn.execute(sql)
    conn.close()