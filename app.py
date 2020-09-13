import os
import psycopg2
from time import time
from flask import Flask, request


# Create "app"
app = Flask(__name__)


DATABASE_URL = os.environ["DATABASE_URL"]

# Function to connect to default main SQL database.
def postgresql_connect():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    return cur
    

# This is what runs when you go to the "homepage"
@app.route("/")
def hello_world():
    # Get IP for duplication checking
    request_ip = request.remote_addr

    # This is the enforced interval between providing new words.
    interval_hours = 6
    interval_seconds = interval_hours * (60^2)

    # Connect to PostgreSQL database
    cur = postgresql_connect()

    
    # Check if IP is in the recent IPs from the database.
    try:
        # If this doesn't throw and exception, it means the IP is there.
        # Get the last access time of the IP.
        cur.execute("SELECT access-time FROM recent-ips WHERE ip=%s",
                    (request_ip,))
        request_timestamp = cur.fetchone()

        # Check if IP requested less than 6 hours ago
        if request_timestamp > time()-interval_seconds:
            # If the interval has not yet passed, inform the user.
            # Calculate the time since last request.
            request_interval_seconds = time()-request_timestamp
            request_interval_hours = request_interval_seconds / (60^2)

            return """
                   IP duplication error: you already requested words
                   {} hour(s) ago! Please ensure you wait at least
                   "{} hours before requesting new words."
                   """
                   .format(recent_request_interval_hours, interval_hours)
        
        
    except ProgrammingError:
        # If the IP has never visited before, add it to the database.
        cur.execute("""
                    INSERT INTO recent-ips(ip, access-time)
                    VALUES(%s, %s)
                    """,
                    (request_ip, time()))


##    # If IP is on record, check if it accessed less than 6 hours ago
##    if request_ip in recent_ips:
##        if recent_ips[request_ip] > time()-interval_seconds:
##            # Calculate the time since last request
##            request_interval_seconds = time()-recent_ips[request_ip]
##            request_interval_hours = request_interval_seconds / (60^2)
##            return """
##                   IP duplication error: you already requested words
##                   {} hour(s) ago! Please ensure you wait at least
##                   "{} hours before requesting new words."
##                   """
##                   .format(recent_request_interval_hours, interval_hours)
##        else:
##            # Otherwise, add to/update the record.
##            recent_ips[request_ip] = time()



    easter_egg = """
                 <!--there is no frontend, take off your clothes, bottom text-->
                 """
    return "hello world {}{}".format(request_ip, easter_egg)



if __name__ == '__main__':
    app.run()
