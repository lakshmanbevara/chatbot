
"""
Database module for Zyren Personal Assistant.
Handles SQLite storage for conversation sessions, message history,
and persistent long-term memories.
"""

import sqlite3
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from config import DB_PATH

def get_connection():
    """Get a SQLite connection with dict-like row access."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables if they do not exist."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Conversations / Chat Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
            )
        """)
        
        # Long-term persistent memories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
        """)
        
        conn.commit()

# --- Conversation Management ---

def create_conversation(title: str = "New Chat") -> str:
    """Create a new conversation session and return its ID."""
    conv_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (conv_id, title, now, now)
        )
        conn.commit()
    return conv_id

def get_conversations() -> List[Dict[str, Any]]:
    """Retrieve all conversations ordered by last update (newest first)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_conversation(conv_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single conversation by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?", (conv_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_conversation_title(conv_id: str, title: str):
    """Update conversation title."""
    now = datetime.now().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, now, conv_id)
        )
        conn.commit()

def delete_conversation(conv_id: str):
    """Delete a conversation and all its associated messages."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        conn.commit()

def search_conversations(query: str) -> List[Dict[str, Any]]:
    """Search conversations by title or message content."""
    clean_q = f"%{query.strip()}%"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT c.id, c.title, c.created_at, c.updated_at 
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE c.title LIKE ? OR m.content LIKE ?
            ORDER BY c.updated_at DESC
        """, (clean_q, clean_q))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def clear_all_conversations():
    """Delete all conversations and their associated messages."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages")
        cursor.execute("DELETE FROM conversations")
        conn.commit()

# --- Message Management ---

def add_message(conv_id: str, role: str, content: str) -> str:
    """Add a message to a conversation and update the conversation's timestamp."""
    msg_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (msg_id, conv_id, role, content, now)
        )
        cursor.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conv_id)
        )
        conn.commit()
    return msg_id

def get_messages(conv_id: str) -> List[Dict[str, Any]]:
    """Retrieve all messages for a given conversation ordered chronologically."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conv_id,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def delete_message(msg_id: str):
    """Delete a single message by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
        conn.commit()

def clear_conversation_messages(conv_id: str):
    """Clear all messages from a conversation while keeping the session."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        conn.commit()

def delete_last_message(conv_id: str):
    """Delete the most recent message in the conversation."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM messages WHERE id = (SELECT id FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 1)",
            (conv_id,)
        )
        conn.commit()

# --- Long-Term Memory Management ---

def add_memory(fact: str) -> bool:
    """Save a user fact to persistent long-term memory."""
    cleaned = fact.strip()
    if not cleaned:
        return False
    now = datetime.now().isoformat()
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO memories (fact, created_at) VALUES (?, ?)",
                (cleaned, now)
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception:
        return False

def get_all_memories() -> List[Dict[str, Any]]:
    """Get all saved memories."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, fact, created_at FROM memories ORDER BY id DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def delete_memory(memory_id: int):
    """Delete a single memory by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        conn.commit()

def clear_all_memories():
    """Clear all saved memories."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories")
        conn.commit()

# Initialize DB on load
init_db()

