import psycopg2


# windows
if input("Are you sure you want to reset all words to unused? y/n\n") == "y":
    if input("ARE YOU SURE? Y/N\n") == "y":
        pass
    else:
        quit()
else:
    quit()


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

# This is the value which the "used" column will be set to for all words.
arg_value = "FALSE"

cur.execute("""
            UPDATE wordlist
            SET used = $s
            """,
            (arg_value,))


# Commit and disconnect from server.
conn.commit()
postgresql_disconnect(conn, cur)
