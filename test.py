from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect

app = FastAPI()


@app.websocket("/client_messages")
async def client_messages(websocket: WebSocket):
    print("Connected client messages websocket")
    await websocket.accept()
    import time

    try:
        for i in range(0, 3):
            time.sleep(2)
            print("Sending message")
            await websocket.send_json(
                {
                    "event": "message",
                    "from": "person",
                    "result": f"Mario {i}",
                }
            )
    except WebSocketDisconnect:
        print("Client websocket disconnected")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("test:app", host="localhost", port=5000)
