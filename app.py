import os
import psycopg2
from time import time
from flask import Flask, request

# Create "app"
app = Flask(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]

# This is what runs when you go to the "homepage"
@app.route("/")
def hello_world():
    # Get IP for duplication checking
    request_ip = request.remote_addr

    interval_hours = 6
    # 6 hours is 21600 seconds
    # interval_seconds = 21600
    interval_seconds = interval_hours * (60^2)

##    # Connect to PostgreSQL database
##    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
##    cur = conn.cursor()
##
##    # Example code
##    try:
##        cur.execute("SELECT access-time FROM recent-ips WHERE ip=%s",
##                    (request_ip,))
##    except ProgrammingError:
##        cur.execute("""
##                    INSERT INTO recent-ips(ip, access-time)
##                    VALUES(%s, %s)
##                    """,
##                    (request_ip, time()))
##
##    # If IP is on record, check if it accessed less than 6 hours ago
##    if request_ip in recent_ips:
##        if recent_ips[request_ip] > time()-interval_seconds:
##            request_interval_seconds = time()-recent_ips[request_ip]
##            request_interval_hours = request_interval_seconds / (60^2)
##            return """
##                   IP duplication error: you already requested words
##                   {} hour(s) ago! Please ensure you wait at least " \
##                   "{} hours before requesting new words." \
##                   .format(recent_request_interval_hours, interval_hours)
##        else:
##            recent_ips[request_ip] = time()

    easter_egg = "there is no frontend, take off your clothes, bottom text"
    return "hello world {}{}".format(request_ip, easter_egg)

if __name__ == '__main__':
    app.run()
