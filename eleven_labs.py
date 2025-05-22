from elevenlabs import stream, voices, play, save
from elevenlabs.client import ElevenLabs
import time
import os
from keys import ELEVENLABS_API_KEY_1, ELEVENLABS_API_KEY_2, ELEVENLABS_API_KEY_3

# I HAVE 3 ELEVEN LABS API KEYS INSTEAD ONE OF THEM RUN OUT OF CHARACTERS (1 key = 10.000 characters)

try:
  # API KEY NB 1
  #client = ElevenLabs(api_key=ELEVENLABS_API_KEY_1)
  
  # API KEY NB 2 IN CASE THE 1ST ONE IS OUT OF CHARACTERS
  client = ElevenLabs(api_key=ELEVENLABS_API_KEY_2)
  
  # API KEY NB 3 IN CASE THE 1ST AND 2ND ONES ARE OUT OF CHARACTERS
  #client = ElevenLabs(api_key=ELEVENLABS_API_KEY_3)
except TypeError:
  exit("Ooops! You forgot to set ELEVENLABS_API_KEY in your environment!")

class ElevenLabsManager:

    def __init__(self):
        # CALLING voices() IS NECESSARY TO INSTANTIATE 11LABS FOR SOME FUCKING REASON
        all_voices = client.voices
        print(f"\nAll ElevenLabs voices: \n{all_voices.get_all()}\n")

    # Convert text to speech, then save it to file. Returns the file path
    def text_to_audio(self, input_text, voice="Doug VO Only", subdirectory=""):
        voices = client.voices.get_all().voices
        for voice_from_list in voices:
          if voice_from_list.name == voice:
             voice_id = voice_from_list.voice_id
             audio_saved = client.text_to_speech.convert(
               text=input_text,
               voice_id=voice_id,
               model_id="eleven_multilingual_v2",
               output_format="mp3_44100_128"
             )
             file_name = f"___Msg{str(hash(input_text))}.mp3"
             tts_file = os.path.join(os.path.abspath(os.curdir), subdirectory, file_name)
             save(audio_saved,tts_file)
             return tts_file

    # Convert text to speech, then play it out loud
    def text_to_audio_played(self, input_text, voice="Doug VO Only"):
        audio = client.generate(
          text=input_text,
          voice=voice,
          model="eleven_monolingual_v1"
        )
        play(audio)

    # Convert text to speech, then stream it out loud (don't need to wait for full speech to finish)
    def text_to_audio_streamed(self, input_text, voice="Doug VO Only"):
        audio_stream = client.generate(
          text=input_text,
          voice=voice,
          model="eleven_monolingual_v1",
          stream=True
        )
        stream(audio_stream)


#if __name__ == '__main__':
#    elevenlabs_manager = ElevenLabsManager()
#
#    elevenlabs_manager.text_to_audio_streamed("This is my streamed test audio, I'm so much cooler than played", "Doug Melina")
#    time.sleep(2)
#    elevenlabs_manager.text_to_audio_played("This is my played test audio, helo hello", "Doug Melina")
#    time.sleep(2)
#    file_path = elevenlabs_manager.text_to_audio("This is my saved test audio, please make me beautiful", "Doug Melina")
#    print("Finished with all tests")
#
#    time.sleep(30)
