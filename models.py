import os, sys, datetime, random, copy

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

# Event Types:
## - PlayerJoined
## - RollingDice
## - DiceRolled
## - PowerupActivated
## - GameOverAck

class EventUpdate:
    def __init__(self, player, event, value) -> None:
        self.player = player
        self.event = event
        self.value = value
        self.acknowledged = False
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
        self.created = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.finished = None

def generateGameCode(notIn=[]):
    code = ""
    if len(notIn) == 0:
        for _ in range(6):
            code += str(random.randint(0, 9))
    else:
        while code in notIn:
            code = ""
            for _ in range(6):
                code += str(random.randint(0, 9))
    return code

def errorObject(message):
    return {"error": message}

def dictRepr(obj):
    obj = copy.deepcopy(obj)
    value = obj.__dict__
    for key in value:
        if isinstance(value[key], EventUpdate) or isinstance(value[key], Player) or isinstance(value[key], Game):
            value[key] = dictRepr(value[key])
    
    return value