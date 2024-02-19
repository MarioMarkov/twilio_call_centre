
from medium_tools import AzureSpeechSynthesizer


speech_synthesizer = AzureSpeechSynthesizer(language="bg-BG", speech_synthesis_voice_name = 'bg-BG-BorislavNeural')
speech_synthesizer.text_to_wav("аз съм бот", 'voice.raw')
