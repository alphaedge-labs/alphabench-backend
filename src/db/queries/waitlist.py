from typing import Optional, Dict
import json
from src.db.base import execute_query_single, execute_query
def get_waitlist_entry(conn, email: str) -> Optional[Dict]:
    """Check if email exists in waitlist"""
    return execute_query_single(
        conn,
        """
        SELECT * FROM waitlist_users
        WHERE email = %s
        """,
        (email,)
    )

def create_waitlist_entry(conn, email: str, metadata: Dict) -> Dict:
    """Create new waitlist entry"""
    result = execute_query_single(
        conn,
        """
        INSERT INTO waitlist_users (email, metadata)
        VALUES (%s, %s)
        RETURNING *
        """,
        (email, json.dumps(metadata))
    )
    conn.commit()
    return result

def get_all_waitlist_entries(conn) -> list[Dict]:
    """Get all waitlist entries"""
    return execute_query(
        conn,
        """
        SELECT email, metadata, created_at 
        FROM waitlist_users 
        ORDER BY created_at DESC
        """,
        ()
    ) or []
