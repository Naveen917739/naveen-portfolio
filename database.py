"""
database.py — SQL Server data layer for Naveen Nimmala Portfolio

Connects to a local SQL Server instance (via Windows Authentication by
default) and stores every contact-form lead in the `inquiries` table.

PREREQUISITES (one-time setup in SSMS before running the app):

    CREATE DATABASE PortfolioDB;
    GO
    USE PortfolioDB;
    GO
    CREATE TABLE inquiries (
        id            INT IDENTITY(1,1) PRIMARY KEY,
        created_at    DATETIME      NOT NULL DEFAULT GETDATE(),
        name          NVARCHAR(200) NOT NULL,
        email         NVARCHAR(200) NOT NULL,
        phone         NVARCHAR(50),
        business      NVARCHAR(200),
        service_type  NVARCHAR(100),
        budget        NVARCHAR(100),
        message       NVARCHAR(MAX) NOT NULL,
        status        NVARCHAR(20)  NOT NULL DEFAULT 'New',
        notes         NVARCHAR(MAX) DEFAULT ''
    );
    GO

Requires the "ODBC Driver 17 (or 18) for SQL Server" to be installed on
Windows (usually already present, or installed alongside SQL Server /
SSMS). If missing, download from Microsoft's ODBC driver page.
"""

import pyodbc
import os
from datetime import datetime
from contextlib import contextmanager

# ─── Connection Configuration ─────────────────────────────────────────
# Override any of these via environment variables for flexibility.
SQL_SERVER   = os.environ.get('SQL_SERVER', 'localhost')
SQL_DATABASE = os.environ.get('SQL_DATABASE', 'PortfolioDB')
SQL_DRIVER   = os.environ.get('SQL_DRIVER', '{ODBC Driver 17 for SQL Server}')

# Windows Authentication (Trusted_Connection) by default — matches SSMS.
# If you prefer SQL Server Authentication, set SQL_USER / SQL_PASSWORD env vars.
SQL_USER     = os.environ.get('SQL_USER', '')
SQL_PASSWORD = os.environ.get('SQL_PASSWORD', '')

if SQL_USER and SQL_PASSWORD:
    CONN_STRING = (
        f"DRIVER={SQL_DRIVER};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
        f"UID={SQL_USER};PWD={SQL_PASSWORD};"
    )
else:
    CONN_STRING = (
        f"DRIVER={SQL_DRIVER};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
        f"Trusted_Connection=yes;"
    )


# ─── Connection Helper ────────────────────────────────────────────────

@contextmanager
def get_db():
    """Context-managed pyodbc connection."""
    conn = pyodbc.connect(CONN_STRING)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─── Schema Setup ─────────────────────────────────────────────────────

def init_db():
    """
    Verify the inquiries table exists; create it if missing.
    The database itself (PortfolioDB) must already exist — see module
    docstring for the one-time SSMS setup script.
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='inquiries' AND xtype='U')
            CREATE TABLE inquiries (
                id            INT IDENTITY(1,1) PRIMARY KEY,
                created_at    DATETIME      NOT NULL DEFAULT GETDATE(),
                name          NVARCHAR(200) NOT NULL,
                email         NVARCHAR(200) NOT NULL,
                phone         NVARCHAR(50),
                business      NVARCHAR(200),
                service_type  NVARCHAR(100),
                budget        NVARCHAR(100),
                message       NVARCHAR(MAX) NOT NULL,
                status        NVARCHAR(20)  NOT NULL DEFAULT 'New',
                notes         NVARCHAR(MAX) DEFAULT ''
            )
        ''')


# ─── CRUD Operations ───────────────────────────────────────────────────

VALID_STATUSES = ('New', 'Contacted', 'Won', 'Lost')


def _row_to_dict(cursor, row) -> dict:
    """Convert a pyodbc row to a plain dict using cursor.description for column names."""
    columns = [col[0] for col in cursor.description]
    d = dict(zip(columns, row))
    # Normalize datetime to an ISO-like string so templates/JS behave the same as before
    if isinstance(d.get('created_at'), datetime):
        d['created_at'] = d['created_at'].isoformat(timespec='seconds')
    return d


def add_inquiry(data: dict) -> int:
    """Insert a new lead. Returns the new row's id."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO inquiries
                (name, email, phone, business, service_type, budget, message, status)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?, 'New')
        ''', (
            data['name'], data['email'], data.get('phone', ''),
            data.get('business', ''), data.get('service_type', ''),
            data.get('budget', ''), data['message'],
        ))
        new_id = cur.fetchone()[0]
        return new_id


def get_all_inquiries(status_filter: str = None, search: str = None) -> list:
    """Return all inquiries, newest first. Optionally filter by status and/or search text."""
    query = 'SELECT * FROM inquiries WHERE 1=1'
    params = []

    if status_filter and status_filter != 'All':
        query += ' AND status = ?'
        params.append(status_filter)

    if search:
        query += ' AND (name LIKE ? OR email LIKE ? OR business LIKE ? OR message LIKE ?)'
        like = f'%{search}%'
        params.extend([like, like, like, like])

    query += ' ORDER BY created_at DESC'

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        return [_row_to_dict(cur, r) for r in rows]


def get_inquiry(inquiry_id: int) -> dict:
    """Fetch a single inquiry by id."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('SELECT * FROM inquiries WHERE id = ?', (inquiry_id,))
        row = cur.fetchone()
        return _row_to_dict(cur, row) if row else None


def update_status(inquiry_id: int, status: str) -> bool:
    """Update an inquiry's status. Returns True if a row was changed."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of {VALID_STATUSES}")
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('UPDATE inquiries SET status = ? WHERE id = ?', (status, inquiry_id))
        return cur.rowcount > 0


def update_notes(inquiry_id: int, notes: str) -> bool:
    """Update the internal notes field for an inquiry."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('UPDATE inquiries SET notes = ? WHERE id = ?', (notes, inquiry_id))
        return cur.rowcount > 0


def delete_inquiry(inquiry_id: int) -> bool:
    """Permanently delete an inquiry."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('DELETE FROM inquiries WHERE id = ?', (inquiry_id,))
        return cur.rowcount > 0


def get_stats() -> dict:
    """Return summary counts for the dashboard header."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM inquiries')
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM inquiries WHERE status = 'New'")
        new = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM inquiries WHERE status = 'Contacted'")
        contacted = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM inquiries WHERE status = 'Won'")
        won = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM inquiries WHERE status = 'Lost'")
        lost = cur.fetchone()[0]
        return {'total': total, 'new': new, 'contacted': contacted, 'won': won, 'lost': lost}
