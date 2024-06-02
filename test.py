from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging


app = FastAPI()
load_dotenv()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@app.websocket("/client_messages")
async def client_messages(websocket: WebSocket):
    print("Connected client messages websocket")
    await websocket.accept()
    import time

    try:
            print("Sending message")
            await websocket.send_json(
                {
                    "event": "message",
                    "from": "person",
                    "result": f"Mario",
                }
            )
    except WebSocketDisconnect:
        print("Client websocket disconnected")





if __name__ == "__main__":
    import uvicorn
    #from pyngrok import ngrok
    import ngrok
    port = 8080
    # public_url = ngrok.connect(
    #     port, bind_tls=True, domain="possum-enough-informally.ngrok-free.app"
    # ).public_url
    listener = ngrok.forward("http://localhost:8080",authtoken_from_env=True, 
                             domain="possum-enough-informally.ngrok-free.app")

    print(f"Ingress established at: {listener.url()}")
    # print(f"Ingress established at: {public_url}")



    uvicorn.run("test:app", host="localhost", port=port)
