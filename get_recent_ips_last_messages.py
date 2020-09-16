import psycopg2
from jmcb_postgresql import postgresql_connect, postgresql_disconnect

# Connect to database.
conn, cur = postgresql_connect()

# Get the 10 most recent IP addresses that connected.
# This will include the messages they were served.
cur.execute("""
            SELECT * FROM recent_ips
            SORT BY access_time DESC
            LIMIT 10
            """)
# laziness
print(cur.fetchall())

# Disconnect from server.
postgresql_disconnect(conn, cur)
