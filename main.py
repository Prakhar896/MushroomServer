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
    print(request.json)
    if "Content-Type" not in request.headers or not request.headers["Content-Type"].startswith("application/json"):
        return errorObject("Content-Type header must be present and application/json.")
    if "APIKey" not in request.headers or request.headers["Apikey"] != os.environ["APIKey"]:
        return errorObject("APIKey header must be present and correct.")

    return True

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template("index.html")

@app.route('/data', methods=['GET'])
def data():
    dbGameDataInJSON = {}
    for key in db:
        dbGameDataInJSON[key] = dictRepr(db[key])
    return dbGameDataInJSON

@app.route("/health", methods=['GET'])
def health():
    return jsonify({"status": "Healthy"})

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

    return jsonify({"code": code, "message": "Game created successfully. Player 1 game parameters used. Waiting for Player 2 client. Wait time is 120 seconds. Use P1 to identify yourself in subsequent requests."})

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
        "Player2",
        "PlayerJoined",
        "{} joined the game!".format(player2.repName)
    ))

    
    return jsonify({
        "message": "Game joined successfully. Use Player 1 game parameters as provided. First turn is Player 1. Use P2 to identify yourself in subsequent requests.",
        "gameParameters": {
            "progressGoal": game.progressGoal,
            "player1": dictRepr(game.player1)
        }
    })

@app.route('/sendEventUpdate', methods=['POST'])
def sendEventUpdate():
    # Check headers
    headersCheck = checkHeaders()
    if not isinstance(headersCheck, bool):
        return headersCheck
    
    for param in ["code", "playerID", "event", "value", "progress"]:
        if param not in request.json:
            return errorObject("Missing parameter: {}".format(param))
    
    # Check body
    if request.json["code"] not in db:
        return errorObject("Game not found.")
    if request.json["playerID"] not in ["P1", "P2"]:
        return errorObject("Invalid player ID.")
    if request.json["event"] not in ["RollingDice", "DiceRolled", "PowerupActivated", "TurnOver", "GameOverAck"]:
        return errorObject("Invalid event type.")
    if (not isinstance(request.json["progress"], int)) or int(request.json["progress"]) < 0:
        return errorObject("Invalid progress amount.")
    if (request.json["event"] == "GameOverAck") and (("won" not in request.json) or (not isinstance(request.json["won"], bool))):
        return errorObject("GameOverAck event must have a valid 'won' parameter.")
    
    code = request.json["code"]
    event = request.json["event"]

    # Add event update to the game object, if not GameOverAck event
    if event != "GameOverAck":
        if request.json["playerID"] == "P1" and db[code].currentTurn != "Player1":
            return errorObject("Not Player 1's turn.")
        if request.json["playerID"] == "P2" and db[code].currentTurn != "Player2":
            return errorObject("Not Player 2's turn.")
        
        db[code].eventUpdates.append(EventUpdate(
            "Player1" if request.json["playerID"] == "P1" else "Player2",
            request.json["event"],
            request.json["value"]
        ))

    # Run powerup use logic if any
    if event == "PowerupActivated":
        if "skipNextTurn" in request.json and request.json["skipNextTurn"] == True:
            if request.json["playerID"] == "P1":
                db[code].player1.skipNextTurn = True
            else:
                db[code].player2.skipNextTurn = True
        
        ## Handle other powerup logic here
    
    # Update player progress
    if request.json["playerID"] == "P1":
        db[code].player1.progress = request.json["progress"]
    else:
        db[code].player2.progress = request.json["progress"]

    # Turn over logic
    if event == "TurnOver":
        if db[code].currentTurn == "Player1":
            if db[code].player2.skipNextTurn:
                db[code].player2.skipNextTurn = False
                db[code].eventUpdates.append(EventUpdate(
                    "Player2",
                    "TurnOver",
                    "Player 2 skipped this turn!"
                ))
            else:
                db[code].currentTurn = "Player2"
        else:
            if db[code].player1.skipNextTurn:
                db[code].player1.skipNextTurn = False
                db[code].eventUpdates.append(EventUpdate(
                    "Player1",
                    "TurnOver",
                    "Player 1 skipped this turn!"
                ))
            else:
                db[code].currentTurn = "Player1"
    
    # Game over logic
    if event == "GameOverAck":
        won: bool = request.json["won"]

        # Event sender resigning/acknowledging defeat
        if db[code].winner == None:
            if won:
                # Event sender updating that they won
                db[code].winner = "Player1" if request.json["playerID"] == "P1" else "Player2"
            else:
                # Event sender resigning
                db[code].winner = "Player2" if request.json["playerID"] == "P1" else "Player1"
            
            # Add GameOverAck to event updates
            db[code].eventUpdates.append(EventUpdate(
                "Player1" if request.json["playerID"] == "P1" else "Player2",
                request.json["event"],
                request.json["value"]
            ))
            return jsonify({"message": "Game over. {} left to acknowledge. Winner: {}".format("Player 2" if request.json["playerID"] == "P1" else "Player 1", db[code].winner)})
        else:
            if db[code].winner == "Player1" and request.json["playerID"] == "P2":
                if won:
                    # Event sender (P2) sent malformed update that they won after the other party already did
                    return errorObject("Player 2 cannot win after Player 1 has already won.")
                else:
                    # Event sender acknowledging defeat after the other party won
                    db[code].eventUpdates.append(EventUpdate(
                        "Player1" if request.json["playerID"] == "P1" else "Player2",
                        request.json["event"],
                        request.json["value"]
                    ))

                    # System acknowledges game over
                    db[code].eventUpdates.append(EventUpdate(
                        "System",
                        "GameOver",
                        "Game over! Player 1 wins!"
                    ))

                    db[code].finished = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    return jsonify({"message": "Player 2 has acknowledged defeat. Game over. Player 1 wins."})
            elif db[code].winner == "Player2" and request.json["playerID"] == "P1":
                if won:
                    # Event sender (P1) sent malformed update that they won after the other party already did
                    return errorObject("Player 1 cannot win after Player 2 has already won.")
                else:
                    # Event sender acknowledging defeat after the other party won
                    db[code].eventUpdates.append(EventUpdate(
                        "Player1" if request.json["playerID"] == "P1" else "Player2",
                        request.json["event"],
                        request.json["value"]
                    ))

                    # System acknowledges game over
                    db[code].eventUpdates.append(EventUpdate(
                        "System",
                        "GameOver",
                        "Game over! Player 2 wins!"
                    ))

                    db[code].finished = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    return jsonify({"message": "Player 1 has acknowledged defeat. Game over. Player 2 wins."})
            else:
                # Event sender who won game attempting to send another GameOverAck event
                return errorObject("Game already over. Winner: {}".format(db[code].winner))
            
    return jsonify({"message": "Event update received successfully."})

@app.route('/getGameStatus', methods=['POST'])
def getGameStatus():
    headersCheck = checkHeaders()
    if not isinstance(headersCheck, bool):
        return headersCheck
    
    if "code" not in request.json:
        return errorObject("Missing parameter: code")
    if "playerID" not in request.json:
        return errorObject("Missing parameter: playerID")
    if request.json["playerID"] not in ["P1", "P2"]:
        return errorObject("Invalid player ID.")
    
    if request.json["code"] not in db:
        return errorObject("Game not found.")
    
    game = db[request.json["code"]]
    initialRepr = dictRepr(game)

    ## Mark events as seen
    for eventIndex in range(len(db[request.json["code"]].eventUpdates)):
        requesterID = "Player1" if request.json["playerID"] == "P1" else "Player2"
        if db[request.json["code"]].eventUpdates[eventIndex].player != requesterID:
            db[request.json["code"]].eventUpdates[eventIndex].acknowledged = True

    print(initialRepr)

    return initialRepr

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8500, debug=True)