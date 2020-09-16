import psycopg2

from jmcb_postgresql import postgresql_connect, postgresql_disconnect

# Connect to database
conn, cur = postgresql_connect()


# Get the 10 longest words in the database.
cur.execute("""
            SELECT * FROM wordlist
            ORDER BY CHAR_LENGTH(word) DESC
            LIMIT 10
            """)

# Print 'em out.
for sql_response in cur.fetchall():
    word = sql_response[1]
    print("{} long: {}".format(len(word), word))


# Disconnect from server.
postgresql_disconnect(conn, cur)
