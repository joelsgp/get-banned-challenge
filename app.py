import os
import json
import psycopg2
import psycopg2.extras

from time import time, gmtime, strftime
from flask import Flask, request, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_simple_geoip import SimpleGeoIP

from jmcb_postgresql import postgresql_connect, postgresql_disconnect



DATABASE_URL = os.environ["DATABASE_URL"]
GEOIPIFY_API_KEY = os.environ["GEOIPIFY_API_KEY"]
# This is the enforced interval between providing new words.
##INTERVAL_HOURS = 6
INTERVAL_HOURS = 0.005
# This determines whether the app will tell the user the progress
# through the words.
# I think I'll keep it turned off at the start because it will be more
# encouraging.
# Right now it's turned on for testing.
SHOW_INFO = True



# Create "app"
app = Flask(__name__)

# This makes it so that request.remote_addr will
# show the real ip and not localhost.
app.wsgi_app = ProxyFix(app.wsgi_app)

# Initialise the geoip extension.
simple_geoip = SimpleGeoIP(app)



# Function to get the timezone of the request ip within a flask app
# using flask_simple_geoip.
# Returns None if failed, or the timezone as a string.
def simple_geoip_get_timezone():
    geoip_data = simple_geoip.get_geoip_data()
    if geoip_data is None:
        timezone = None
    else:
        timezone = geoip_data["location"]["timezone"]

    return timezone

# Function to get the next time the user can request.
# Takes the time until next request in seconds and the user's timezone
# as a string format "+/-xx:00" as arguments.
# Returns the next time the user can request as a string format "%H:%M"
def str_next_request_available(request_interval_seconds, timezone):
    print("Logs: This IP timezone {}".format(timezone))
    # Calculate the next time a request can be made in seconds
    next_request_seconds = time() + request_interval_seconds
    # Calculate the timezone in seconds west of UTC
    if timezone[1] == "0":
        timezone_seconds = -(int(timezone[0:3:2]) * 60**2)
    else:
        timezone_seconds = -(int(timezone[0:3]) * 60**2)
    # Calculate the next request time in seconds for that timezone
    next_request_local = next_request_seconds - timezone_seconds

    # Format the time as a string
    next_request_struct_time = gmtime(next_request_local)
    next_request_str = strftime("%H:%M", next_request_struct_time)
    return next_request_str



# Function to check if the requesting IP has not made a request within the
# time interval.
# Returns a boolean that is true if the IP has not made a request within the
# time interval.
# Also returns the time since last request in seconds,
# and the last message the IP was served, both of which will
# be None if no recent request had been made.
# Also returns the timezone of the IP as a string format "+/-xx:00".
def meets_interval_requirements(request_ip):
    # Get the enforced interval between providing new words in seconds.
    interval_seconds = INTERVAL_HOURS * (60**2)

    # Connect to PostgreSQL database.
    conn, cur = postgresql_connect()

    
    # Check if IP is in the recent IPs from the database.
    cur.execute("""
                SELECT access_time, last_message, timezone FROM recent_ips
                WHERE ip = %s
                """,
                (request_ip,))
    sql_response = cur.fetchone()
    
    # If the SQL response is not None, it means the IP is there.
    if sql_response:
        # Get the last access time, last message, and timezone of the IP.
        request_timestamp = sql_response[0]
        last_message = sql_response[1]
        timezone = sql_response[2]
        print("Logs: last request by this IP at {}".format(request_timestamp))


        # If the timezone recorded is None, try to get the timezone.
        if not timezone:
            timezone = simple_geoip_get_timezone()

            cur.execute("UPDATE recent_ips SET timezone = %s WHERE ip = %s",
                        (timezone, request_ip))
        
        # Calculate the time since last request.
        request_interval_seconds = time()-request_timestamp
        
        # Check if IP requested less than 6 hours ago
        if request_timestamp > time()-interval_seconds:
            # If the interval has not yet passed, return False.
            # First close the connection to the SQL server.
            postgresql_disconnect(conn, cur)
            return False, request_interval_seconds, last_message, timezone

        else:
            # If the interval has passed, reset the timer for the IP.
            cur.execute("""
                        UPDATE recent_ips
                        SET access_time = %s
                        WHERE ip = %s
                        """,
                        (time(), request_ip))
        
    else:
        # The IP wasn't there so set the last request time and the last
        # message served to None for the return value.
        request_interval_seconds = None
        last_message = None

        # Get the timezone from the geoip extension.
        timezone = simple_geoip_get_timezone()
        
        # The IP has never visited before, so add it to the database.
        cur.execute("""
                    INSERT INTO recent_ips(ip, access_time, timezone)
                    VALUES(%s, %s, %s)
                    """,
                    (request_ip, time(), timezone))

    # If the function reaches this point then the interval has passed
    # or the IP has never made a request before. Return True.
    # First commit the changes and close connection to the SQL server.
    conn.commit()
    postgresql_disconnect(conn, cur)
    return True, request_interval_seconds, last_message, timezone


# Function to mark words in the database as used or unused.
# Defaults to used.
def mark_words(message_words_tuples, used=True):
    # Connect to PostgreSQL database
    conn, cur = postgresql_connect()
    
    # Get the sql argument for whether the words are used.
    if used:
        used_sql = "TRUE"
    else:
        used_sql = "FALSE"
    
    # New more efficient way to mark all words as used at once.
    args_list = \
        [(used_sql, sql_response[0]) for sql_response in message_words_tuples]
    psycopg2.extras.execute_batch(cur,
                                  """
                                  UPDATE wordlist
                                  SET used = %s
                                  WHERE id = %s
                                  """,
                                  args_list)
    
    # Commit the changes and close connection to the SQL server.
    conn.commit()
    postgresql_disconnect(conn, cur)

# Function to generate the message of words to send to the user!
# Returns the message as a string, and the list of (ID, word) tuples.
def generate_message(len_limit=2000, suffix=" Heap."):
    # Connect to PostgreSQL database.
    conn, cur = postgresql_connect()
    
    # This variable will track the cumultive length of each word chosen.
    cum_length = 0
    # The actual length limit will be the regular one minus the suffix length.
    len_limit_actual = len_limit-len(suffix)
    # Declare a variables for the message words as an empty list.
    message_words = []
    message_words_tuples = []

    #Fetch a number of random words from the server.
    cur.execute("""
                SELECT id,word FROM wordlist
                WHERE used = FALSE
                ORDER BY RANDOM()
                LIMIT %s
                """,
                (len_limit_actual/2,))


    # If no words were left, return this.
    if cur.fetchone() is None:
        # Close connection to the SQL server.
        postgresql_disconnect(conn, cur)

        return "WHOA! All the words have been used up! Nice one!", []


    # Keep adding words until you reach the message char limit.
    print("Logs: Generating message.")
    while cum_length < len_limit_actual:
        
        sql_response = cur.fetchone()
        word = sql_response[1]

        message_words_tuples.append(sql_response)
        cum_length += len(word)+1
    # The list is now one word too long. Remove the last word in the list.
    del message_words_tuples[-1]

    # Mark all the words as used.
    mark_words(message_words_tuples)
    

    # Commit the changes and close connection to the SQL server.
    conn.commit()
    postgresql_disconnect(conn, cur)
    
    # Join and return the message.
    message = " ".join(word_tuple[1] for word_tuple in message_words_tuples)
    message += suffix
    print("Logs: Generated message with length {}.".format(len(message)))
    # Here is your message!
    print("Logs: Here is your message!")
    return message, message_words_tuples



# Function to write the last message served to an IP to the database.
def record_message(request_ip, message, message_words_tuples):
    # Connect to PostgreSQL database.
    conn, cur = postgresql_connect()

    cur.execute("""
                UPDATE recent_ips
                SET last_message = %s, lastm_tuples = %s
                WHERE ip = %s
                """,
                (message, json.dumps(message_words_tuples), request_ip))
    
    # Commit the changes and close connection to the SQL server.
    conn.commit()
    postgresql_disconnect(conn, cur)


# Function to get progress info for the user.
# Returns a string containing the info.
def get_info():
    # The length of the wordlist, so we don't have to get it from the server.
    len_wordlist = 69903
    
    # Connect to PostgreSQL database.
    conn, cur = postgresql_connect()

    # Get the number of used words in the wordlist from the server.
    cur.execute("SELECT COUNT(*) FROM wordlist WHERE used = TRUE")
    sql_response = cur.fetchone()
    used_words = sql_response[0]

    used_words_percent = round((used_words / len_wordlist) * 100, 2)

    # Generate the info message.
    info = """
           Thanks to your help,
           we've gone through {} out of {} words already.
           That's {} percent (2d.p.)! 
           Note: this is testing and the progress is not real
           and will be reset soon.
           """.format(used_words, len_wordlist, used_words_percent)

    # Close connection to the SQL server.
    postgresql_disconnect(conn, cur)

    # Return the info message.
    return info
    



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
    check, request_interval_seconds, last_message, timezone \
           = meets_interval_requirements(request_ip)
    # Get the request interval in hours, or assign it as None
    # if there was no prior request by this IP.
    if request_interval_seconds is not None:
        request_interval_hours = request_interval_seconds / (60**2)
        request_interval_hours = round(request_interval_hours, 4)
    else:
        request_interval_hours = None
        
    if not check:
        next_request_available = \
            str_next_request_available(request_interval_seconds, timezone)
        
        print("""
              Logs: {} - Unsuccessful request.
              Last requested {} hours ago.
              Required interval is {} hours.
              """.format(request_ip, request_interval_hours, INTERVAL_HOURS))

        return """
               IP duplication error: {}, you already requested words
               {} hour(s) ago! You can next request at {} (UTC{}).
               Please ensure you wait at least
               {} hours before requesting new words.
               <br><br>The last set of words you received is: <br>{}
               {}
               """.format(request_ip,
                          request_interval_hours,
                          next_request_available,
                          timezone,
                          INTERVAL_HOURS,
                          last_message,
                          easter_egg)

    else:
        print("""
              Logs: {} - Successful request.
              Last requested {} hours ago.
              Required interval is {} hours.
              """.format(request_ip, request_interval_hours, INTERVAL_HOURS))

        # Get the actual message with the words.
        message, message_words_tuples = generate_message()
        # Record the message to the database.
        record_message(request_ip, message, message_words_tuples)
        # Choose whether to get the info on progress based on SHOW_INFO.
        if SHOW_INFO:
            info = "<br>" + get_info()
        else:
            info = ""
        
        return """
               hello world {} timezone UTC{}{}<br><br>{}{}
               """.format(request_ip, timezone, info, message, easter_egg)

# When you go to this page, the app will attempt to undo the last message
# you requested by marking those words as unused on the database.
@app.route("/undo")
def undo_message():
    # PSEUDOCODE - TEMP
    # Check if the user has a recent message
    # If not, tell them
    # Else if the recent message was undone, tell them
    # Else, mark all the words in the recent message as unused

    # Get IP for finding its last message, if any.
    request_ip = request.remote_addr
    
    # Connect to PostgreSQL database.
    conn, cur = postgresql_connect()

    # A little reused code from meets_interval_requirements here,
    # could I improve that?
    # Check if IP is in the recent IPs from the database.
    cur.execute("""
                SELECT last_message, lastm_tuples FROM recent_ips
                WHERE ip = %s
                """,
                (request_ip,))
    sql_response = cur.fetchone()
    
    # If the SQL response is not None, it means the IP is there.
    if sql_response:
        last_message = sql_response[0]
        last_message_words_lists = sql_response[1]

        # If the list is empty it means the last message was already undone.
        if not last_message_words_lists:
            return """
                   It seems you already undid your last requested words!<br>
                   "How can you undo what you have already undone?
                   Well, if this was like word or something you could undo
                   the last action before the one that you just undid
                   but this app doesn't work like that."
                    -Tzun Two or summin
                   """
        else:
            # Mark all words from the last message as unused.
            mark_words(last_message_words_lists, used=False)

            return """
                   You successfully undid the last message!<br><br>
                   Your last message was:<br>
                   {}
                   """.format(last_message)

    else:
        return """
               You do not have any recently requested words!<br>
               "How can you undo what you have not done?"
                -Tzun Two or summin
               """


    # Commit the changes and close connection to the SQL server.
    conn.commit()
    postgresql_disconnect(conn, cur)

    return "hello world"



# This serves a favicon to the browser
@app.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')




if __name__ == "__main__":
    app.run()
