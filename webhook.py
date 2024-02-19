import json
import time
import os
from flask import Flask, request
from flask_sock import Sock
from twilio.twiml.voice_response import VoiceResponse, Connect
from twilio.rest import Client
from scipy.io import wavfile

from medium_tools import AzureSpeechRecognizer, AzureSpeechSynthesizer, play_audio, send_audio_custom, send_raw_audio

app = Flask(__name__)
sock = Sock(app)
twilio_client = Client()

@app.route('/call', methods=['POST', 'GET'])
def call():
    """Accept a phone call."""
    response = VoiceResponse()
    #response.say("Hello ")

    start = Connect()
    response.append(start)
    start.stream(url=f'wss://{request.host}/stream')

    return str(response), 200, {'Content-Type': 'text/xml'}

@sock.route('/stream')
def stream(ws):
    """Receive and recognize audio stream."""
    speech_recognizer = AzureSpeechRecognizer(language="bg-BG")
    speech_synthesizer = AzureSpeechSynthesizer(language="bg-BG", speech_synthesis_voice_name = 'bg-BG-BorislavNeural')
    same_last_recognition_count = 0 
    prev_recognition = ''
    while ws.connected:
        message = ws.receive()
        packet = json.loads(message)
        if packet["event"] == "start":
            print('\nStreaming has started')
            # Here you can put .wav file with welcome phrase
            # samples_per_second=8000, bits_per_sample=16, channels=1
            #send_raw_audio("welcome.wav", ws, packet["streamSid"])

        elif packet['event'] == 'stop':
            print('\nStreaming has stopped')

        elif packet['event'] == 'mark':
            print(packet)
            
        elif packet['event'] == 'media':
            if 'type' in packet:
                print('evrika')
            
            data = packet["media"]["payload"]
          
            speech_recognizer.process_twilio_audio(f'{{"data": "{data}"}}')
            curr_recognition = str(speech_recognizer.recognitions[-1])
          
            if curr_recognition != "":
                #user_request = curr_recognition
                #print("Recognized", speech_recognizer.recognitions)
                print(f"Recognized: {speech_recognizer.recognitions}, Count : {same_last_recognition_count}")
                #speech_synthesizer.text_to_wav("аз съм бот", wav_path)
                #wav_path = "output.wav"
                wav_path = "voice.raw"

                #speech_synthesizer.text_to_wav("аз съм бот", wav_path)
                send_audio_custom(wav_path, ws, packet["streamSid"])

                if curr_recognition == prev_recognition:
                    same_last_recognition_count +=1
                else: 
                    same_last_recognition_count = 0 
                         
                prev_recognition = curr_recognition
            
            #print(speech_recognizer.recognitions[-5:])
            if speech_recognizer.recognitions[-5:] == [""] * 10:
                ws.connected = False
            # if same_last_recognition_count >=100:
            #     print("Disconneting")
            #     ws.connected = False

if __name__ == '__main__':
    from pyngrok import ngrok
    port = 5000
    public_url = ngrok.connect(port, bind_tls=True).public_url
    number = twilio_client.incoming_phone_numbers.list()[0]
    number.update(voice_url=public_url + '/call')
    print(f'Waiting for calls on {number.phone_number} public url: {public_url}')

    app.run(port=port)