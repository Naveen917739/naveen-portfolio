"""
database.py — Smart tri-mode data layer for Naveen Nimmala Portfolio

- RENDER/CLOUD: uses PostgreSQL (Supabase) when DATABASE_URL is set
- LOCAL WINDOWS: uses SQL Server (pyodbc) when available
- FALLBACK: uses SQLite
"""

import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager

# ─── Environment Detection ─────────────────────────────────────────────
DATABASE_URL = os.environ.get('DATABASE_URL', '')  # Set this on Render

if DATABASE_URL:
    MODE = 'postgres'
    import psycopg2
    import psycopg2.extras
elif os.path.exists('C:\\'):
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
        MODE = 'sqlserver'
    except ImportError:
        MODE = 'sqlite'
else:
    MODE = 'sqlite'

SQLITE_PATH = os.environ.get('SQLITE_PATH', 'portfolio.db')

# ─── Connection Helpers ────────────────────────────────────────────────
@contextmanager
def _pg_conn():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

@contextmanager
def _sqlite_conn():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

@contextmanager
def _sqlserver_conn():
    conn = pyodbc.connect(CONN_STRING)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

# ─── Init ──────────────────────────────────────────────────────────────
def init_db():
    if MODE == 'postgres':
        with _pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS inquiries (
                    id           SERIAL PRIMARY KEY,
                    created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
                    name         VARCHAR(200) NOT NULL,
                    email        VARCHAR(200) NOT NULL,
                    phone        VARCHAR(50),
                    business     VARCHAR(200),
                    service_type VARCHAR(100),
                    budget       VARCHAR(100),
                    message      TEXT NOT NULL,
                    status       VARCHAR(20) NOT NULL DEFAULT 'New',
                    notes        TEXT DEFAULT ''
                )
            """)
    elif MODE == 'sqlite':
        with _sqlite_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inquiries (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
                    name         TEXT NOT NULL,
                    email        TEXT NOT NULL,
                    phone        TEXT,
                    business     TEXT,
                    service_type TEXT,
                    budget       TEXT,
                    message      TEXT NOT NULL,
                    status       TEXT NOT NULL DEFAULT 'New',
                    notes        TEXT DEFAULT ''
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

def _row_to_dict(row, cur=None):
    if MODE == 'postgres':
        cols = [desc[0] for desc in cur.description]
        d = dict(zip(cols, row))
    elif MODE == 'sqlite':
        d = dict(row)
    else:
        d = {
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
    vals = (
        data['name'], data['email'], data.get('phone'), data.get('business'),
        data.get('service_type'), data.get('budget'), data['message'],
    )
    if MODE == 'postgres':
        with _pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO inquiries (name,email,phone,business,service_type,budget,message)
                VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """, vals)
            return cur.fetchone()[0]
    elif MODE == 'sqlite':
        with _sqlite_conn() as conn:
            cur = conn.execute("""
                INSERT INTO inquiries (name,email,phone,business,service_type,budget,message)
                VALUES (?,?,?,?,?,?,?)
            """, vals)
            return cur.lastrowid
    else:
        with _sqlserver_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO inquiries (name,email,phone,business,service_type,budget,message)
                OUTPUT INSERTED.id VALUES (?,?,?,?,?,?,?)
            """, vals)
            return cur.fetchone()[0]

def get_all_inquiries(status_filter=None, search=None):
    if MODE == 'postgres':
        with _pg_conn() as conn:
            cur = conn.cursor()
            q = "SELECT * FROM inquiries WHERE 1=1"
            p = []
            if status_filter and status_filter != 'ALL' :
                q += " AND status=%s"; p.append(status_filter)
            if search:
                q += " AND (name ILIKE %s OR email ILIKE %s OR business ILIKE %s)"
                p += [f'%{search}%'] * 3
            q += " ORDER BY created_at DESC"
            cur.execute(q, p)
            rows=cur.fetchall()
            print("Rows FOUND = ",len(rows))
            print("Query =",q)
            print("PARAMS=",p)
            RETURN[_row_to_dict(r,cur) for r in rows]
    elif MODE == 'sqlite':
        with _sqlite_conn() as conn:
            q = "SELECT * FROM inquiries WHERE 1=1"
            p = []
            if status_filter and status_filter != 'ALL':
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
            if status_filter and status_filter != 'ALL':
                q += " AND status=?"; p.append(status_filter)
            if search:
                q += " AND (name LIKE ? OR email LIKE ? OR business LIKE ?)"
                p += [f'%{search}%'] * 3
            q += " ORDER BY created_at DESC"
            cur.execute(q, p)
            return [_row_to_dict(r) for r in cur.fetchall()]

def get_inquiry(inquiry_id: int):
    if MODE == 'postgres':
        with _pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM inquiries WHERE id=%s", (inquiry_id,))
            row = cur.fetchone()
            return _row_to_dict(row, cur) if row else None
    elif MODE == 'sqlite':
        with _sqlite_conn() as conn:
            row = conn.execute("SELECT * FROM inquiries WHERE id=?", (inquiry_id,)).fetchone()
            return _row_to_dict(row) if row else None
    else:
        with _sqlserver_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM inquiries WHERE id=?", (inquiry_id,))
            row = cur.fetchone()
            return _row_to_dict(row) if row else None

def update_status(inquiry_id: int, status: str):
    if MODE == 'postgres':
        with _pg_conn() as conn:
            conn.cursor().execute("UPDATE inquiries SET status=%s WHERE id=%s", (status, inquiry_id))
    elif MODE == 'sqlite':
        with _sqlite_conn() as conn:
            conn.execute("UPDATE inquiries SET status=? WHERE id=?", (status, inquiry_id))
    else:
        with _sqlserver_conn() as conn:
            conn.cursor().execute("UPDATE inquiries SET status=? WHERE id=?", (status, inquiry_id))

def update_notes(inquiry_id: int, notes: str):
    if MODE == 'postgres':
        with _pg_conn() as conn:
            conn.cursor().execute("UPDATE inquiries SET notes=%s WHERE id=%s", (notes, inquiry_id))
    elif MODE == 'sqlite':
        with _sqlite_conn() as conn:
            conn.execute("UPDATE inquiries SET notes=? WHERE id=?", (notes, inquiry_id))
    else:
        with _sqlserver_conn() as conn:
            conn.cursor().execute("UPDATE inquiries SET notes=? WHERE id=?", (notes, inquiry_id))

def delete_inquiry(inquiry_id: int):
    if MODE == 'postgres':
        with _pg_conn() as conn:
            conn.cursor().execute("DELETE FROM inquiries WHERE id=%s", (inquiry_id,))
    elif MODE == 'sqlite':
        with _sqlite_conn() as conn:
            conn.execute("DELETE FROM inquiries WHERE id=?", (inquiry_id,))
    else:
        with _sqlserver_conn() as conn:
            conn.cursor().execute("DELETE FROM inquiries WHERE id=?", (inquiry_id,))

def get_stats():
    sql_pg = """
        SELECT COUNT(*) as total,
            SUM(CASE WHEN status='New' THEN 1 ELSE 0 END) as new,
            SUM(CASE WHEN status='Contacted' THEN 1 ELSE 0 END) as contacted,
            SUM(CASE WHEN status='Won' THEN 1 ELSE 0 END) as won,
            SUM(CASE WHEN status='Lost' THEN 1 ELSE 0 END) as lost
        FROM inquiries
    """
    if MODE == 'postgres':
        with _pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql_pg)
            row = cur.fetchone()
            return {'total': row[0] or 0, 'new': row[1] or 0, 'contacted': row[2] or 0,
                    'won': row[3] or 0, 'lost': row[4] or 0}
    elif MODE == 'sqlite':
        with _sqlite_conn() as conn:
            row = conn.execute(sql_pg).fetchone()
            return {'total': row[0] or 0, 'new': row[1] or 0, 'contacted': row[2] or 0,
                    'won': row[3] or 0, 'lost': row[4] or 0}
    else:
        with _sqlserver_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql_pg)
            row = cur.fetchone()
            return {'total': row[0] or 0, 'new': row[1] or 0, 'contacted': row[2] or 0,
                    'won': row[3] or 0, 'lost': row[4] or 0}
