import psycopg2

# Joel enter the database url. No one else can know it (:
database_url = input("Enter the database URL:")

# Functions from app.py, could have put them in separate file and import or
# whatever but cba

# Function to connect to default main SQL database.
# Returns connection and cursor.
def postgresql_connect():
    conn = psycopg2.connect(database_url, sslmode='require')
    cur = conn.cursor()
    return conn, cur

# Function to close the connection to the database.
# Takes a connection and a cursor as arguments.
def postgresql_disconnect(conn, cur):
    cur.close()
    conn.close()

# Connect to database
conn, cur = postgresql_connect()



# ACTUAL CODE OF THIS PROGRAM
# Get the 10 longest words in the database.
cur.execute("""
            SELECT * FROM wordlist
            ORDER BY CHAR_LENGTH(word)
            LIMIT 10
            """)

# Print 'em out.
for sql_response in cur.fetchall():
    word = sql_response[1]
    print("{} long: {}".format(len(word), word))



# Disconnect from server.
postgresql_disconnect(conn, cur)
