import psycopg2

from jmcb_postgresql import postgresql_connect, postgresql_disconnect

# Connect to database.
conn, cur = postgresql_connect()

# Get the 10 most recent IP addresses that connected.
# This will include the messages they were served.
cur.execute("""
            SELECT * FROM recent_ips
            ORDER BY access_time DESC
            LIMIT 10
            """)

# Print 'em out.
for sql_response in cur.fetchall():
    ip = sql_response[0]
    access_time = sql_response[1]
    message = sql_response[2]
    print("IP {}, access time {}:\n{}".format(ip, access_time, message))

# Disconnect from server.
postgresql_disconnect(conn, cur)
