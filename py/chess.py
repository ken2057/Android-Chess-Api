import string, secrets, json
from datetime import datetime
from flask_restful import Resource
from pymongo import MongoClient
from flask import request

mongodb = ""
if mongodb == "":
	raise Exception("Insert mongodb link")
client = MongoClient(mongodb)
db = client.chess_online
dateFormat = '%Y-%m-%d %H:%M:%S'

class JoinLobby(Resource):
	def createRandomMatchID(self, length = 20):
		return ''.join(secrets.choice(string.ascii_uppercase + string.digits + string.ascii_lowercase) for _ in range(length))

	def createLobby(self, androidId):
		print("Create lobby: ", end=' ')
		matchId = self.createRandomMatchID();
		db.lobby.insert({ '_id': matchId, 'player1': androidId, 'time': datetime.now(), 'player1_lastOnline': datetime.now() })
		print("Done")
		return matchId

	def findLobbyWatting(self, androidId):
		#check lobby out of time
		lobby = [];

		while lobby != None:
			#get lobby without player2 and still not winning
			lobby = db.lobby.find_one(  { '$and': [{ 'player2': { '$exists': False }}, { 'winner': { '$exists': False } } ] } )
			try:
				timePlayer1 = (datetime.now() - datetime.strptime(str(lobby['player1_lastOnline'])[:-7], dateFormat)).total_seconds()

				#if both last time online 2 player > 2 minutes 
				#--> close the lobby
				#else
				#--> break the loop
				if(timePlayer1 > 1*60):
					db.lobby.update_one({'_id': lobby['matchId']}, {'$set': {'winner': 'None'}})
				else:
					break
			except Exception as e:
				lobby = None
				break
		print(lobby)

		if(lobby != None):
			db.lobby.update({ '_id': lobby['_id']}, 
							{ '$set': { 
								'player2': androidId, 
								'player2_lastOnline': datetime.now(), 
								'history': [],
								'chat': []
								} 
							})
			return lobby['_id']

		return -1

	def post(self):
		try:
			json = request.get_json()
			print(json)
			if('androidId' in json):
				matchId = self.findLobbyWatting(json['androidId'])
				
				if(matchId == -1):
					matchId = self.createLobby(json['androidId'])
				match = { 'matchId': matchId }

				return match, 200
		except Exception as e:
			print('error join: ',e)
		return -1, 200
		
class CheckIsInLobby(Resource):
	def findLobbyIn(self, androidId):
		lobby = db.lobby.find_one( { '$and': [{ '$or': [ {'player1': androidId}, {'player2': androidId}] }, {'winner': { '$exists': False }} ] })
		try:
			timePlayer1 = (datetime.now() - datetime.strptime(str(lobby['player1_lastOnline'])[:-7], dateFormat)).total_seconds()
			timePlayer2 = (datetime.now() - datetime.strptime(str(lobby['player2_lastOnline'])[:-7], dateFormat)).total_seconds()

			if(timePlayer1 + timePlayer2 < 60):
				return lobby['_id']

			db.update_one({'_id': lobby['_id']},{'$set': {'winner': 'None'}})
		except Exception as e:
			print('check is in lobby ',e)

		return -1

	def get(self, androidId):
		result = { "result": self.findLobbyIn(androidId) }
		return result, 200

class CheckPlayerJoinLobby(Resource):
	def checkLobby(self, matchId):
		lobby = db.lobby.find_one({ '_id': matchId })
		db.lobby.update_one({'_id': matchId}, {'$set': {'player1_lastOnline': datetime.now()}})

		return ['player2' in lobby, lobby['player1']]

	def get(self, matchId):	
		try:
			r = self.checkLobby(matchId)
			result = { '2players': r[0], 'white': r[1] }

			return result, 200
		except Exception as e:
			print(e)
			return "Error", 200

class CancelLobby(Resource):
	def post(self):
		json = ''
		try:
			json = request.get_json()
			if('androidId' in json and 'matchId' in json):
				lobby = db.lobby.find_one({'_id': json['matchId']})

				if(lobby['player1'] == json['androidId']):
					db.lobby.remove({'_id': json['matchId']})
		except Exception as e:
			print(e)
		return "Done", 200

class SendMove(Resource):
	def post(self):
		try:
			print('send move',end=' ')
			json = request.get_json()
			match = db.lobby.find_one({ '_id' : json['matchId']})
			print(json)
			isWhite = match['player1'] == json['androidId']

			#convert db type for android can readable			
			oldPos = [ json['oldPos'][0], json['oldPos'][-1]]
			newPos = [ json['newPos'][0], json['newPos'][-1]]
			killPos = [ json['killPos'].split(' ')[0], json['killPos'].split(' ')[1] ]
			castlingNewPos = [ json['castlingNewPos'].split(' ')[0], json['castlingNewPos'].split(' ')[1] ]
			castlingOldPos = [ json['castlingOldPos'].split(' ')[0], json['castlingOldPos'].split(' ')[1] ]

			#reverse the result if player checking not white
			if(not isWhite):
				oldPos = [ str(7-int(x)) for x in oldPos]
				newPos = [ str(7-int(x)) for x in newPos]

				if(castlingNewPos[0] != '-1'):
					castlingOldPos = [ str(7-int(x)) for x in castlingOldPos]
					castlingNewPos = [ str(7-int(x)) for x in castlingNewPos]

				if(killPos[0] != '-1'):
					killPos = [ str(7-int(x)) for x in killPos]

			if(killPos[0] == '-1'):
				killPos = [' ',' ']

			if(castlingNewPos[0] == '-1'):
				castlingNewPos = [' ',' ']
				castlingOldPos = [' ',' ']

			history = []
			if('history' in match):
				history = match['history']

			#if have winner
			#--> update db
			winner = ' '
			if(json['isWin'] != 0):
				if(json['isWin'] == 2):
					winner = 'D'
					db.lobby.update_one({'_id': match['_id']}, {'$set': {'winner': 'draw'}} )
				elif(json['isWin'] == 1):
					#check white
					if(json['androidId'] == match['player1']):
						winner = 'W'
						db.lobby.update_one({'_id': match['_id']}, {'$set': {'winner': match['player1']}})
					else:
						winner = 'B'
						db.lobby.update_one({'_id': match['_id']}, {'$set': {'winner': match['player2']}})
				else:
					if(json['androidId'] == match['player1']):
						winner = 'B'
						db.lobby.update_one({'_id': match['_id']}, {'$set': {'winner': match['player2']}})
					else:
						winner = 'W'
						db.lobby.update_one({'_id': match['_id']}, {'$set': {'winner': match['player1']}})

			history.append(	''.join(oldPos)
							+"-"+''.join(newPos)
							+"-"+''.join(killPos)
							+'-'+''.join(castlingOldPos)
							+""+''.join(castlingNewPos)
							+"-"+json['pawnEvolveTo']
							+'-'+winner)
			
			#update player last online
			if(json['androidId'] == match['player1']):
				db.lobby.update_one({'_id': match['_id']}, {'$set': {'history': history, 'player1_lastOnline': datetime.now() } })
			else:
				db.lobby.update_one({'_id': match['_id']}, {'$set': {'history': history, 'player2_lastOnline': datetime.now() } })				

			print("Done")

		except Exception as e:
			print(e)
			return "Error", 200
		return "Done", 200

class CheckIsMoved(Resource):
	def checkOnline(self, androidId, matchId, lobby):
		time = None

		if(androidId == lobby['player1']):
			time = (datetime.now() - datetime.strptime(str(lobby['player2_lastOnline'])[:-7], dateFormat)).total_seconds()
			db.lobby.update_one({'_id': lobby['_id']}, { '$set': { 'player1_lastOnline': datetime.now() } })
		else:
			time = (datetime.now() - datetime.strptime(str(lobby['player1_lastOnline'])[:-7], dateFormat)).total_seconds()
			db.lobby.update_one({'_id': lobby['_id']}, { '$set': { 'player2_lastOnline': datetime.now() } })

		if (time > 60 and 'winner' not in lobby):
			#if player disconnect more than 60s 
			# opponent will get win
			win = 'B'
			if (androidId == lobby['player1']):
				win='W'

			history = lobby['history']
			history.append("00-00-  -    - -"+win)
		
			db.lobby.update_one({'_id': lobby['_id']}, {'$set': {'winner': androidId, 'history': history}})

	def post(self):
		try:
			json = request.get_json()

			for k in ['androidId', 'matchId', 'numMove', 'numChat']:
				if(k not in json):
					print('Missing ', k)
					return 'Not valid', 200

			lobby = db.lobby.find_one({ '_id': json['matchId'] })

			#check if correct all information
			if(json['androidId'] in [lobby['player1'], lobby['player2']]):
				# if('winner' in lobby):
					# return {'winner': lobby['winner']} , 200

				self.checkOnline(json['androidId'], json['matchId'], lobby)
				
				#check move
				lastMove = ""
				if(json['numMove'] == len(lobby['history'])-1):
					lastMove = lobby['history'][-1]
					if(lobby['player1'] != json['androidId']):
						temp = lastMove.split('-')
						posOld = [str(7-int(temp[0][0])), str(7-int(temp[0][1]))]
						posNew = [str(7-int(temp[1][0])), str(7-int(temp[1][1]))]
						posKill = temp[2]
						posCastling = temp[3]
						#convert db type for android can readable
						if(' ' not in posKill[0]):
							posKill = [str(7-int(posKill[0])), str(7-int(posKill[1]))]
						if(' ' not in posCastling[0]):
							posCastling = [str(7-int(posCastling[0])), 
											str(7-int(posCastling[1])), 
											str(7-int(posCastling[2])), 
											str(7-int(posCastling[3]))]

						lastMove = str(	''.join(posOld)
										+'-'+''.join(posNew)
										+'-'+''.join(posKill)
										+'-'+''.join(posCastling)
										+'-'+temp[-2]
										+'-'+temp[-1])

				#check chat
				lastChat = []
				if(json['numChat'] != len(lobby['chat'])):
					lastChat = lobby['chat'][json['numChat'] - len(lobby['chat']):]

				if (lastMove != "" or lastChat != []):
					return { 	'result': lastMove, 
								'chat': lastChat,
									'totalMove': len(lobby['history']) }, 200

				return 'OK', 200

			return "Not valid", 200

		except Exception as e:
			print('Error CheckIsMoved ',e)
			return "Error", 200

class Surrender(Resource):
	def post(self):
		try:
			json = request.get_json()

			for k  in ['androidId', 'matchId']:
				if(k not in json):
					print('Missing ', k)
					return "Not valid", 200

			lobby = db.lobby.find_one({'_id': json['matchId']})

			#check infomation valid
			if(json['androidId'] in [lobby['player1'], lobby['player2']]):
				if(json['androidId'] == lobby['player1']):
					db.lobby.update_one({'_id': lobby['_id']}, { '$set': { 'winner': lobby['player2'] } })
				else:
					db.lobby.update_one({'_id': lobby['_id']}, { '$set': { 'winner': lobby['player1'] } })

			return "Done", 200

		except Exception as e:
			print('Surrender ', e)
			return "Error", 200

class SendChat(Resource):
	def post(self):
		try:
			json = request.get_json()

			for k in ['androidId', 'matchId', 'chatMsg']:
				if(k not in json):
					print('Missing ', k)
					return 'Not valid', 200

			lobby = db.lobby.find_one({ '_id': json['matchId'] })

			if(json['androidId'] in [lobby['player1'], lobby['player2']]):
				chatHistory = lobby['chat']
				who = "Black"
				if(json['androidId'] == lobby['player1']):
					who ="White"
				chatHistory.append([ who, json['chatMsg']])

				db.lobby.update_one({'_id': lobby['_id']}, {'$set': {'chat': chatHistory}})


			return "Ok", 200
		except Exception as e:
			print("Error send chat ", e)
			return "Error", 200
			