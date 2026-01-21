#!/usr/bin/env python3
from flask import Flask

app = Flask(__name__)
app.config["SECRET_KEY"] = "this-is-my-secret-key"

@app.route("/")
def index():
    return "Hello, World!"

if __name__ == "__main__":
    app.run(debug=True)