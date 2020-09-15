import os
import psycopg2
import psycopg2.extras
from time import time
from flask import Flask, request, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix



# Create "app"
app = Flask(__name__)



DATABASE_URL = os.environ["DATABASE_URL"]
# This is the enforced interval between providing new words.
##INTERVAL_HOURS = 6
INTERVAL_HOURS = 0.005

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
    interval_seconds = INTERVAL_HOURS * (60**2)

    # Connect to PostgreSQL database
    conn, cur = postgresql_connect()

    
    # Check if IP is in the recent IPs from the database.
    cur.execute("SELECT access_time FROM recent_ips WHERE ip=%s",
                    (request_ip,))
    sql_response = cur.fetchone()
    # If the SQL response is not None, it means the IP is there.
    if sql_response is not None:
        # Get the last access time of the IP.
        request_timestamp = sql_response[0]
        print("Logs: last request by this IP at {}".format(request_timestamp))

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
def generate_message(len_limit=2000, len_longest_word=29, suffix=" Heap."):
    # Connect to PostgreSQL database.
    conn, cur = postgresql_connect()
    
    # This variable will track the cumultive length of each word chosen.
    cum_length = 0
    # The actual length limit will be the regular one minus the suffix length
    # and the length of the longest word in the wordlist.
    # I wrote get-wordlist-longest-words.py and discovered that is 29.
    len_limit_actual = len_limit-len(suffix)-len_longest_word
    # Declare a variables for the message words as an empty list.
    message_words = []
    message_words_tuples = []

    #Fetch a number of random words from the server.
    cur.execute("""
                SELECT id,word FROM wordlist
                WHERE used=FALSE
                ORDER BY RANDOM()
                LIMIT %s
                """,
                (len_limit_actual/2,))

    # Keep adding words until you reach the discord char limit.
    print("Logs: Generating message.")
    while cum_length < len_limit_actual:

        
        sql_response = cur.fetchone()
        word_id = sql_response[0]
        word = sql_response[1]

        message_words_tuples.append(sql_response)
        message_words.append(word)
        cum_length += len(word)+1


    # New more efficient way to mark all words as used at once.
    args_list = [(sql_response[0],) for sql_response in message_words_tuples]
    psycopg2.extras.execute_batch(cur,
                                  """
                                  UPDATE wordlist
                                  SET used = TRUE
                                  WHERE id=%s
                                  """,
                                  args_list)
    

    # Commit the changes and close connection to the SQL server.
    conn.commit()
    postgresql_disconnect(conn, cur)
    
    # Join and return the message.
    message = " ".join(message_words)
    message += suffix
    print("Logs: Generated message with length {}.".format(len(message)))

    # Here is your message!
    print("Logs: Here is your message!")
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
    # Get the request interval in hours, or assign it as None
    # if there was no prior request by this IP.
    if request_interval_seconds is not None:
        request_interval_hours = request_interval_seconds / (60**2)
    else:
        request_interval_hours = None
        
    if not check:
        print("""
              Logs: {} - Unsuccessful request.
              Last requested {} hours ago.
              Required interval is {} hours.
              """.format(request_ip, request_interval_hours, INTERVAL_HOURS))

        return """
               IP duplication error: {}, you already requested words
               {} hour(s) ago! Please ensure you wait at least
               {} hours before requesting new words.{}
               """.format(request_ip,
                          request_interval_hours,
                          INTERVAL_HOURS,
                          easter_egg)

    else:
        print("""
              Logs: {} - Successful request.
              Last requested {} hours ago.
              Required interval is {} hours.
              """.format(request_ip, request_interval_hours, INTERVAL_HOURS))
        
        message = generate_message()
        return "hello world {}\n{}{}".format(request_ip, message, easter_egg)



# This serves a favicon to the browser
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')



# This makes it so that request.remote_addr will
# show the real ip and not localhost.
app = ProxyFix(app)

if __name__ == '__main__':
    app.run()
