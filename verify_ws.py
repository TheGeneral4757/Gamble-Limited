
import asyncio
import websockets

async def main():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        print(f"Connected to {uri}")
        response = await websocket.recv()
        print(f"< {response}")

if __name__ == "__main__":
    asyncio.run(main())
