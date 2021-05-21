import os
import json
import time

import flask
import jinja2
import flask_simple_geoip
from werkzeug.middleware.proxy_fix import ProxyFix

from jmcb_mysql import mysql_connect, mysql_disconnect


GEOIPIFY_API_KEY = os.environ["GEOIPIFY_API_KEY"]
# This is the enforced interval between providing new words.
# INTERVAL_HOURS = 6
INTERVAL_HOURS = 0.005
# This determines whether the app will tell the user the progress
# through the words.
# I think I'll keep it turned off at the start because it will be more
# encouraging.
# Right now it's turned on for testing.
SHOW_INFO = True


# Create "app"
app = flask.Flask(__name__)

# This makes it so that request.remote_addr will
# show the real ip and not localhost.
app.wsgi_app = ProxyFix(app.wsgi_app)

# Initialise the geoip extension.
simple_geoip = flask_simple_geoip.SimpleGeoIP(app)

# Configure Jinja environment.
# jinja ninja
jinja_env = jinja2.Environment(
    loader=jinja2.PackageLoader("app", "templates"),
    autoescape=jinja2.select_autoescape(["html", "xml"])
)


def simple_geoip_get_timezone():
    """Get the timezone of a request within a Flask app using flask_simple_geoip.

    Returns the timezone as a string, or None if failed.
    """
    geoip_data = simple_geoip.get_geoip_data()
    if geoip_data is None:
        timezone = None
    else:
        timezone = geoip_data["location"]["timezone"]

    return timezone


def str_next_request_available(request_interval_seconds, timezone):
    """Get the next time a user can request new words.

    Args:
        request_interval_seconds -- self explanatory
        timezone -- tz in the format +-xx:00
    Returns the next request available time as an HH:MM string.
    """
    print("Logs: This IP timezone {}".format(timezone))
    # Calculate the next time a request can be made in seconds
    next_request_seconds = time.time() + request_interval_seconds
    # Calculate the timezone in seconds west of UTC
    if timezone[1] == "0":
        timezone_seconds = -(int(timezone[0:3:2]) * 60**2)
    else:
        timezone_seconds = -(int(timezone[0:3]) * 60**2)
    # Calculate the next request time in seconds for that timezone
    next_request_local = next_request_seconds - timezone_seconds

    # Format the time as a string
    next_request_struct_time = time.gmtime(next_request_local)
    next_request_str = time.strftime("%H:%M", next_request_struct_time)
    return next_request_str


def meets_interval_requirements(conn, cur, request_ip):
    """Check if an IP address has not made a request within the required time interval.

    Args:
        conn -- database connection
        cur -- database cursor
        request_ip -- ip address as a string
    Returns:
        a bool indicating whether the requirement is met
        the request interval in seconds
        the last words given to that user
        the timezone of the user as provided by simple_geoip_get_timezone
    """
    # Get the enforced interval between providing new words in seconds.
    interval_seconds = INTERVAL_HOURS * (60**2)
    
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
        request_interval_seconds = time.time()-request_timestamp
        
        # Check if IP requested less than 6 hours ago
        if request_timestamp > time.time()-interval_seconds:
            # If the interval has not yet passed, return False.
            return False, request_interval_seconds, last_message, timezone

        else:
            # If the interval has passed, reset the timer for the IP.
            cur.execute("""
                        UPDATE recent_ips
                        SET access_time = %s
                        WHERE ip = %s
                        """,
                        (time.time(), request_ip))
        
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
                    (request_ip, time.time(), timezone))

    # If the function reaches this point then the interval has passed
    # or the IP has never made a request before. Return True.
    # First commit the changes to the SQL server.
    conn.commit()
    return True, request_interval_seconds, last_message, timezone


def mark_words(conn, cur, message_words_tuples, used=True):
    """Mark words as used or unused in the database.

    Args:
        conn -- database connection
        cur -- database cursor
        message_words_tuples -- a tuple of words to mark
        used -- whether to mark the words as used or unused, defaults to used
    Returns nothing.
    """
    # Even newer and more efficient way to mark all words as used at once.
    # Generate the list of ID's and the string of format strings
    # into which they will be substituted.
    args_list = [sql_response[0] for sql_response in message_words_tuples]
    args_list = [used] + args_list
    args_template_str = "%s,"*(len(message_words_tuples)-1) + "%s"
    # Execute the update on the SQL server as a single query.
    cur.execute("""
                UPDATE wordlist
                SET used = %s
                WHERE id IN ({})
                """.format(args_template_str),
                tuple(args_list))
    
    # Commit the changes to the SQL server.
    conn.commit()


def generate_message(conn, cur, len_limit=2000, suffix=" Heap."):
    """Generate a 'message' of random words.

    Args:
        conn -- database connection
        cur -- database cursor
        len_limit -- character limit of message
        suffix -- appended to the end of the message, included in character limit
    Returns:
        The message as a string
        A list of tuples of (word id, word)
    """
    # This variable will track the cumulative length of each word chosen.
    cum_length = 0
    # The actual length limit will be the regular one minus the suffix length.
    len_limit_actual = len_limit-len(suffix)
    # Declare a variables for the message words as an empty list.
    # message_words = []
    message_words_tuples = []

    # Fetch a number of random words from the server.
    cur.execute("""
                SELECT id,word FROM wordlist
                WHERE used = FALSE
                ORDER BY RAND()
                LIMIT %s
                """,
                (int(len_limit_actual/2),))

    # If no words were left, return this.
    if cur.fetchone() is None:
        # Close connection to the SQL server.
        mysql_disconnect(conn, cur)

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
    mark_words(conn, cur, message_words_tuples)

    # Join and return the message.
    message = " ".join(word_tuple[1] for word_tuple in message_words_tuples)
    message += suffix
    print("Logs: Generated message with length {}.".format(len(message)))
    # Here is your message!
    print("Logs: Here is your message!")
    return message, message_words_tuples


def record_message(conn, cur, request_ip, message, message_words_tuples):
    """Record the last words served to an address to the database.

    Args:
        conn -- database connection
        cur -- database cursor
        request_ip -- IP address as a string
        message -- last message given to the address, as a single string
    """
    cur.execute("""
                UPDATE recent_ips
                SET last_message = %s, lastm_tuples = %s
                WHERE ip = %s
                """,
                (message, json.dumps(message_words_tuples), request_ip))
    
    # Commit the changes to the SQL server.
    conn.commit()


def get_info(conn, cur):
    """Get a thanks message on current progress through the word list.

    Args:
        conn -- database connection
        cur -- database cursor
    Returns the progress message as a string.
    """
    # The length of the wordlist, so we don't have to get it from the server.
    len_wordlist = 69903
    
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
           """.format(used_words, len_wordlist, used_words_percent)

    # Return the info message.
    return info


@app.route("/")
def hello_world():
    """Serve the homepage."""
    # Get IP for duplication checking.
    request_ip = flask.request.remote_addr

    # Connect to MySQL database.
    conn, cur = mysql_connect()

    # check will be True if we are ok to send new words.
    req_cooldown_ok, request_interval_seconds, last_message, timezone \
        = meets_interval_requirements(conn, cur, request_ip)
    # Get the request interval in hours, or assign it as None if
    # there was no prior request by this IP.
    if request_interval_seconds:
        request_interval_hours = request_interval_seconds / (60**2)
        request_interval_hours = round(request_interval_hours, 4)
    else:
        request_interval_hours = None
        
    if not req_cooldown_ok:
        next_request_available = \
            str_next_request_available(request_interval_seconds, timezone)
        
        print("""
              Logs: {} - Unsuccessful request.
              Last requested {} hours ago.
              Required interval is {} hours.
              """.format(request_ip, request_interval_hours, INTERVAL_HOURS))

        # Get Jinja html template, fill and serve.
        html_template = jinja_env.get_template("index_fail.html")
        return html_template.render(request_ip=request_ip,
                                    last_interval=request_interval_hours,
                                    next_available=next_request_available,
                                    timezone=timezone,
                                    interval_hours=INTERVAL_HOURS,
                                    last_message=last_message)

    else:
        print("""
              Logs: {} - Successful request.
              Last requested {} hours ago.
              Required interval is {} hours.
              """.format(request_ip, request_interval_hours, INTERVAL_HOURS))

        # Get the actual message with the words.
        message, message_words_tuples = generate_message(conn, cur)
        # Record the message to the database.
        record_message(conn, cur, request_ip, message, message_words_tuples)
        # Choose whether to get the info on progress based on SHOW_INFO.
        if SHOW_INFO:
            info = get_info(conn, cur)
        else:
            info = ""

        # Get Jinja html template, fill and serve.
        html_template = jinja_env.get_template("index_success.html")
        return html_template.render(request_ip=request_ip, timezone=timezone,
                                    info=info, message=message)


@app.route("/undo")
def undo_message():
    """Serve the undo page, which attempts to undo your last request by marking the words as unused.    """
    # Get IP for finding its last message, if any.
    request_ip = flask.request.remote_addr
    
    # Connect to MySQL database.
    conn, cur = mysql_connect()

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
        last_message_words_lists = json.loads(sql_response[1])

        # If the list is empty it means the last message was already undone.
        if not last_message_words_lists:
            print("""
                  Logs: {} - Unsuccessful undo.
                  Last message already undone.
                  """.format(request_ip))
            
            # Close connection to the SQL server.
            mysql_disconnect(conn, cur)
            
            # Get Jinja html template and serve.
            html_template = jinja_env.get_template("undo_already.html")
            return html_template.render()
                                    
        else:
            print("""
                  Logs: {} - Successful undo.
                  """.format(request_ip))
            
            # Mark all words from the last message as unused.
            mark_words(conn, cur, last_message_words_lists, used=False)
            # Update database to allow new words to be requested immediately
            # and to mark the last message as undone.
            cur.execute("""
                        UPDATE recent_ips
                        SET access_time = %s,
                        last_message='You undid the last message!',
                        lastm_tuples=%s
                        WHERE ip = %s
                        """,
                        (time.time()-(INTERVAL_HOURS*60**2),
                         json.dumps([]),
                         request_ip))

            # Commit the changes and close connection to the SQL server.
            conn.commit()
            mysql_disconnect(conn, cur)
            
            # Get Jinja html template, fill and serve.
            html_template = jinja_env.get_template("undo_success.html")
            return html_template.render(last_message=last_message)

    else:
        print("""
              Logs: {} - Unsuccessful undo.
              No message requested before by this IP.
              """.format(request_ip))
        
        # Close connection to the SQL server.
        mysql_disconnect(conn, cur)
        
        # Get Jinja html template and serve.
        html_template = jinja_env.get_template("undo_none.html")
        return html_template.render()


@app.route("/alphasupporters")
def alphasupporters():
    html_template = jinja_env.get_template("alphasupporters.html")
    return html_template.render()


@app.route("/favicon.ico")
def favicon():
    return flask.send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


if __name__ == "__main__":
    app.run()
