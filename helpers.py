import json
import os
import threading
import wave
import base64
import audioop
from fastapi import WebSocket
import soundfile
import wave
from dotenv import load_dotenv

# import wavefile

load_dotenv()
import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech import SpeechSynthesizer, AudioConfig

key = os.getenv("SPEECH_KEY")
service_region = os.getenv("SPEECH_REGION")
speech_synthesis_voice_name = "bg-BG-BorislavNeural"
language = "bg-BG"


class AzureSpeechRecognizer:

    def __init__(self, language: str):

        self.language = language
        audio_format = speechsdk.audio.AudioStreamFormat(
            samples_per_second=8000,
            bits_per_sample=16,
            channels=1,
            wave_stream_format=speechsdk.AudioStreamWaveFormat.MULAW,
        )
        self.stream = speechsdk.audio.PushAudioInputStream(stream_format=audio_format)
        self.audio_config = speechsdk.audio.AudioConfig(stream=self.stream)
        self.recognition_done = threading.Event()

        # Adjust silence detection time limit
        initial_silence_timeout_ms = 10 * 1e3
        end_silence_timeout_ms = 10 * 1e3  # Example value: 10 seconds
        babble_timeout_ms = 10 * 1e3  # Example value: 10 seconds
        end_silence_timeout_ambiguous_ms = 10 * 1e3  # Example value: 10 seconds
        # template = ("wss://{}.stt.speech.microsoft.com/speech/recognition"
        #             "/conversation/cognitiveservices/v1?initialSilenceTimeoutMs={:d}"
        #             "&endSilenceTimeoutMs={:d}&babbleTimeoutMs={:d}&endSilenceTimeoutAmbiguousMs={:d}")

        # endpoint = template.format(self.service_region, int(initial_silence_timeout_ms), int(end_silence_timeout_ms),
        #                            int(babble_timeout_ms), int(end_silence_timeout_ambiguous_ms))

        self.speech_config = speechsdk.SpeechConfig(
            subscription=key,
            speech_recognition_language=language,
            region=service_region,
        )
        # self.speech_config.set_properties_by_name({"SpeechServiceConnection_InitialSilenceTimeoutMs","10000"} )
        self.speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config, audio_config=self.audio_config
        )
        self.recognitions = [""]

        self.speech_recognizer.recognizing.connect(self.recognizing_cb)
        self.speech_recognizer.recognized.connect(self.recognized_cb)
        self.speech_recognizer.session_stopped.connect(self.session_stopped_cb)
        self.speech_recognizer.canceled.connect(self.canceled_cb)

        self.recognize_thread = threading.Thread(target=self.recognize_audio)
        self.recognize_thread.start()

    def session_stopped_cb(self, evt):
        print("SESSION STOPPED: {}".format(evt))
        self.recognition_done.set()

    def canceled_cb(self, evt):
        print("CANCELED: {}".format(evt.reason))
        self.recognition_done.set()

    def recognizing_cb(self, evt):
        # print(f"RECOGNIZING: {evt}")
        pass

    def recognized_cb(self, evt):
        # print('RECOGNIZED:', evt.result.text)
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


# old class does not work
class AzureSpeechSynthesizer:
    key = os.getenv("SPEECH_KEY")
    service_region = os.getenv("SPEECH_REGION")

    def __init__(self, language: str, speech_synthesis_voice_name: str):

        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.key,
            region=self.service_region,
            speech_recognition_language=language,
        )
        # Raw8Khz16BitMonoPcm - no
        # Riff8Khz16BitMonoPcm - no
        self.speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff8Khz8BitMonoMULaw
        )

        self.speech_config.speech_synthesis_voice_name = speech_synthesis_voice_name

        self.audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)

        self.speech_synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config, audio_config=self.audio_config
        )

    def text_to_wav(self, text: str, file_name: str = "output.wav"):
        audio_output = AudioConfig(filename=file_name)
        synthesizer = SpeechSynthesizer(
            speech_config=self.speech_config, audio_config=audio_output
        )
        synthesizer.speak_text_async(text).get()


async def text_to_base64_audio(text):
    """Convert text to base64 audio using azure speech synthesis"""

    # stores the byte64 encoded string
    full_audio = []

    class CustomAudioOutputStreamCallback(
        speechsdk.audio.PushAudioOutputStreamCallback
    ):
        def __init__(self):
            super().__init__()
            # define the bytearray of the audio data
            # self._audio_data = bytearray()

        def write(self, audio_buffer: memoryview) -> int:
            # write the current audio received to the audio_data
            # self._audio_data.extend(audio_buffer)

            # append the audio buffer to the full audio
            full_audio.append(audio_buffer.tobytes())
            # print(audio_buffer.tobytes())
            return len(audio_buffer)

        def close(self) -> None:
            print("Stream closed")

    speech_config = speechsdk.SpeechConfig(
        subscription=key, region=service_region, speech_recognition_language=language
    )

    # output raw audio in mulaw-x format 8khz and 8bit
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Raw8Khz8BitMonoMULaw
    )

    # set voice name
    speech_config.speech_synthesis_voice_name = speech_synthesis_voice_name

    # make audio stream to push the audio to the array insted of a file
    audio_stream_cb = CustomAudioOutputStreamCallback()
    stream = speechsdk.audio.PushAudioOutputStream(audio_stream_cb)
    audio_config = speechsdk.audio.AudioOutputConfig(stream=stream)

    # initizlize the speech syntesizer
    speech_synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=audio_config
    )
    syntesis_done = threading.Event()

    def syntesizing_cb(evt):
        # print(f"Syntesizing: {evt}")
        pass

    def syntesized_cb(evt):
        print("SPEAKING READY:", evt.result.text)
        full_audio.append(evt.result.text)

    def canceled_cb(evt):
        # print('CANCELED Syntesis: {}'.format(evt.reason))
        syntesis_done.set()

    speech_synthesizer.synthesizing.connect(syntesizing_cb)
    speech_synthesizer.synthesis_completed.connect(syntesized_cb)
    speech_synthesizer.synthesis_canceled.connect(canceled_cb)

    # def syntesize_audio(text):
    #     speech_synthesizer.start_speaking_text_async(text)
    #     #syntesis_done.wait()
    #     speech_synthesizer.stop_speaking_async()

    # syntesize_thread = threading.Thread(target=syntesize_audio, kwargs ={'text': "здравейте"})
    # syntesize_thread.start()
    # speech_synthesizer.start_speaking_text_async()

    speech_synthesizer.speak_text_async(text).get()
    # syntesis_done.wait()
    # syntesize_audio('здравейте')
    final_audio = b"".join(full_audio)
    # print(final_audio)

    # mulaw_audio = final_audio
    # audio = audioop.lin2ulaw(mulaw_audio, 2)
    base64_audio = base64.b64encode(final_audio).decode("utf-8")
    return base64_audio


async def play_text_raw_audio(
    websocket: WebSocket, stream_sid: str, text: str, streaming: bool = False
):

    audio_string = await text_to_base64_audio(text)
    for i in range(0, len(audio_string), 216):
        # Get the chunk
        chunk = audio_string[i : i + 216]
        await websocket.send_json(
            {"event": "media", "streamSid": stream_sid, "media": {"payload": chunk}}
        )
        if not streaming:
            # LAST CHUNK
            if i + len(chunk) >= len(audio_string):
                await websocket.send_json(
                    {
                        "event": "mark",
                        "streamSid": stream_sid,
                        "mark": {"name": "my label"},
                    }
                )


from langchain_core.messages.ai import AIMessageChunk


async def get_tokens(input: str, agent, message_history):
    path_status = {}
    async for chunk in agent.astream_log(
        {"input": input, "chat_history": message_history.messages},
        config={"configurable": {"session_id": "asd"}},
        include_names=["ChatOpenAI"],
    ):
        for op in chunk.ops:
            if op["op"] == "add":
                if op["path"] not in path_status:
                    path_status[op["path"]] = op["value"]
                else:
                    if not isinstance(op["value"], dict):
                        path_status[op["path"]] += op["value"]
        if isinstance(path_status.get(op["path"]), AIMessageChunk):
            yield path_status.get(op["path"]).content
