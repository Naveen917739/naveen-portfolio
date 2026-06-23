"""
database.py — Smart dual-mode data layer for Naveen Nimmala Portfolio

- On LOCAL (Windows with SQL Server): uses pyodbc + SQL Server
- On RENDER / cloud (Linux): uses SQLite automatically

No config needed — auto-detects the environment.
"""

import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager

# ─── Environment Detection ─────────────────────────────────────────────
# Use SQLite on Render/Linux, SQL Server on Windows local
USE_SQLITE = os.environ.get('USE_SQLITE', '') == '1' or not os.path.exists('C:\\')

if not USE_SQLITE:
    try:
        import pyodbc
        SQL_SERVER   = os.environ.get('SQL_SERVER', 'localhost')
        SQL_DATABASE = os.environ.get('SQL_DATABASE', 'PortfolioDB')
        SQL_DRIVER   = os.environ.get('SQL_DRIVER', 'ODBC Driver 17 for SQL Server')
        SQL_USER     = os.environ.get('SQL_USER', '')
        SQL_PASSWORD = os.environ.get('SQL_PASSWORD', '')
        if SQL_USER:
            CONN_STRING = (
                f"DRIVER={{{SQL_DRIVER}}};SERVER={SQL_SERVER};"
                f"DATABASE={SQL_DATABASE};UID={SQL_USER};PWD={SQL_PASSWORD};"
            )
        else:
            CONN_STRING = (
                f"DRIVER={{{SQL_DRIVER}}};SERVER={SQL_SERVER};"
                f"DATABASE={SQL_DATABASE};Trusted_Connection=yes;"
            )
    except ImportError:
        USE_SQLITE = True

SQLITE_PATH = os.environ.get('SQLITE_PATH', 'portfolio.db')

# ─── SQLite Helpers ────────────────────────────────────────────────────
@contextmanager
def _sqlite_conn():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

# ─── SQL Server Helpers ────────────────────────────────────────────────
@contextmanager
def _sqlserver_conn():
    conn = pyodbc.connect(CONN_STRING)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def get_db():
    return _sqlite_conn() if USE_SQLITE else _sqlserver_conn()

# ─── Init ──────────────────────────────────────────────────────────────
def init_db():
    if USE_SQLITE:
        with _sqlite_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inquiries (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
                    name         TEXT    NOT NULL,
                    email        TEXT    NOT NULL,
                    phone        TEXT,
                    business     TEXT,
                    service_type TEXT,
                    budget       TEXT,
                    message      TEXT    NOT NULL,
                    status       TEXT    NOT NULL DEFAULT 'New',
                    notes        TEXT    DEFAULT ''
                )
            """)
    else:
        with _sqlserver_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                IF NOT EXISTS (
                    SELECT * FROM sysobjects WHERE name='inquiries' AND xtype='U'
                )
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
            """)

def _row_to_dict(row):
    d = dict(row) if USE_SQLITE else {
        'id': row.id, 'created_at': row.created_at, 'name': row.name,
        'email': row.email, 'phone': row.phone, 'business': row.business,
        'service_type': row.service_type, 'budget': row.budget,
        'message': row.message, 'status': row.status, 'notes': row.notes or '',
    }
    if isinstance(d.get('created_at'), datetime):
        d['created_at'] = d['created_at'].isoformat()
    return d

# ─── CRUD ──────────────────────────────────────────────────────────────
def add_inquiry(data: dict) -> int:
    sql = """
        INSERT INTO inquiries (name, email, phone, business, service_type, budget, message)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    vals = (
        data['name'], data['email'], data.get('phone'), data.get('business'),
        data.get('service_type'), data.get('budget'), data['message'],
    )
    if USE_SQLITE:
        with _sqlite_conn() as conn:
            cur = conn.execute(sql, vals)
            return cur.lastrowid
    else:
        with _sqlserver_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql.replace('VALUES', 'OUTPUT INSERTED.id VALUES'), vals)
            return cur.fetchone()[0]

def get_all_inquiries(status_filter=None, search=None):
    if USE_SQLITE:
        with _sqlite_conn() as conn:
            q = "SELECT * FROM inquiries WHERE 1=1"
            p = []
            if status_filter:
                q += " AND status=?"; p.append(status_filter)
            if search:
                q += " AND (name LIKE ? OR email LIKE ? OR business LIKE ?)"
                p += [f'%{search}%'] * 3
            q += " ORDER BY created_at DESC"
            return [_row_to_dict(r) for r in conn.execute(q, p).fetchall()]
    else:
        with _sqlserver_conn() as conn:
            cur = conn.cursor()
            q = "SELECT * FROM inquiries WHERE 1=1"
            p = []
            if status_filter:
                q += " AND status=?"; p.append(status_filter)
            if search:
                q += " AND (name LIKE ? OR email LIKE ? OR business LIKE ?)"
                p += [f'%{search}%'] * 3
            q += " ORDER BY created_at DESC"
            cur.execute(q, p)
            return [_row_to_dict(r) for r in cur.fetchall()]

def get_inquiry(inquiry_id: int):
    with get_db() as conn:
        if USE_SQLITE:
            row = conn.execute("SELECT * FROM inquiries WHERE id=?", (inquiry_id,)).fetchone()
        else:
            cur = conn.cursor()
            cur.execute("SELECT * FROM inquiries WHERE id=?", (inquiry_id,))
            row = cur.fetchone()
        return _row_to_dict(row) if row else None

def update_status(inquiry_id: int, status: str):
    with get_db() as conn:
        if USE_SQLITE:
            conn.execute("UPDATE inquiries SET status=? WHERE id=?", (status, inquiry_id))
        else:
            conn.cursor().execute("UPDATE inquiries SET status=? WHERE id=?", (status, inquiry_id))

def update_notes(inquiry_id: int, notes: str):
    with get_db() as conn:
        if USE_SQLITE:
            conn.execute("UPDATE inquiries SET notes=? WHERE id=?", (notes, inquiry_id))
        else:
            conn.cursor().execute("UPDATE inquiries SET notes=? WHERE id=?", (notes, inquiry_id))

def delete_inquiry(inquiry_id: int):
    with get_db() as conn:
        if USE_SQLITE:
            conn.execute("DELETE FROM inquiries WHERE id=?", (inquiry_id,))
        else:
            conn.cursor().execute("DELETE FROM inquiries WHERE id=?", (inquiry_id,))

def get_stats():
    with get_db() as conn:
        if USE_SQLITE:
            rows = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status='New' THEN 1 ELSE 0 END) as new,
                    SUM(CASE WHEN status='Contacted' THEN 1 ELSE 0 END) as contacted,
                    SUM(CASE WHEN status='Won' THEN 1 ELSE 0 END) as won,
                    SUM(CASE WHEN status='Lost' THEN 1 ELSE 0 END) as lost
                FROM inquiries
            """).fetchone()
            return dict(rows)
        else:
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status='New' THEN 1 ELSE 0 END) as new,
                    SUM(CASE WHEN status='Contacted' THEN 1 ELSE 0 END) as contacted,
                    SUM(CASE WHEN status='Won' THEN 1 ELSE 0 END) as won,
                    SUM(CASE WHEN status='Lost' THEN 1 ELSE 0 END) as lost
                FROM inquiries
            """)
            row = cur.fetchone()
            return {'total': row[0], 'new': row[1], 'contacted': row[2], 'won': row[3], 'lost': row[4]}
