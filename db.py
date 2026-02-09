"""
Database layer for the ticket management system.
Provides CRUD operations for tickets and comments.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path.home() / ".claude" / "tickets" / "tickets.db"

VALID_STATUSES = {"pending", "in_progress", "ready_to_test", "closed"}
VALID_PRIORITIES = {"high", "medium", "low"}


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database schema if it doesn't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            priority TEXT NOT NULL DEFAULT 'medium',
            tags TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (ticket_id) REFERENCES tickets (id) ON DELETE CASCADE
        )
    """)

    # Create indexes for common queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_project ON tickets (project)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets (status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_ticket ON comments (ticket_id)")

    conn.commit()
    conn.close()


# Initialize on import
init_db()


def now_iso() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now().isoformat()


# ============ Ticket Operations ============

def create_ticket(
    project: str,
    title: str,
    description: str,
    priority: str = "medium",
    tags: str = ""
) -> dict:
    """Create a new ticket and return it."""
    if priority not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority: {priority}. Must be one of {VALID_PRIORITIES}")

    conn = get_connection()
    cursor = conn.cursor()
    now = now_iso()

    cursor.execute("""
        INSERT INTO tickets (project, title, description, status, priority, tags, created_at, updated_at)
        VALUES (?, ?, ?, 'pending', ?, ?, ?, ?)
    """, (project, title, description, priority, tags, now, now))

    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return get_ticket(ticket_id)


def get_ticket(ticket_id: int) -> Optional[dict]:
    """Get a ticket by ID with all its comments."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    ticket = dict(row)

    # Get comments
    cursor.execute(
        "SELECT * FROM comments WHERE ticket_id = ? ORDER BY created_at ASC",
        (ticket_id,)
    )
    ticket["comments"] = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return ticket


def list_tickets(
    project: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    tag: Optional[str] = None
) -> list[dict]:
    """List tickets with optional filters."""
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM tickets WHERE 1=1"
    params = []

    if project:
        query += " AND project = ?"
        params.append(project)

    if status:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")
        query += " AND status = ?"
        params.append(status)

    if priority:
        if priority not in VALID_PRIORITIES:
            raise ValueError(f"Invalid priority: {priority}. Must be one of {VALID_PRIORITIES}")
        query += " AND priority = ?"
        params.append(priority)

    if tag:
        query += " AND (',' || tags || ',') LIKE ?"
        params.append(f"%,{tag},%")

    query += " ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, created_at DESC"

    cursor.execute(query, params)
    tickets = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return tickets


def update_ticket(
    ticket_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[str] = None
) -> Optional[dict]:
    """Update a ticket's fields. Only provided fields are updated."""
    # Check ticket exists
    existing = get_ticket(ticket_id)
    if not existing:
        return None

    updates = []
    params = []

    if title is not None:
        updates.append("title = ?")
        params.append(title)

    if description is not None:
        updates.append("description = ?")
        params.append(description)

    if status is not None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")
        updates.append("status = ?")
        params.append(status)

    if priority is not None:
        if priority not in VALID_PRIORITIES:
            raise ValueError(f"Invalid priority: {priority}. Must be one of {VALID_PRIORITIES}")
        updates.append("priority = ?")
        params.append(priority)

    if tags is not None:
        updates.append("tags = ?")
        params.append(tags)

    if not updates:
        return existing

    updates.append("updated_at = ?")
    params.append(now_iso())
    params.append(ticket_id)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE tickets SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()

    return get_ticket(ticket_id)


def search_tickets(
    query: str,
    project: Optional[str] = None,
    status: Optional[str] = None,
) -> list[dict]:
    """Search tickets by matching query against title, description, tags, and comments."""
    conn = get_connection()
    cursor = conn.cursor()

    sql = """
        SELECT DISTINCT t.* FROM tickets t
        LEFT JOIN comments c ON c.ticket_id = t.id
        WHERE (
            t.title LIKE ?
            OR t.description LIKE ?
            OR t.tags LIKE ?
            OR c.content LIKE ?
        )
    """
    pattern = f"%{query}%"
    params = [pattern, pattern, pattern, pattern]

    if project:
        sql += " AND t.project = ?"
        params.append(project)

    if status:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")
        sql += " AND t.status = ?"
        params.append(status)

    sql += " ORDER BY CASE t.priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, t.created_at DESC"

    cursor.execute(sql, params)
    tickets = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return tickets


def delete_ticket(ticket_id: int) -> bool:
    """Delete a ticket and its comments. Returns True if ticket existed."""
    conn = get_connection()
    cursor = conn.cursor()

    # Delete comments first (foreign key)
    cursor.execute("DELETE FROM comments WHERE ticket_id = ?", (ticket_id,))
    cursor.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))

    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return deleted


# ============ Comment Operations ============

def add_comment(ticket_id: int, author: str, content: str) -> Optional[dict]:
    """Add a comment to a ticket. Returns the comment or None if ticket doesn't exist."""
    # Check ticket exists
    if not get_ticket(ticket_id):
        return None

    conn = get_connection()
    cursor = conn.cursor()
    now = now_iso()

    cursor.execute("""
        INSERT INTO comments (ticket_id, author, content, created_at)
        VALUES (?, ?, ?, ?)
    """, (ticket_id, author, content, now))

    comment_id = cursor.lastrowid

    # Also update the ticket's updated_at
    cursor.execute("UPDATE tickets SET updated_at = ? WHERE id = ?", (now, ticket_id))

    conn.commit()
    conn.close()

    return {"id": comment_id, "ticket_id": ticket_id, "author": author, "content": content, "created_at": now}


def get_comments(ticket_id: int) -> list[dict]:
    """Get all comments for a ticket."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM comments WHERE ticket_id = ? ORDER BY created_at ASC",
        (ticket_id,)
    )
    comments = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return comments
