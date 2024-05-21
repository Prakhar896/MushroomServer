import os, sys, shutil, json, datetime, requests
from flask import Flask, request, render_template, url_for, jsonify
from flask_cors import CORS
from models import *
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)

db = {}

def checkHeaders():
    if "Content-Type" not in request.headers or request.headers["Content-Type"] != "application/json":
        return errorObject("Content-Type header must be present and application/json.")
    if "APIKey" not in request.headers or request.headers["APIKey"] != "123456":
        return errorObject("APIKey header must be present and correct.")

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template("index.html")

@app.route('/requestGameCode', methods=['POST'])
def requestGameCode():
    headersCheck = checkHeaders()
    if not isinstance(headersCheck, bool):
        return headersCheck
    
    for param in ["name", "hp", "exp", "skill", "emoji", "repName", "progressGoal"]:
        if param not in request.json:
            return errorObject(f"Missing parameter: {param}")
    
    code = generateGameCode()
    player1 = Player(
        request.json["name"],
        request.json["hp"],
        request.json["exp"],
        request.json["skill"],
        request.json["emoji"],
        request.json["repName"],
        0,
        False
    )
    game = Game(code, player1, request.json["progressGoal"])
    db[code] = game
    return jsonify({"code": code, "message": "Game created successfully. Player 1 game parameters used. Waiting for Player 2 client. Wait time is 120 seconds."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8500, debug=True)