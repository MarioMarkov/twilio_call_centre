import asyncio
import datetime

from dotenv import load_dotenv

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, WebSocket

load_dotenv()


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


connections = {}


@app.websocket("/client_messages")
async def client_messages(websocket: WebSocket):
    print("Connected client messages websocket")
    connections["client"] = websocket

    await websocket.accept()
    await connections["client"].send_json(
        {
            "event": "call_start",
            "from": "websocket",
            "from_number": "36723453452134",
            "timestamp": datetime.datetime.now().isoformat(),
        }
    )
    await asyncio.sleep(2)
    await connections["client"].send_json(
        {
            "event": "message",
            "from": "person",
            "result": "test recognition",
            "timestamp": datetime.datetime.now().isoformat(),
        }
    )
    await asyncio.sleep(1)
    await connections["client"].send_json(
        {
            "event": "message",
            "from": "bot",
            "result": "I am the bot ",
            "timestamp": datetime.datetime.now().isoformat(),
        }
    )
    await asyncio.sleep(1)

    await connections["client"].send_json({"event": "call_end"})


if __name__ == "__main__":
    # from pyngrok import ngrok
    import uvicorn
    import ngrok

    port = 8080

    listener = ngrok.forward(
        f"http://localhost:{port}",
        authtoken_from_env=True,
        domain="possum-enough-informally.ngrok-free.app",
    )
    public_url = listener.url()

    print(f"Waiting for calls on public url: {public_url}")
    try:

        uvicorn.run("main:app", host="localhost", port=port)
    except KeyboardInterrupt:
        import os
        import signal

        os.kill(os.getpid(), signal.SIGINT)
