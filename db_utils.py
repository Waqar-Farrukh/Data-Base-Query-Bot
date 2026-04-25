"""
db_utils.py — Database Utility Functions
==========================================
Provides helper functions for:
  1. Extracting the database schema (tables, columns, types, foreign keys)
  2. Executing SQL queries safely (read-only, SELECT-only enforcement)

These utilities are used by both the LLM engine and the Streamlit UI.
"""

import sqlite3
import os
import re
from typing import Optional

DB_NAME = "company.db"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_NAME)


# ── Dangerous SQL keywords that should NEVER appear in user-triggered queries ──
BLOCKED_KEYWORDS = [
    "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE",
    "TRUNCATE", "REPLACE", "ATTACH", "DETACH", "PRAGMA",
    "GRANT", "REVOKE", "EXEC", "EXECUTE",
]


def get_schema(db_path: Optional[str] = None) -> str:
    """
    Extract the complete database schema as a formatted string.

    Returns a human-readable representation of all tables, their columns,
    data types, constraints, and foreign key relationships. This string
    is designed to be injected into the LLM's system prompt so it
    understands the database structure.

    Args:
        db_path: Path to the SQLite database. Defaults to company.db.

    Returns:
        A formatted string describing the full database schema.
    """
    db_path = db_path or DB_PATH
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    schema_parts = []

    # Get all table names
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
    ).fetchall()

    for (table_name,) in tables:
        # Get column info using PRAGMA
        columns = cursor.execute(f"PRAGMA table_info({table_name});").fetchall()
        # columns: (cid, name, type, notnull, dflt_value, pk)

        # Get foreign key info
        fkeys = cursor.execute(f"PRAGMA foreign_key_list({table_name});").fetchall()
        # fkeys: (id, seq, table, from, to, on_update, on_delete, match)

        # Build column descriptions
        col_lines = []
        for col in columns:
            cid, col_name, col_type, notnull, default, pk = col
            parts = [f"    {col_name} {col_type}"]
            if pk:
                parts.append("PRIMARY KEY")
            if notnull and not pk:
                parts.append("NOT NULL")
            if default is not None:
                parts.append(f"DEFAULT {default}")
            col_lines.append(" ".join(parts))

        # Build foreign key descriptions
        fk_lines = []
        for fk in fkeys:
            _, _, ref_table, from_col, to_col, *_ = fk
            fk_lines.append(f"    FOREIGN KEY ({from_col}) → {ref_table}({to_col})")

        # Get row count for context
        count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

        # Assemble table description
        table_desc = f"TABLE: {table_name} ({count} rows)\n"
        table_desc += "  Columns:\n" + "\n".join(col_lines)
        if fk_lines:
            table_desc += "\n  Relationships:\n" + "\n".join(fk_lines)

        schema_parts.append(table_desc)

    conn.close()
    return "\n\n".join(schema_parts)


def get_schema_dict(db_path: Optional[str] = None) -> dict:
    """
    Extract the database schema as a structured dictionary.

    Used by the Streamlit sidebar to render a clean schema display.

    Returns:
        Dict mapping table names to lists of column info dicts.
    """
    db_path = db_path or DB_PATH
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    schema = {}

    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
    ).fetchall()

    for (table_name,) in tables:
        columns = cursor.execute(f"PRAGMA table_info({table_name});").fetchall()
        fkeys = cursor.execute(f"PRAGMA foreign_key_list({table_name});").fetchall()
        count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

        # Build FK lookup: from_col → ref_table(to_col)
        fk_map = {}
        for fk in fkeys:
            _, _, ref_table, from_col, to_col, *_ = fk
            fk_map[from_col] = f"→ {ref_table}({to_col})"

        col_list = []
        for col in columns:
            cid, col_name, col_type, notnull, default, pk = col
            col_info = {
                "name": col_name,
                "type": col_type,
                "pk": bool(pk),
                "notnull": bool(notnull),
                "fk": fk_map.get(col_name),
            }
            col_list.append(col_info)

        schema[table_name] = {"columns": col_list, "row_count": count}

    conn.close()
    return schema


def validate_query(sql: str) -> tuple[bool, str]:
    """
    Validate that a SQL query is safe to execute.

    Safety checks:
      1. Must be a SELECT statement (or WITH ... SELECT for CTEs).
      2. Must NOT contain any blocked keywords (DROP, DELETE, etc.).
      3. Must not contain multiple statements (no semicolons mid-query).

    Args:
        sql: The SQL query string to validate.

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    cleaned = sql.strip().rstrip(";").strip()

    if not cleaned:
        return False, "Empty query."

    # Check it starts with SELECT or WITH (for CTEs)
    upper = cleaned.upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return False, "Only SELECT queries are allowed. The query must start with SELECT."

    # Check for blocked keywords (as whole words, not substrings)
    for keyword in BLOCKED_KEYWORDS:
        # Use word-boundary matching to avoid false positives
        # e.g., "updated_at" should not trigger "UPDATE"
        pattern = rf'\b{keyword}\b'
        if re.search(pattern, upper):
            return False, f"Blocked keyword detected: {keyword}. Only read-only queries are permitted."

    # Check for multiple statements
    # Remove string literals first to avoid false positives with semicolons inside strings
    no_strings = re.sub(r"'[^']*'", "", cleaned)
    if ";" in no_strings:
        return False, "Multiple SQL statements are not allowed."

    return True, ""


def execute_query(sql: str, db_path: Optional[str] = None) -> dict:
    """
    Execute a validated SQL query and return results.

    The connection is opened in read-only mode for additional safety.

    Args:
        sql: The SQL query to execute (must pass validation).
        db_path: Path to the SQLite database. Defaults to company.db.

    Returns:
        Dict with keys:
          - 'success': bool
          - 'columns': list of column names (if success)
          - 'rows': list of tuples (if success)
          - 'row_count': int (if success)
          - 'error': str (if not success)
    """
    db_path = db_path or DB_PATH

    # Step 1: Validate the query
    is_valid, error_msg = validate_query(sql)
    if not is_valid:
        return {"success": False, "error": error_msg}

    # Step 2: Open a READ-ONLY connection for safety
    try:
        # Use URI mode with ?mode=ro to enforce read-only access
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=10)
        cursor = conn.cursor()

        # Execute the query
        cursor.execute(sql)
        columns = [description[0] for description in cursor.description] if cursor.description else []
        rows = cursor.fetchall()

        conn.close()

        return {
            "success": True,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
        }

    except sqlite3.Error as e:
        return {"success": False, "error": f"SQL Error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}
