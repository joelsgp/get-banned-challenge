import os
import mysql.connector

from urllib.parse import urlparse


def mysql_connect(database_url=os.environ["JAWSDB_URL"]):
    """Connect to sql database.

    Args:
        database_url -- url as a string, should include username, password, host and database
    Returns conn, cur
    """
    # Split the whole URL into the needed components.
    jdb_uri = urlparse(database_url)

    conn = mysql.connector.connect(
        user=jdb_uri.username,
        password=jdb_uri.password,
        host=jdb_uri.hostname,
        database=jdb_uri.path.replace("/", "")
    )
    cur = conn.cursor(buffered=True)
    return conn, cur


def mysql_disconnect(conn, cur):
    """Close a db connection."""
    cur.close()
    conn.close()
