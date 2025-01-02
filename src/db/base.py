import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Generator

from src.config.settings import settings

def get_db_connection():
    """Create a database connection"""
    return psycopg2.connect(
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        cursor_factory=RealDictCursor
    )

@contextmanager
def get_db() -> Generator:
    """Database connection context manager"""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()

def execute_query(conn, query: str, params: tuple = None):
    """Execute a query and return results"""
    with conn.cursor() as cur:
        cur.execute(query, params)
        try:
            return cur.fetchall()
        except psycopg2.ProgrammingError:
            return None

def execute_query_single(conn, query: str, params: tuple = None):
    """Execute a query and return a single result"""
    with conn.cursor() as cur:
        cur.execute(query, params)
        try:
            return cur.fetchone()
        except psycopg2.ProgrammingError:
            return None
