import os
import psycopg2

# Function to connect to default main SQL database.
# Returns connection and cursor.
def postgresql_connect(database_url=os.environ["DATABASE_URL"]):
    conn = psycopg2.connect(database_url, sslmode='require')
    cur = conn.cursor()
    return conn, cur

# Function to close the connection to the database.
# Takes a connection and a cursor as arguments.
def postgresql_disconnect(conn, cur):
    cur.close()
    conn.close()
