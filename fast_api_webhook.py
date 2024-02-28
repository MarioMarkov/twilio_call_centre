import json
import sys
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect
from twilio.rest import Client
#from urllib.parse import urlparse
from streaming_audio_recognizer import get_audio_string_from_text
from dotenv import load_dotenv
from agent import agent_with_chat_history
from helpers import AzureSpeechRecognizer, AzureSpeechSynthesizer,  play_text_raw_audio
load_dotenv()

app = FastAPI()
twilio_client = Client()

@app.get('/call')
def call(request: Request):
    """Accept a phone call."""
    response = VoiceResponse()
   
    start = Connect()
    response.append(start)
    print(request.url.hostname)
    start.stream(url=f'wss://{request.url.hostname}/stream')
   
    return Response(content=str(response), media_type="application/xml")



@app.post('/call')
def call(request: Request):
    """Accept a phone call."""
    response = VoiceResponse()

    start = Connect()
    response.append(start)
    print(request.url.hostname)

    start.stream(url=f'wss://{request.url.hostname}/stream')

    return Response(content=str(response), media_type="application/xml")

@app.websocket("/stream")
async def echo(websocket: WebSocket):
    """Receive and recognize audio stream."""
    speech_recognizer = AzureSpeechRecognizer(language="bg-BG")
    speech_synthesizer = AzureSpeechSynthesizer(language="bg-BG", speech_synthesis_voice_name = 'bg-BG-BorislavNeural')
    prev_recognitions_len = 0
    
    await websocket.accept()
    print("Streaming...")
    try:
        while True:
            message = await websocket.receive_text()
            packet = json.loads(message)
            
            if packet["event"] == "mark":
                print('Received mark. Speaking has stopped')
            
            if packet["event"] == "start":
                print('\nStreaming has started')
                # Here you can put .wav file with welcome phrase
                # samples_per_second=8000, bits_per_sample=16, channels=1
                await play_text_raw_audio(websocket=websocket,
                                          stream_sid=  packet["streamSid"],
                                          text= "Здравейте, аз съм бот на А едно.")

            elif packet['event'] == 'stop':
                print('\nStreaming has stopped')
                await websocket.close()
                break
                

            elif packet['event'] == 'closed':
                await websocket.close()
                print('\nStreaming has closed')
                break
                
            elif packet['event'] == 'media':
                if packet['media']['track'] == 'outbound':
                    print('sending audio.............')
                
                data = packet["media"]["payload"]

                speech_recognizer.process_twilio_audio(f'{{"data": "{data}"}}')
                curr_recognition = str(speech_recognizer.recognitions[-1])
            
                # having new recognition
                if prev_recognitions_len < len(speech_recognizer.recognitions) and curr_recognition != "":
                    print("Recognized: ", speech_recognizer.recognitions)
                    prev_recognitions_len = len(speech_recognizer.recognitions)    
                    answer = agent_with_chat_history.invoke({'input': curr_recognition}, {'configurable': {'session_id': 'asd'}})['output']
                    print(f"Chatbot answer {answer}")
                    await play_text_raw_audio(websocket=websocket,
                                          stream_sid=  packet["streamSid"],
                                          text= answer)
                        
               
                # Hang up if 3 consecutive recognitions are empty
                if speech_recognizer.recognitions[-3:] == [""] * 3:
                    print("Disconnecting...")
                    await websocket.close()
                    break
                    
                    
    except WebSocketDisconnect:
        print("WebSocketDisconnect")
        await websocket.close()


if __name__ == '__main__':
    from pyngrok import ngrok
    import uvicorn
    port = 5000
    # Twilio Config 
    public_url = ngrok.connect(port, bind_tls=True).public_url
    number = twilio_client.incoming_phone_numbers.list()[0]
    number.update(voice_url=public_url + '/call')
    print(f'Waiting for calls on {number.phone_number} public url: {public_url}')
    
    uvicorn.run("fast_api_webhook:app", host="localhost",port=port)