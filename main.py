# Rcode
import asyncio
import websockets
import json

async def serve_handler(websocket, path):
    async for message in websocket:
        ctx = json.loads(message)
        await websocket.send(message)

async def main():
    async with websockets.serve(serve_handler, "0.0.0.0", 8765):
        await asyncio.Future()
 
if __name__ == "__main__":
    asyncio.run(main())
