from websockets import server

class ClientExtention:
    def __init__(self, websocket: server.WebSocketServerProtocol):
        self.websocket = websocket
        self.project = ""
        self.ospath = "./"
        self.sdk = ""
        self.conf = ""
        self.scheme = ""
        self.target = ""

    async def send(self, message: str):
        await self.websocket.send(message)
