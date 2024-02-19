import json
import os
import threading
import wave
import base64
import audioop
import soundfile
from dotenv import load_dotenv 
from scipy.io import wavfile
import ffmpeg
import wave
import array
#import wavefile

load_dotenv()


import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech import SpeechSynthesizer, AudioConfig

class AzureSpeechRecognizer:
    key = os.getenv("SPEECH_KEY")
    service_region = os.getenv("SPEECH_REGION")

    def __init__(self, language:str):

        self.language = language
        audio_format = speechsdk.audio.AudioStreamFormat(samples_per_second=8000, bits_per_sample=16,
                                                         channels=1, wave_stream_format=speechsdk.AudioStreamWaveFormat.MULAW)
        self.stream = speechsdk.audio.PushAudioInputStream(stream_format=audio_format)
        self.audio_config = speechsdk.audio.AudioConfig(stream=self.stream)
        self.recognition_done = threading.Event()
        
        # Adjust silence detection time limit
        initial_silence_timeout_ms = 3 * 1e3
        end_silence_timeout_ms = 3 * 1e3  # Example value: 10 seconds
        babble_timeout_ms = 3 * 1e3  # Example value: 10 seconds
        end_silence_timeout_ambiguous_ms = 3  * 1e3  # Example value: 10 seconds
        template = ("wss://{}.stt.speech.microsoft.com/speech/recognition"
                    "/conversation/cognitiveservices/v1?initialSilenceTimeoutMs={:d}"
                    "&endSilenceTimeoutMs={:d}&babbleTimeoutMs={:d}&endSilenceTimeoutAmbiguousMs={:d}")

        endpoint = template.format(self.service_region, int(initial_silence_timeout_ms), int(end_silence_timeout_ms),
                                   int(babble_timeout_ms), int(end_silence_timeout_ambiguous_ms))

        self.speech_config = speechsdk.SpeechConfig(subscription=self.key, speech_recognition_language=language, endpoint=endpoint)
        self.speech_recognizer = speechsdk.SpeechRecognizer(speech_config=self.speech_config, audio_config=self.audio_config)

        self.recognitions = [""]

        self.speech_recognizer.recognizing.connect(self.recognizing_cb)
        self.speech_recognizer.recognized.connect(self.recognized_cb)
        self.speech_recognizer.session_stopped.connect(self.session_stopped_cb)
        self.speech_recognizer.canceled.connect(self.canceled_cb)

        self.recognize_thread = threading.Thread(target=self.recognize_audio)
        self.recognize_thread.start()

    def session_stopped_cb(self, evt):
        print('SESSION STOPPED: {}'.format(evt))
        self.recognition_done.set()

    def canceled_cb(self, evt):
        print('CANCELED: {}'.format(evt.reason))
        self.recognition_done.set()

    def recognizing_cb(self, evt):
        print(f"RECOGNIZING: {evt}")

    def recognized_cb(self, evt):
        print('RECOGNIZED:', evt.result.text)
        self.recognitions.append(evt.result.text)

    def push_audio(self, audio_data):
        audio_bytes = base64.b64decode(audio_data.get("data", "").encode())
        self.stream.write(audio_bytes)

    def recognize_audio(self):
        self.speech_recognizer.start_continuous_recognition()
        self.recognition_done.wait()
        self.speech_recognizer.stop_continuous_recognition()

    def process_twilio_audio(self, twilio_audio_json):
        audio_data = json.loads(twilio_audio_json)
        self.push_audio(audio_data)


class AzureSpeechSynthesizer:
    key = os.getenv("SPEECH_KEY")
    service_region = os.getenv("SPEECH_REGION")

    def __init__(self, language: str , speech_synthesis_voice_name: str):

        self.speech_config = speechsdk.SpeechConfig(subscription=self.key, region=self.service_region, speech_recognition_language=language)
        self.speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Raw8Khz8BitMonoMULaw)

        self.speech_config.speech_synthesis_voice_name = speech_synthesis_voice_name

        self.audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)

        self.speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config, audio_config=self.audio_config)

    def text_to_wav(self, text: str, file_name: str = "output.wav"):
        audio_output = AudioConfig(filename=file_name)
        synthesizer = SpeechSynthesizer(speech_config=self.speech_config, audio_config=audio_output)
        synthesizer.speak_text_async(text).get()

def play_audio(file_path, ws, stream_sid):
    #print(mulaw_base64)
    pass

def send_audio_custom(file_path, ws, stream_sid):
    # Open the raw audio file
    with open(file_path, 'rb') as f:
        # Read the raw data
        raw_data = f.read()

    # Encode the raw data to Base64
    base64_encoded = base64.b64encode(raw_data)

    # Convert Base64 bytes to a string
    base64_string = base64_encoded.decode('utf-8')
    
    # Split the encoded audio data into chunks
    for i in range(0, len(base64_string), 216):
        # Get the chunk
        chunk = base64_string[i:i + 216]

        # Send the chunk to the websocket
        ws.send(
            {
                'type': 'asd',
                "event": "media",
                "streamSid": stream_sid,
                "media": {
                    "payload": chunk
                }
            }
        )


def send_raw_audio(file_path, ws, stream_sid):
    data, samplerate = soundfile.read(file_path)
    soundfile.write(file_path, data, samplerate)
    with wave.open(file_path, 'rb') as wav_file:
        while True:
            wav_data = wav_file.readframes(320)
            if not wav_data:
                ws.send(
                    {
                        "event": "mark",
                        "streamSid": stream_sid,
                        "mark": {
                            "name": "my label"
                        }
                    }
                )
                break
        wav_file.readframes()
        mulaw_data = audioop.lin2ulaw(wav_file, 2)
        base64_audio = base64.b64encode(mulaw_data).decode("utf-8")

        ws.send(
            {
                "event": "media",
                "streamSid": stream_sid,
                "media": {
                    "payload": base64_audio
                }
            }
        )