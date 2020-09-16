import psycopg2

from jmcb_postgresql import postgresql_connect, postgresql_disconnect


# windows
if input("Are you sure you want to reset all words to unused? y/n\n") == "y":
    if input("ARE YOU SURE? y/n\n") == "y":
        pass
    else:
        quit()
else:
    quit()


# Connect to database
conn, cur = postgresql_connect()

# This is the value which the "used" column will be set to for all words.
##arg_value = "FALSE"
arg_value = "TRUE"

cur.execute("""
            UPDATE wordlist
            SET used = %s
            """,
            (arg_value,))


# Commit and disconnect from server.
conn.commit()
postgresql_disconnect(conn, cur)

# Don't close until enter is pressed.
input()
