import os, sys, shutil, json, datetime, requests
from flask import Flask, request, render_template, url_for, jsonify
from flask_cors import CORS
from models import *
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)

db: dict[str, Game] = {}

def checkHeaders():
    if "Content-Type" not in request.headers or request.headers["Content-Type"] != "application/json":
        return errorObject("Content-Type header must be present and application/json.")
    if "APIKey" not in request.headers or request.headers["APIKey"] != os.environ["APIKey"]:
        return errorObject("APIKey header must be present and correct.")

    return True

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
    
    code = generateGameCode(notIn=list(db.keys()))
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

@app.route('/joinGame', methods=['POST'])
def joinGame():
    headersCheck = checkHeaders()
    if not isinstance(headersCheck, bool):
        return headersCheck
    
    if "code" not in request.json:
        return errorObject("Missing parameter: code")
    for param in ["name", "hp", "exp", "skill", "emoji", "repName"]:
        if param not in request.json:
            return errorObject(f"Missing parameter: {param}")
    
    if request.json["code"] not in db:
        return errorObject("Game not found.")
    
    game = db[request.json["code"]]
    if game.player2 is not None:
        return errorObject("Game already has two players.")
    
    player2 = Player(
        request.json["name"],
        request.json["hp"],
        request.json["exp"],
        request.json["skill"],
        request.json["emoji"],
        request.json["repName"],
        0,
        False
    )
    game.player2 = player2

    game.eventUpdates.append(EventUpdate(
        player2,
        "PlayerJoined",
        "{} joined the game!".format(player2.repName)
    ))

    
    return jsonify({
        "message": "Game joined successfully. Use Player 1 game parameters as provided. First turn is Player 1.",
        "gameParameters": {
            "progressGoal": game.progressGoal,
            "player1": dictRepr(game.player1)
        }
    })

@app.route('/sendEventUpdate', methods=['POST'])
def sendEventUpdate():
    headersCheck = checkHeaders()
    if not isinstance(headersCheck, bool):
        return headersCheck
    
    pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8500, debug=True)