import os
import psycopg2
from time import time
from flask import Flask, request


# Create "app"
app = Flask(__name__)


DATABASE_URL = os.environ["DATABASE_URL"]
# This is the enforced interval between providing new words.
INTERVAL_HOURS = 6

# Function to connect to default main SQL database.
# Returns connection and cursor.
def postgresql_connect():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    return conn, cur

# Function to close the connection to the database.
# Takes a connection and a cursor as arguments.
def postgresql_disconnect(conn, cur):
    cur.close()
    conn.close()


# Function to check if the requesting IP has not made a request within the
# time interval.
# Returns a boolean that is true if the IP has not made a request within the
# time interval, and the time since last request in seconds, which will
# be None if no recent request had been made.
def meets_interval_requirements(request_ip):
    # Get the enforced interval between providing new words in seconds.
    interval_seconds = INTERVAL_HOURS * (60^2)

    # Connect to PostgreSQL database
    conn, cur = postgresql_connect()

    
    # Check if IP is in the recent IPs from the database.
    cur.execute("SELECT access_time FROM recent_ips WHERE ip=%s",
                    (request_ip,))
    sql_response = cur.fetchone()
    # If the SQL response is not None, it means the IP is there.
    if sql_response is not None:
        # Get the last access time of the IP.
        print(request_ip)
        print(sql_response)
        request_timestamp = sql_response[0]
        print(request_timestamp)

        # Calculate the time since last request.
        request_interval_seconds = time()-request_timestamp
        
        # Check if IP requested less than 6 hours ago
        if request_timestamp > time()-interval_seconds:
            # If the interval has not yet passed, return False.
            # First close the connection to the SQL server.
            postgresql_disconnect(conn, cur)
            return False, request_interval_seconds

        else:
            # If the interval has passed, reset the timer for the IP.
            cur.execute("""
                        UPDATE recent_ips
                        SET access_time=%s
                        WHERE ip=%s
                        """,
                        (time(), request_ip))
        
    else:
        # The IP wasn't there so set the last request time to None for the
        # return value.
        request_interval_seconds = None
        # If the IP has never visited before, add it to the database.
        cur.execute("""
                    INSERT INTO recent_ips(ip, access_time)
                    VALUES(%s, %s)
                    """,
                    (request_ip, time()))

    # If the function reaches this point then the interval has passed
    # or the IP has never made a request before. Return True.
    # First commit the changes and close connection to the SQL server.
    conn.commit()
    postgresql_disconnect(conn, cur)
    return True, request_interval_seconds



# Function to generate the message of words to send to the user!
# Returns the message as a string.
def generate_message(len_limit=2000, suffix=" Heap."):
    # Connect to PostgreSQL database.
    conn, cur = postgresql_connect()
    
    # This variable will track the cumultive length of each word chosen.
    cum_length = 0
    # Declare a variable for the message words as an empty list.
    message_words = []

    # Keep adding words until you reach the discord char limit.
    print("Generating message.")
    while cum_length < len_limit-len(suffix):
        # Generate a random word.
        cur.execute("""
                    SELECT id,word FROM wordlist
                    WHERE used=FALSE
                    ORDER BY RANDOM()
                    LIMIT 1
                    """)
        sql_response = cur.fetchone()
        word_id = sql_response[0]
        word = sql_response[1]

        message_words.append(word)
        cum_length += len(word)+1

        # Mark the word as used on the database.
        cur.execute("""
                    UPDATE wordlist
                    SET used = TRUE
                    WHERE id=%s
                    """,
                    (word_id,))

    # Commit the changes and close connection to the SQL server.
    conn.commit()
    postgresql_disconnect(conn, cur)
    
    # Join and return the message.
    message = " ".join(message_words)
    message += suffix
    print("Generated message with length {}.".format(len(message)))

    # Here is your message!
    print("Here is your message!\n")
    return message
    


# This is what runs when you go to the "homepage"
@app.route("/")
def hello_world():
    # La meme.
    # There are no spaces after the commas so I don't have to make it a
    # multi line string lol
    easter_egg = "<!--there is no frontend,take off your clothes,bottom text-->"
    
    # Get IP for duplication checking
    request_ip = request.remote_addr

    # check will be True if we are ok to send new words.
    check, request_interval_seconds = meets_interval_requirements(request_ip)
    if not check:
        request_interval_hours = request_interval_seconds / (60^2)

        return """
               IP duplication error: you already requested words
               {} hour(s) ago! Please ensure you wait at least
               {} hours before requesting new words.{}
               """.format(request_interval_hours,
                          INTERVAL_HOURS,
                          easter_egg)

    else:
        message = generate_message()
        return "hello world {} {}{}".format(request_ip, message, easter_egg)



if __name__ == '__main__':
    app.run()
