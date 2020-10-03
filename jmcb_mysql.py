import os
import mysql.connector
from urllib.parse import urlparse


# Function to connect to default main SQL database.
# Returns connection and cursor.
def mysql_connect(database_url=os.environ["JAWSDB_URL"]):
    # Split the whole URL into the needed components.
    jdb_uri = urlparse(database_url)

    # Connect.
    conn= mysql.connector.connect(user=jdb_uri.username,
                                  password=jdb_uri.password,
                                  host=jdb_uri.hostname,
                                  database=jdb_uri.path.replace("/", ""))
    cur = conn.cursor()
    return conn, cur

# Function to close the connection to the database.
# Takes a connection and a cursor as arguments.
def mysql_disconnect(conn, cur):
    cur.close()
    conn.close()


conn, cur = mysql_connect()
print("Connected.")
mysql_disconnect(conn, cur)
