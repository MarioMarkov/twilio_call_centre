import sys
import time
import json
import asyncio
import datetime

from dotenv import load_dotenv


# from langserve import RemoteRunnable
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect


from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect



from agent import create_agent
from helpers import (
    AzureSpeechRecognizer,
    play_text_raw_audio,
    speak_streaming_tokens,
)
from langchain_community.chat_message_histories import ChatMessageHistory

load_dotenv()


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

twilio_client = Client()
agent = create_agent(retrieval_file_name="about_you")


connections = {}


# remote_agent = RemoteRunnable(
#     "https://bot.happytree-937aa4bb.westus2.azurecontainerapps.io"
# )
message_history = ChatMessageHistory()
message_history.clear()


@app.post("/get_message")
def get_message():
    """Accept a phone call."""

    return "I am a bad guy"


@app.get("/call")
async def call(request: Request):
    """Accept a phone call."""
    # intiazlize voice response
    response = VoiceResponse()

    # start stream
    start = Connect()
    response.append(start)
    start.stream(url=f"wss://{request.url.hostname}/stream")

    return Response(content=str(response), media_type="application/xml")


@app.post("/call")
async def call(request: Request):
    """Accept a phone call."""

    request_details = await request.form()
    called_number = request_details.get("Called")
    from_number = request_details.get("From")
    to_state = request_details.get("ToState")
    caller_country = request_details.get("CallerCountry")
    direction = request_details.get("Direction")
    caller_phone_num = request_details.get("Caller")

    # intiazlize voice response
    response = VoiceResponse()

    # start stream
    start = Connect()
    response.append(start)
    start.stream(url=f"wss://{request.url.hostname}/stream/{caller_phone_num}")

    return Response(content=str(response), media_type="application/xml")


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

    # try:
    #     while True:
    #         data = await websocket.receive_text()
    #         # Send received message to all connected clients on the other WebSocket endpoint
    #         print(f"Received: {data}")
    # except WebSocketDisconnect:
    #     print("Client websocket disconnected")


@app.websocket("/stream/{caller_phone_num}")
async def echo(websocket: WebSocket, caller_phone_num: str):
    """Receive and recognize audio stream."""
    print("##############")
    # print(websocket.url)
    # print(websocket.base_url)
    # print(websocket.headers)
    # print(websocket.query_params)
    # print(websocket.client)
    # print("##############")
    # caller_phone_num = websocket.query_params

    # samples_per_second=8000, bits_per_sample=16, channels=1
    speech_recognizer = AzureSpeechRecognizer(language="bg-BG")
    # speech_synthesizer = AzureSpeechSynthesizer(language="bg-BG", speech_synthesis_voice_name = 'bg-BG-BorislavNeural')

    prev_recognitions_len = 0

    # this stops recognizing when the bot is talking
    can_recognize = True
    # print("Twilio websocket", websocket)

    connections["twilio"] = websocket
    # start accepting messages
    await websocket.accept()

    # catch the WebSocketDisconnect exception
    try:
        while True:

            data = await websocket.receive_text()
            packet = json.loads(data)

            # this means the bot has stopped speaking
            if packet["event"] == "mark":
                print("Received mark. Speaking has stopped")
                # start recognizing
                can_recognize = True

            if packet["event"] == "start":
                print("\nStreaming has started")
                await connections["client"].send_json(
                    {
                        "event": "call_start",
                        "from": "websocket",
                        "from_number": caller_phone_num,
                    }
                )

                # welcome phrase
                # await play_text_raw_audio(
                #     websocket=websocket,
                #     stream_sid=packet["streamSid"],
                #     text="Здравейте, аз съм бот на абаут ю.",
                # )

            elif packet["event"] == "stop":
                print("\nStreaming has stopped")
                await connections["client"].send_json({"event": "call_end"})
                await websocket.close()
                break

            elif packet["event"] == "closed":
                await websocket.close()
                print("\nStreaming has closed")
                break

            elif packet["event"] == "media":

                # get media data
                data = packet["media"]["payload"]

                # if the bot is not speaking -> recognize audio
                if can_recognize:
                    speech_recognizer.process_twilio_audio(f'{{"data": "{data}"}}')
                    curr_recognition = str(speech_recognizer.recognitions[-1])

                    # pass what the user said to the bot if something is recognized
                    if (
                        prev_recognitions_len < len(speech_recognizer.recognitions)
                        and curr_recognition != ""
                    ):
                        print("Recognized: ", speech_recognizer.recognitions)
                        prev_recognitions_len = len(speech_recognizer.recognitions)

                        # disable recognized until speaking is finished
                        can_recognize = False
                        await connections["client"].send_json(
                            {
                                "event": "message",
                                "from": "person",
                                "result": curr_recognition,
                                "timestamp": datetime.datetime.now().isoformat(),
                            }
                        )
                        bot_answer = await speak_streaming_tokens(
                            input=curr_recognition,
                            agent=agent,
                            message_history=message_history,
                            websocket=websocket,
                            stream_sid=packet["streamSid"],
                        )

                        await connections["client"].send_json(
                            {
                                "event": "message",
                                "from": "bot",
                                "result": bot_answer,
                                "timestamp": datetime.datetime.now().isoformat(),
                            }
                        )

                        await websocket.send_json(
                            {
                                "event": "mark",
                                "streamSid": packet["streamSid"],
                                "mark": {"name": "my label"},
                            }
                        )

                # Hang up if 3 consecutive recognitions are empty
                if speech_recognizer.recognitions[-4:] == [""] * 4:
                    print("Disconnecting...")
                    await websocket.close()
                    break

    except WebSocketDisconnect:
        print("WebSocketDisconnect caught")


if __name__ == "__main__":
    # from pyngrok import ngrok
    import uvicorn
    import ngrok

    port = 8080
    # Twilio Config
    # bind_tls=True returns only https
    # public_url = ngrok.connect(
    #     port, bind_tls=True, domain="possum-enough-informally.ngrok-free.app"
    # ).public_url
    listener = ngrok.forward(
        f"http://localhost:{port}",
        authtoken_from_env=True,
        domain="possum-enough-informally.ngrok-free.app",
    )
    public_url = listener.url()
    # print(f"Ingress established at: {public_url}")
    number = twilio_client.incoming_phone_numbers.list()[0]
    number.update(voice_url=public_url + "/call")

    print(f"Waiting for calls on {number.phone_number} public url: {public_url}")
    try:

        uvicorn.run("main:app", host="localhost", port=port)
    except KeyboardInterrupt:
        import os
        import signal

        os.kill(os.getpid(), signal.SIGINT)
