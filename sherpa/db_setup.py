import sqlite3
import os
from datetime import datetime

from config import DB_PATH

def create_connection():
    """Create a database connection to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        print(f"Connected to {DB_PATH}")
        return conn
    except sqlite3.Error as e:
        print(e)
    return conn

def create_table(conn):
    """Create the leads table."""
    create_leads_table_sql = """
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        linkedin_url TEXT NOT NULL UNIQUE,
        first_name TEXT,
        last_name TEXT,
        email TEXT,
        phone TEXT,
        company TEXT,
        title TEXT,
        location TEXT,
        status TEXT DEFAULT 'New',
        verification_status TEXT,
        draft_email_subject TEXT,
        draft_email_body TEXT,
        draft_linkedin_note TEXT,
        draft_whatsapp_nudge TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    create_examples_table_sql = """
    CREATE TABLE IF NOT EXISTS examples (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT, -- 'Email', 'LinkedIn', 'WhatsApp'
        content TEXT,
        context TEXT, -- Optional notes
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    try:
        c = conn.cursor()
        c.execute(create_leads_table_sql)
        print("Table 'leads' created successfully.")
        c.execute(create_examples_table_sql)
        print("Table 'examples' created successfully.")
    except sqlite3.Error as e:
        print(e)

def add_column_if_not_exists(conn, table, column, col_type):
    try:
        c = conn.cursor()
        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        print(f"Added column {column} to {table}")
    except sqlite3.OperationalError:
        pass # Column likely exists

def setup_database():
    if os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} already exists.")
    
    conn = create_connection()
    if conn:
        create_table(conn)
        # Migration: Add attachment_file column if it doesn't exist
        add_column_if_not_exists(conn, "leads", "attachment_file", "TEXT")
        conn.close()
    else:
        print("Error! cannot create the database connection.")

if __name__ == '__main__':
    setup_database()
