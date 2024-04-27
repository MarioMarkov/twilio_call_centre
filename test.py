from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect

app = FastAPI()

@app.get("/get_message")
def call(request: Request):
    """Accept a phone call."""

    return "I am a bad guy"


if __name__ == "__main__":
    from pyngrok import ngrok
    import uvicorn

    port = 5000
    # Twilio Config
    public_url = ngrok.connect(port, bind_tls=True).public_url
    print(f"Public url: {public_url}")

    uvicorn.run("test:app", host="localhost", port=port)
