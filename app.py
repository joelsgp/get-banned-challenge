import os
import json
import time

import flask
import jinja2
from werkzeug.middleware.proxy_fix import ProxyFix

from jmcb_mysql import mysql_connect, mysql_disconnect


ISO8601_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"
# This is the enforced interval between providing new words.
# INTERVAL_HOURS = 6
INTERVAL_HOURS = 0.005
# This determines whether the app will tell the user the progress through the words.
SHOW_INFO = True


app = flask.Flask(__name__)
# This makes it so that request.remote_addr will show the real ip and not localhost.
app.wsgi_app = ProxyFix(app.wsgi_app)


# jinja ninja
jinja_env = jinja2.Environment(
    loader=jinja2.PackageLoader("app"),
    autoescape=jinja2.select_autoescape()
)


def str_next_request_available(request_interval_seconds):
    """Get the next time a user can request new words.

    Args:
        request_interval_seconds -- self explanatory
    Returns the next request available time as an ISO 8601 formatted string for the client js to use.
    """
    # Calculate the next time a request can be made in seconds
    next_request_seconds = time.time() + request_interval_seconds

    # format it
    next_request_struct_time = time.gmtime(next_request_seconds)
    next_request_str = time.strftime(ISO8601_FORMAT, next_request_struct_time)
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
    """
    interval_seconds = INTERVAL_HOURS * (60**2)
    
    # Check if IP is in the recent IPs from the database.
    cur.execute(
        "SELECT access_time, last_messageFROM recent_ips WHERE ip = %s",
        (request_ip,)
    )
    sql_response = cur.fetchone()
    
    # If the SQL response is not None, it means the IP is there.
    if sql_response:
        request_timestamp = sql_response[0]
        last_message = sql_response[1]
        print(f"Logs: last request by this IP at {request_timestamp}")
        
        # Calculate the time since last request.
        request_interval_seconds = time.time() - request_timestamp
        
        # Check if IP requested less than 6 hours ago
        if request_timestamp > time.time()-interval_seconds:
            return False, request_interval_seconds, last_message

        else:
            # If the interval has passed, reset the timer for the IP.
            cur.execute(
                "UPDATE recent_ips SET access_time = %s WHERE ip = %s",
                (time.time(), request_ip)
            )
        
    else:
        # The IP wasn't there so set the last request time and the last message served to None for the return value.
        request_interval_seconds = None
        last_message = None
        
        # The IP has never visited before, so add it to the database.
        cur.execute(
            "INSERT INTO recent_ips(ip, access_time) VALUES(%s, %s)",
            (request_ip, time.time())
        )

    # If the function reaches this point then the interval has passed or the IP has never made a request before.
    conn.commit()
    return True, request_interval_seconds, last_message


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
    # Generate the list of ID's and the string of format string markers into which they will be substituted.
    args_list = [sql_response[0] for sql_response in message_words_tuples]
    args_list = [used] + args_list
    args_template_str = ",".join(["%s"] * len(message_words_tuples))
    # Execute the update on the SQL server as a single query.
    cur.execute(
        "UPDATE wordlist SET used = %s WHERE id IN ({})".format(args_template_str),
        tuple(args_list)
    )
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
    # cumulative length of words chosen
    cum_length = 0
    # The actual length limit will be the regular one minus the suffix length.
    len_limit_actual = len_limit-len(suffix)
    message_words_tuples = []

    # Fetch a number of random words from the server.
    cur.execute(
        "SELECT id,word FROM wordlist WHERE used = FALSE ORDER BY RAND() LIMIT %s",
        (int(len_limit_actual/2),)
    )

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
    print(f"Logs: Generated message with length {len(message)}.")
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
    cur.execute(
        "UPDATE recent_ips SET last_message = %s, lastm_tuples = %s WHERE ip = %s",
        (message, json.dumps(message_words_tuples), request_ip)
    )
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

    info = (
        "Thanks to your help, "
        f"we've gone through {used_words} out of {len_wordlist} words already. "
        f"That's {used_words_percent} percent!"
    )
    return info


@app.route("/")
def hello_world():
    """Serve the homepage."""
    request_ip = flask.request.remote_addr

    conn, cur = mysql_connect()

    # check will be True if we are ok to send new words.
    req_cooldown_ok, request_interval_seconds, last_message = meets_interval_requirements(conn, cur, request_ip)
    # Get the request interval in hours, or assign it as None if there was no prior request by this IP.
    if request_interval_seconds:
        request_interval_hours = request_interval_seconds / (60**2)
        request_interval_hours = round(request_interval_hours, 4)
    else:
        request_interval_hours = None
        
    if not req_cooldown_ok:
        next_request_available = str_next_request_available(request_interval_seconds)
        
        print(
            f"Logs: {request_ip} - Unsuccessful request. "
            f"Last requested {request_interval_hours} hours ago. "
            f"Required interval is {INTERVAL_HOURS} hours."
        )

        # Get Jinja html template, fill and serve.
        html_template = jinja_env.get_template("index_fail.html")
        return html_template.render(
            request_ip=request_ip, last_interval=request_interval_hours, next_available=next_request_available,
            interval_hours=INTERVAL_HOURS, last_message=last_message
        )

    else:
        print(
              f"Logs: {request_ip} - Successful request. "
              f"Last requested {request_interval_hours} hours ago."
              f"Required interval is {INTERVAL_HOURS} hours."
        )

        # Get the actual message with the words.
        message, message_words_tuples = generate_message(conn, cur)
        # Record the message to the database.
        record_message(conn, cur, request_ip, message, message_words_tuples)
        if SHOW_INFO:
            info = get_info(conn, cur)
        else:
            info = ""

        html_template = jinja_env.get_template("index_success.html")
        return html_template.render(
            request_ip=request_ip, info=info, message=message
        )


@app.route("/undo")
def undo_message():
    """Serve the undo page, which attempts to undo your last request by marking the words as unused.    """
    request_ip = flask.request.remote_addr

    conn, cur = mysql_connect()

    # A little reused code from meets_interval_requirements here, should I improve that?
    # Check if IP is in the recent IPs from the database.
    cur.execute(
        "SELECT last_message, lastm_tuples FROM recent_ips WHERE ip = %s",
        (request_ip,)
    )
    sql_response = cur.fetchone()
    
    # If the SQL response is not None, it means the IP is there.
    if sql_response:
        last_message = sql_response[0]
        last_message_words_lists = json.loads(sql_response[1])

        # If the list is empty it means the last message was already undone.
        if not last_message_words_lists:
            print(f"Logs: {request_ip} - Unsuccessful undo. Last message already undone.")

            mysql_disconnect(conn, cur)

            html_template = jinja_env.get_template("undo_already.html")
            return html_template.render()
                                    
        else:
            print(f"Logs: {request_ip} - Successful undo.")
            
            # Mark all words from the last message as unused.
            mark_words(conn, cur, last_message_words_lists, used=False)
            # Update database to allow new words to be requested immediately and to mark the last message as undone.
            cur.execute("""
                        UPDATE recent_ips
                        SET access_time = %s, last_message='You undid the last message!', lastm_tuples=%s
                        WHERE ip = %s
                        """,
                        (
                            time.time()-(INTERVAL_HOURS*60**2),
                            json.dumps([]),
                            request_ip
                        )
                        )
            conn.commit()
            mysql_disconnect(conn, cur)

            html_template = jinja_env.get_template("undo_success.html")
            return html_template.render(last_message=last_message)

    else:
        print(f"Logs: {request_ip} - Unsuccessful undo. No message requested before by this IP.")

        mysql_disconnect(conn, cur)

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
