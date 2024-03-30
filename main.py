import json
import sys
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from langserve import RemoteRunnable
from twilio.twiml.voice_response import VoiceResponse, Connect
from twilio.rest import Client
import re

# from urllib.parse import urlparse
from dotenv import load_dotenv

# from agent import agent_with_chat_history, message_history
from agent import create_agent
from helpers import (
    AzureSpeechRecognizer,
    play_text_raw_audio,
    speak_streaming_tokens,
)
from langchain_community.chat_message_histories import ChatMessageHistory

load_dotenv()

app = FastAPI()
twilio_client = Client()
agent = create_agent(retrieval_file_name="about_you")


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
def call(request: Request):
    """Accept a phone call."""

    # intiazlize voice response
    response = VoiceResponse()

    # start stream
    start = Connect()
    response.append(start)
    print(request.url.hostname)
    start.stream(url=f"wss://{request.url.hostname}/stream")

    return Response(content=str(response), media_type="application/xml")


@app.get("/call")
def call(request: Request):
    """Accept a phone call."""

    # intiazlize voice response
    response = VoiceResponse()

    # start stream
    start = Connect()
    response.append(start)
    print(request.url.hostname)
    start.stream(url=f"wss://{request.url.hostname}/stream")

    return Response(content=str(response), media_type="application/xml")


@app.websocket("/stream")
async def echo(websocket: WebSocket):
    """Receive and recognize audio stream."""

    # get_message()

    # samples_per_second=8000, bits_per_sample=16, channels=1
    speech_recognizer = AzureSpeechRecognizer(language="bg-BG")
    # speech_synthesizer = AzureSpeechSynthesizer(language="bg-BG", speech_synthesis_voice_name = 'bg-BG-BorislavNeural')

    prev_recognitions_len = 0

    # this stops recognizing when the bot is talking
    can_recognize = True

    # start accepting messages
    await websocket.accept()
    # await websocket.send_text(f"Echo: from ws")

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
                # welcome phrase
                # await play_text_raw_audio(
                #     websocket=websocket,
                #     stream_sid=packet["streamSid"],
                #     text="Здравейте, аз съм бот на абаут ю.",
                # )

            elif packet["event"] == "stop":
                print("\nStreaming has stopped")
                await websocket.close()
                break

            elif packet["event"] == "closed":
                await websocket.close()
                print("\nStreaming has closed")
                break

            elif packet["event"] == "media":
                if packet["media"]["track"] == "outbound":
                    print("sending audio.............")

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
                        await speak_streaming_tokens(
                            input=curr_recognition,
                            agent=agent,
                            message_history=message_history,
                            websocket=websocket,
                            stream_sid=packet["streamSid"],
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
        await websocket.close()


if __name__ == "__main__":
    from pyngrok import ngrok
    import uvicorn

    port = 5000
    # Twilio Config
    # bind_tls=True returns only https
    public_url = ngrok.connect(
        port, bind_tls=True, domain="possum-enough-informally.ngrok-free.app"
    ).public_url
    number = twilio_client.incoming_phone_numbers.list()[0]
    number.update(voice_url=public_url + "/call")
    print(f"Waiting for calls on {number.phone_number} public url: {public_url}")

    uvicorn.run("main:app", host="localhost", port=port)
