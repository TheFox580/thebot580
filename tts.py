import azure.cognitiveservices.speech as speechsdk
from keys import AZURE_TTS_KEY, AZURE_TTS_REGION
from gtts import gTTS
from pydub import AudioSegment
import os
import pygame

class TTSManager:

    def __init__(self, tts_voice:str):
        try:
            self.azure_speechconfig = speechsdk.SpeechConfig(subscription=AZURE_TTS_KEY, region=AZURE_TTS_REGION)
        except TypeError:
            exit("Ooops! You forgot to set AZURE_TTS_KEY or AZURE_TTS_REGION or AZURE_TTS_ENDPOINT in your environment!")
        self.azure_speechconfig.speech_synthesis_voice_name = tts_voice
        self.azure_synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.azure_speechconfig, audio_config=None)
        

    def text_to_speech(self, input:str):
        ssml_text = f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts' xmlns:emo='http://www.w3.org/2009/10/emotionml' xml:lang='en-US'><voice name='{self.azure_speechconfig.speech_synthesis_voice_name}'><mstts:express-as style='friendly'>{input}</mstts:express-as></voice></speak>"
        result = self.azure_synthesizer.speak_ssml_async(ssml_text).get()
        
        output = os.path.join(os.path.abspath(os.curdir), f"_Msg{str(hash(input))}-{str(hash(self.azure_speechconfig.speech_synthesis_voice_name))}-{str(hash("friendly"))}.wav")
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted: # type: ignore
            stream = speechsdk.AudioDataStream(result)
            stream.save_to_wav_file(output)
        else:
            print("\n   Azure failed, using gTTS instead   \n")
            output_mp3 = output.replace(".wav", ".mp3")
            msgAudio = gTTS(text=input, lang='en', slow=False)
            msgAudio.save(output_mp3)
            audiosegment = AudioSegment.from_mp3(output_mp3)
            audiosegment.export(output, format="wav")
        
        return output

if __name__ == "__main__":
    
    tts_manager = TTSManager("en-US-GuyNeural")
    pygame.mixer.init()

    file_path = tts_manager.text_to_speech("This is a test message!")
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()