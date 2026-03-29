import sqlite3

import pytest

from app.database import init_db_with_connection


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db_with_connection(conn)
    yield conn
    conn.close()
