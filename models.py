import os, sys, datetime, random

class Player:
    def __init__(self, characterName, hp, exp, skill, emoji, repName, progress, skipNextTurn) -> None:
        self.characterName = characterName
        self.hp = hp
        self.exp = exp
        self.skill = skill
        self.emoji = emoji
        self.repName = repName
        self.progress = progress
        self.skipNextTurn = skipNextTurn

class EventUpdate:
    def __init__(self, player, event, value) -> None:
        self.player = player
        self.event = event
        self.value = value
        self.timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class Game:
    def __init__(self, code, player1: Player, progressGoal, player2: Player=None) -> None:
        self.code = code
        self.player1 = player1
        self.player2 = player2
        self.progressGoal = progressGoal
        self.winner = None
        self.currentTurn = "Player1"
        self.eventUpdates = []

def generateGameCode():
    code = ""
    for i in range(6):
        code += str(random.randint(0, 9))
    return code

def errorObject(message):
    return {"error": message}