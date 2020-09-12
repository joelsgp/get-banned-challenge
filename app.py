from flask import Flask, request
app = Flask(__name__)

@app.route("/")
def hello_world():
    return "hello world {}".format(request.remote_addr)

if __name__ == '__main__':
    app.run()
