from flask import Flask
from flask_restful import Api

from py.chess import JoinLobby, CheckPlayerJoinLobby, CheckIsInLobby, SendMove, CancelLobby, CheckIsMoved, Surrender, SendChat

app = Flask(__name__)
api = Api(app)

api.add_resource(JoinLobby, "/JoinLobby/")
api.add_resource(CheckPlayerJoinLobby, "/CheckPlayerJoinLobby/<string:matchId>")
api.add_resource(CheckIsInLobby, "/CheckIsInLobby/<string:androidId>")
api.add_resource(SendMove, "/SendMove/")
api.add_resource(CancelLobby, "/CancelLobby/")
api.add_resource(CheckIsMoved, "/CheckIsMoved/")
api.add_resource(Surrender, "/Surrender/")
api.add_resource(SendChat, "/SendChat/")

if __name__ == "__main__":
  app.run()