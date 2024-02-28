
import audioop
import base64
#import pyaudioop as audioop 

import os
import threading
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech import SpeechSynthesizer, AudioConfig


load_dotenv()


def get_audio_string_from_text(text):

    full_audio = []

    class CustomAudioOutputStreamCallback(speechsdk.audio.PushAudioOutputStreamCallback):
        def __init__(self):
            super().__init__()
            self._audio_data = bytearray()

        def write(self, audio_buffer: memoryview) -> int:
            self._audio_data.extend(audio_buffer)
            full_audio.append(audio_buffer.tobytes())
            #print(audio_buffer.tobytes())
            return len(audio_buffer)

        def close(self) -> None:
            print("Stream closed")
            


    key = os.getenv("SPEECH_KEY")
    service_region = os.getenv("SPEECH_REGION")
    speech_synthesis_voice_name = "bg-BG-BorislavNeural"
    language = "bg-BG"

    speech_config = speechsdk.SpeechConfig(subscription=key, region=service_region, speech_recognition_language=language)
    #Raw8Khz16BitMonoPcm - no
    #Riff8Khz16BitMonoPcm - no
    speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Raw8Khz8BitMonoMULaw)

    speech_config.speech_synthesis_voice_name = speech_synthesis_voice_name

    audio_stream_cb = CustomAudioOutputStreamCallback()
    stream = speechsdk.audio.PushAudioOutputStream(audio_stream_cb)
    audio_config = speechsdk.audio.AudioOutputConfig(stream=stream)


    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    syntesis_done = threading.Event()

    def syntesizing_cb( evt):
        #print(f"Syntesizing: {evt}")
        pass
            
            
    def syntesized_cb(evt):
        print('SPEAKING READY:', evt.result.text)
        full_audio.append(evt.result.text)

    def canceled_cb(evt):
        #print('CANCELED Syntesis: {}'.format(evt.reason))
        syntesis_done.set()

    speech_synthesizer.synthesizing.connect(syntesizing_cb)
    speech_synthesizer.synthesis_completed.connect(syntesized_cb)
    speech_synthesizer.synthesis_canceled.connect(canceled_cb)


    # def syntesize_audio(text):
    #     speech_synthesizer.start_speaking_text_async(text)
    #     #syntesis_done.wait()
    #     speech_synthesizer.stop_speaking_async()

    #syntesize_thread = threading.Thread(target=syntesize_audio, kwargs ={'text': "здравейте"})
    #syntesize_thread.start()
    #speech_synthesizer.start_speaking_text_async()

    speech_synthesizer.speak_text_async(text).get()
    #syntesis_done.wait()
    #syntesize_audio('здравейте')
    final_audio = b''.join(full_audio)
    #print(final_audio)

    mulaw_audio = final_audio
    #audio = audioop.lin2ulaw(mulaw_audio, 2)
    base64_audio = base64.b64encode(mulaw_audio).decode("utf-8")
    return  base64_audio


#print(get_audio_string_from_text('здравейте'))