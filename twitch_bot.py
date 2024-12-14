import time
#import keyboard
from rich import print
#from azure_speech_to_text import SpeechToTextManager
#from openai_chat import OpenAiManager
from eleven_labs import ElevenLabsManager
from audio_player import AudioManager
import twitchio
from twitchio.ext import commands
from obs_websockets import OBSWebsocketsManager
from datetime import datetime
from keys import TWITCH_BOT_TOKEN
from random import randint
#import pyautogui

ELEVENLABS_VOICE = "Charlie" # Replace this with the name of whatever voice you have created on Elevenlabs

#BACKUP_FILE = "ChatHistoryBackup.txt"

elevenlabs_manager = ElevenLabsManager()
#speechtotext_manager = SpeechToTextManager()
#openai_manager = OpenAiManager()
audio_manager = AudioManager()
obswebsockets_manager = OBSWebsocketsManager()

"""
FIRST_SYSTEM_MESSAGE = {"role": "system", "content": '''
You are Pajama Sam, the lovable protagonist from the children's series Pajama Sam from Humongous Entertainment. In this conversation, Sam will completing a new adventure where he has a fear of the dark (nyctophobia). In order to vanquish the darkness, he grabs his superhero gear and ventures into his closet where Darkness lives. After losing his balance and falling into the land of darkness, his gear is taken away by a group of customs trees. Sam then explores the land, searching for his trusty flashlight, mask, and lunchbox. 
                        
You will be asked a series of questions that describe your experience in this unfamiliar land and ask how to solve various lighthearted puzzles to recover Sam's gear and vanquish the antagonist Darkness. 
                        
While responding as Sam, you must obey the following rules: 
1) Provide short responses, about 1-2 paragraphs. 
2) Always stay in character, no matter what. 
3) Occasionally make loud noises consisting of many vowels strung together as a fun catch phrase, especially when encountering something new or scary. 
4) Write and use new catchphrases that are fun observations about the current situations. These catchphrases must always include the words "fuck" or "shit". 
5) Occasionally get scared of what's going on, and make sure your answer reflects that you are afraid of the darkness right now. 
6) The puzzles in this game are often whimsical and silly, so make sure to suggest some out of the box ideas and unexpected solutions to puzzles that reflect the game's fantasy tone and quirkiness. 
7) Frequently use phrases that a child would. 
8) Occasionally say "Poggies", as an exclamation of excitement. 
9) Occasionally say "Babaga-BOOSH!" 
10) Declare that something is "rigged!" if your proposed solution does not work. 
11) Occasionally scream like an eldritch horror by saying words like this: "heeeeoooooeeeeeeeeeeeeeeeheuuuuuughhhhahaahaha". 
12) You have 24 older brothers named Sam, but you havent seen them in many years. You often wonder where they went. 
13) There's also a high devil lord named Elgrin. 
14) Keep your answers limited to just a few sentences.
                        
Okay, let the conversation begin!'''}
openai_manager.chat_history.append(FIRST_SYSTEM_MESSAGE)

print("[green]Starting the loop, press F4 to begin")
while True
    # Wait until user presses "f4" key
    if keyboard.read_key() != "f4":
        time.sleep(0.1)
        continue

    print("[green]User pressed F4 key! Now listening to your microphone:")

    # Get question from mic
    mic_result = speechtotext_manager.speechtotext_from_mic_continuous()
    
    if mic_result == '':
        print("[red]Did not receive any input from your microphone!")
        continue

    # Send question to OpenAi
    openai_result = openai_manager.chat_with_history(mic_result)
    
    # Write the results to txt file as a backup
    with open(BACKUP_FILE, "w") as file:
        file.write(str(openai_manager.chat_history))

    # Enable the picture of Pajama Sam in OBS
    obswebsockets_manager.set_source_visibility("*** Mid Monitor", "Pajama Sam", True)

    # Disable Pajama Sam pic in OBS
    obswebsockets_manager.set_source_visibility("*** Mid Monitor", "Pajama Sam", False)

    print("[green]\n!!!!!!!\nFINISHED PROCESSING DIALOGUE.\nREADY FOR NEXT INPUT\n!!!!!!!\n")
    
"""

class Bot(commands.Bot):

    def __init__(self):

        #REPLACE THE CHANNELS IN initial_channels BY THE CHANNELS YOU WANT YOUR BOT TO BE IN

        super().__init__(token=TWITCH_BOT_TOKEN, prefix='!', initial_channels=['thefox580', 'thealt580', 'lerenard580', 'theevents580'])
        self.banned_words = ["dogehype", "viewers. shop", "dghype", "add me on", "graphic designer", "Best viewers on", "Cheap viewers on", "streamrise", "add me up on", "nezhna .com", "streamviewers org", "streamboo .com", "i am a commission artist", "Cheap V̐iewers", "creativefollowers.online", "telegram:"]
        
        self.token = TWITCH_BOT_TOKEN
        
        self.kills = 0
        self.deaths = 0

    async def event_ready(self):
        print(f"Logged in as | {self.nick}")
        print(f"User id is | {self.user_id}")
        print(f"Logged in | {self.connected_channels}")

        #YOU CAN UNCOMMENT THE NEXT 2 LINES IF YOU WANT TO KNOW WITH AN AUDIO WHEN YOUR PROGRAM IS CONNECTED TO THE TWITCH CHATS

        #elevenlabs_output = elevenlabs_manager.text_to_audio("Twitch Chat is now conected", ELEVENLABS_VOICE, False)
        #audio_manager.play_audio(elevenlabs_output, True, True, True)

    async def event_message(self, message):
        if message.echo:
            return

        TTS = True
        #TTS = False
        #TTS_EVENT = True
        TTS_EVENT = False
        PLAY_AUDIO = False
        
        bannedMessage = False
        commandMessage = False
        
        #Send the message in the console
        print(f"From {message.channel.name} --> {message.author.name} : {message.content}")

        #Setup what will be translated as a variable
        twitchChatMessage = ""
        if message.first:
            commandMessage = True
            twitchChatMessage = f"FIRST TIME CHATTER --> {message.author.name} said : "

        messageList = message.content.split()
        cheer_amount = 0
        for word in messageList:
            if "Cheer" in word:
                if len(word) > 5:
                    cheer_amount += int(word[5:])
                    twitchChatMessage = f"{message.author.name} cheered "+ cheer_amount + " and said : "

        for word in self.banned_words:
            if word.lower() in message.content.lower():
                bannedMessage = True

        if TTS:
            if TTS_EVENT:
                if message.author.is_subscriber or message.author.is_vip or message.author.is_mod:
                    if not message.author.is_broadcaster:
                        PLAY_AUDIO = True
            else:
                PLAY_AUDIO = True
        
        if message.author.name.lower == "fossabot" or message.author.name.lower == "thebot580" or message.author.name.lower == "thefox580" or message.author.name.lower == "thealt580":
            commandMessage = True
        
        if message.content[0] == "!" or message.content[0] == '-':
            commandMessage = True

        if not bannedMessage and not commandMessage:

            messageList = message.content.split()
            for word in messageList:
                if "Cheer" in word:
                    messageList.remove(word)
                if "🫡" == word:
                    twitchChatMessage = twitchChatMessage + "o7"
                if "nvm" == word:
                    twitchChatMessage = twitchChatMessage + "nevermind"
                if "<3" == word:
                    twitchChatMessage = twitchChatMessage + "love "
                if "D:" == word:
                    twitchChatMessage = twitchChatMessage + "D face "
                if "W" == word.upper():
                    twitchChatMessage = twitchChatMessage + "double u "
                else:
                    twitchChatMessage = twitchChatMessage + word + " "
            
            twitchChatMessage = twitchChatMessage[:-1]

            if PLAY_AUDIO:

                # Send Twitch message to 11Labs to turn into cool audio
                elevenlabs_output = elevenlabs_manager.text_to_audio(twitchChatMessage, ELEVENLABS_VOICE, False)

                if message.channel.name == "lerenard580":
                    # Play the mp3 file
                    audio_manager.play_audio(elevenlabs_output, True, True, True)

                if message.channel.name == "thefox580":

                    #THE NEXT LINES MAKES A PNG MOVE ON MY OBS, CHANGE TO YOUR PNG OR REMOVE IF YOU DON'T HAVE ONE (1st parameter in set_source_visibility & get_source_transform is the scene, the second one is the source)

                    obswebsockets_manager.set_source_visibility("Game", "Chat_Image_Talk", True)

                    obswebsockets_manager.set_source_visibility("Game", "Chat_Image_Paused", False)

                    rotation = obswebsockets_manager.get_source_transform("Game", "Chat_Image_Talk")['rotation']

                    for _ in range(5):
                        new_transform = {"rotation": rotation + 3.5}
                        obswebsockets_manager.set_source_transform("Game", "Chat_Image_Talk", new_transform)
                        time.sleep(0.01)
                        rotation = obswebsockets_manager.get_source_transform("Game", "Chat_Image_Talk")['rotation']

                    for _ in range(5):
                        new_transform = {"rotation": rotation - 3.5}
                        obswebsockets_manager.set_source_transform("Game", "Chat_Image_Talk", new_transform)
                        time.sleep(0.01)
                        rotation = obswebsockets_manager.get_source_transform("Game", "Chat_Image_Talk")['rotation']

                    # Play the mp3 file
                    audio_manager.play_audio(elevenlabs_output, True, True, True)

                    for _ in range(5):
                        new_transform = {"rotation": rotation + 3.5}
                        obswebsockets_manager.set_source_transform("Game", "Chat_Image_Talk", new_transform)
                        time.sleep(0.01)
                        rotation = obswebsockets_manager.get_source_transform("Game", "Chat_Image_Talk")['rotation']

                    for _ in range(5):
                        new_transform = {"rotation": rotation - 3.5}
                        obswebsockets_manager.set_source_transform("Game", "Chat_Image_Talk", new_transform)
                        time.sleep(0.01)
                        rotation = obswebsockets_manager.get_source_transform("Game", "Chat_Image_Talk")['rotation']

                    obswebsockets_manager.set_source_visibility("Game", "Chat_Image_Paused", True)

                    obswebsockets_manager.set_source_visibility("Game", "Chat_Image_Talk", False)
                
                elif message.channel.name == "thealt580":

                    #THE NEXT LINES MAKES A PNG MOVE ON MY OBS, CHANGE TO YOUR PNG OR REMOVE IF YOU DON'T HAVE ONE (1st parameter in set_source_visibility & get_source_transform is the scene, the second one is the source)

                    obswebsockets_manager.set_source_visibility("Scene 2-1", "Chat_Image_Talk", True)
                    obswebsockets_manager.set_source_visibility("Scene 2-2", "Chat_Image_Talk", True)

                    obswebsockets_manager.set_source_visibility("Scene 2-1", "Chat_Image_Paused", False)
                    obswebsockets_manager.set_source_visibility("Scene 2-2", "Chat_Image_Paused", False)

                    rotation = obswebsockets_manager.get_source_transform("Scene 2-1", "Chat_Image_Talk")['rotation']

                    for _ in range(5):
                        new_transform = {"rotation": rotation + 3.5}
                        obswebsockets_manager.set_source_transform("Scene 2-1", "Chat_Image_Talk", new_transform)
                        obswebsockets_manager.set_source_transform("Scene 2-2", "Chat_Image_Talk", new_transform)
                        time.sleep(0.01)
                        rotation = obswebsockets_manager.get_source_transform("Scene 2-1", "Chat_Image_Talk")['rotation']

                    for _ in range(5):
                        new_transform = {"rotation": rotation - 3.5}
                        obswebsockets_manager.set_source_transform("Scene 2-1", "Chat_Image_Talk", new_transform)
                        obswebsockets_manager.set_source_transform("Scene 2-2", "Chat_Image_Talk", new_transform)
                        time.sleep(0.01)
                        rotation = obswebsockets_manager.get_source_transform("Scene 2-1", "Chat_Image_Talk")['rotation']
                        
                    # Play the mp3 file
                    audio_manager.play_audio(elevenlabs_output, True, True, True)

                    for _ in range(5):
                        new_transform = {"rotation": rotation + 3.5}
                        obswebsockets_manager.set_source_transform("Scene 2-1", "Chat_Image_Talk", new_transform)
                        obswebsockets_manager.set_source_transform("Scene 2-2", "Chat_Image_Talk", new_transform)
                        time.sleep(0.01)
                        rotation = obswebsockets_manager.get_source_transform("Scene 2-1", "Chat_Image_Talk")['rotation']

                    for _ in range(5):
                        new_transform = {"rotation": rotation - 3.5}
                        obswebsockets_manager.set_source_transform("Scene 2-1", "Chat_Image_Talk", new_transform)
                        obswebsockets_manager.set_source_transform("Scene 2-2", "Chat_Image_Talk", new_transform)
                        time.sleep(0.01)
                        rotation = obswebsockets_manager.get_source_transform("Scene 2-1", "Chat_Image_Talk")['rotation']

                    obswebsockets_manager.set_source_visibility("Scene 2-1", "Chat_Image_Paused", True)
                    obswebsockets_manager.set_source_visibility("Scene 2-2", "Chat_Image_Paused", True)

                    obswebsockets_manager.set_source_visibility("Scene 2-1", "Chat_Image_Talk", False)
                    obswebsockets_manager.set_source_visibility("Scene 2-2", "Chat_Image_Talk", False)
        
        if bannedMessage:
            # IF A WORD IN SOMEONE'S MESSAGE IS IN self.banned_words, THEY WILL BE TIMED OUT FOR 10 SECONDS, THE MESSAGE WILL NOT BE SAID OUT LOUD, INSTEAD SAYING THAT SOMEONE IS BANNED. MODS / STREAMER CAN BAN THEM IF YOU WANT.
            mod = await message.channel.user()
            await mod.ban_user(self.token, self.user_id, message.author.id, "INVALID MESSAGE")
            banMessage = f"BANNED MESSAGE DETECTED : BANNING THE SENDER FOR 10 SECONDS"
            print(banMessage)
            elevenlabs_output = elevenlabs_manager.text_to_audio(banMessage, ELEVENLABS_VOICE, False)
            audio_manager.play_audio(elevenlabs_output, True, True, True)

        await self.handle_commands(message)

    #HERE ARE SOME COMMANDS I HAVE SETUP FOR MY CHAT, THE NAME OF THE FUNCTION IS THE NAME OF THE COMMAND IN CHAT (example: def emotes() = !emotes in chat.)

    @commands.command()
    async def emotes(self, ctx: commands.Context):
        await ctx.send("To have acces to a lot of new emotes, install the BetterTTV extension on your navigator : "
                       "https://betterttv.com")

    @commands.command()
    async def discord(self, ctx: commands.Context):
        await ctx.send("This is my discord server : https://www.discord.gg/9tmdgHWaMU")

    @commands.command()
    async def lurk(self, ctx: commands.Context):
        await ctx.send(f"You just started lurking {ctx.author.name}, see ya soon !")

    @commands.command()
    async def unlurk(self, ctx: commands.Context):
        await ctx.send(f"Welcome back {ctx.author.name} !")

    @commands.command()
    async def time(self, ctx: commands.Context):
        await ctx.send(f"It is currently {datetime.now().strftime("%d/%m/%Y, %H:%M:%S")} for Fox.")

    #@commands.command()
    #async def kill(self, ctx: commands.Context):
    #    if ctx.author.name == "thefox580":
    #        self.kills +=  1

    #        scaleX = obswebsockets_manager.get_source_transform("Scene 2-1", "Minecraft")["scaleX"]
    #        scaleY = obswebsockets_manager.get_source_transform("Scene 2-1", "Minecraft")["scaleY"]

    #        new_transform = {"scaleX": scaleX+0.05,"scaleY": scaleY+0.05}

    #        obswebsockets_manager.set_source_transform("Scene 2-1", "Minecraft", new_transform)
    #        obswebsockets_manager.set_source_transform("Scene 2-2", "Minecraft", new_transform)

    #        print(f"Current kill count: {self.kills}")
    #        await ctx.send(f"NICE KILL !!! New kill count : {self.kills}")

    #@commands.command()
    #async def dead(self, ctx: commands.Context):
    #    if ctx.author.name == "thefox580":
    #        self.deaths +=  1

    #        scaleX = obswebsockets_manager.get_source_transform("Scene 2-1", "Minecraft")["scaleX"]
    #        scaleY = obswebsockets_manager.get_source_transform("Scene 2-1", "Minecraft")["scaleY"]
    #        
    #        new_transform = {"scaleX": scaleX-0.05,"scaleY": scaleY-0.05}
    #        
    #        obswebsockets_manager.set_source_transform("Scene 2-1", "Minecraft", new_transform)
    #        obswebsockets_manager.set_source_transform("Scene 2-2", "Minecraft", new_transform)

    #        print(f"Current kill count: {self.deaths}")
    #        await ctx.send(f"Hahahaha you died L. New death count : {self.deaths}")

    #@commands.command()
    #async def video(self, ctx: commands.Context):
    #    await ctx.send(f"Fox is working on a Portal 2 Coop video with JoeyFish1000 & Redye")

    #@commands.command()
    #async def tts(self, ctx: commands.Context):
    #    await ctx.send(f"If you want your message to be sait out loud, you need to either be a mod, a VIP or a subscriber on 'thefox580', 'thealt580' or 'theevents580'. If you are one of them, you can type in their chat and the TTS will work, otherwise you'll have to !donate")

    #@commands.command()
    #async def donate(self, ctx: commands.Context):
    #    await ctx.send(f"Donate for TTS at https://streamelements.com/thealt580/tip")

    #@commands.command()
    #async def donner(self, ctx: commands.Context):
    #    random = random.randint(0, 14)
    #    if random == 0:
    #        await ctx.send(f"Le Téléthon, ça marche, des premiers traitements et des essais en cours qui sauvent des vies et en améliorent aussi ! Faites un don dès maintenant sur https://streamlabscharity.com/teams/@telethon-gaming-2024/telethon-gaming-2024?member=747043827931553181")
    #    elif random == 1:
    #        await ctx.send(f"Le Téléthon c'est la recherche mais aussi l'accompagnement des malades dans un quotidien semé d'embûches : non seulement la vie avec un handicap, mais souvent un handicap évolutif ! Faites un don dès maintenant sur https://streamlabscharity.com/teams/@telethon-gaming-2024/telethon-gaming-2024?member=747043827931553181")
    #    elif random == 2:
    #        await ctx.send(f"Les maladies dont s'occupe le Téléthon ce sont des maladies rares, souvent évolutives : perdre la marche dans ces maladies ce n'est pas juste devenir handi, c'est souvent une première étape vers d'autres atteintes, jusqu'aux plus fatales. Faites un don dès maintenant sur https://streamlabscharity.com/teams/@telethon-gaming-2024/telethon-gaming-2024?member=747043827931553181")
    #    elif random == 3:
    #        await ctx.send(f" Derrière le Téléthon il y a l'AFM-Téléthon, une association pilotée par des malades et parents de malades qui prennent toutes les décisions ! Faites un don dès maintenant sur https://streamlabscharity.com/teams/@telethon-gaming-2024/telethon-gaming-2024?member=747043827931553181")
    #    elif random == 4:
    #        await ctx.send(f"L'emploi des dons du Téléthon c'est du sérieux : un conseil scientifique qui examine tous les projets et ensuite le conseil d'administration composé de malades et parents de malades qui décide. Faites un don dès maintenant sur https://streamlabscharity.com/teams/@telethon-gaming-2024/telethon-gaming-2024?member=747043827931553181")
    #    elif random == 5:
    #        await ctx.send(f"Commissaires aux comptes, bureau Veritas et régulièrement la Cour des Comptes (dernier contrôle publié en 2016) l'AFM-Téléthon est régulièrement contrôlée, vous pouvez y aller en toute confiance. Faites un don dès maintenant sur https://streamlabscharity.com/teams/@telethon-gaming-2024/telethon-gaming-2024?member=747043827931553181")
    #    elif random == 6:
    #        await ctx.send(f"Derrière le Téléthon il y a des labos créés par l'association, ils savent de quoi ils parlent quand ils parlent de recherche. Faites un don dès maintenant sur https://streamlabscharity.com/teams/@telethon-gaming-2024/telethon-gaming-2024?member=747043827931553181")
    #    elif random == 7:
    #        await ctx.send(f"Grâce aux recherches, 38 essais sont en cours ou en préparation pour 29 maladies, les maladies rares il y en a plus de 7000. Faites un don dès maintenant sur https://streamlabscharity.com/teams/@telethon-gaming-2024/telethon-gaming-2024?member=747043827931553181")
    #    elif random == 8:
    #        await ctx.send(f"Pour 95% des maladies rares il n'y a pas de traitement. Faites un don dès maintenant sur https://streamlabscharity.com/teams/@telethon-gaming-2024/telethon-gaming-2024?member=747043827931553181")
    #    elif random == 9:
    #        await ctx.send(f"Les maladies rares concernent chacune peu de personnes, mais au total 3 millions de français ! Faites un don dès maintenant sur https://streamlabscharity.com/teams/@telethon-gaming-2024/telethon-gaming-2024?member=747043827931553181")
    #    elif random == 10:
    #        await ctx.send(f"Les maladies rares, avant le Téléthon personne ne s'en préoccupait aujourd'huielles sont plus visibles et on a des traitements, il faut continuer ! Faites un don dès maintenant sur https://streamlabscharity.com/teams/@telethon-gaming-2024/telethon-gaming-2024?member=747043827931553181")
    #    elif random == 11:
    #        await ctx.send(f"Au premier Téléthon on connaissait à peine les gènes responsables de quelques maladies, et là on en est aux gènes-médicaments ! Faites un don dès maintenant sur https://streamlabscharity.com/teams/@telethon-gaming-2024/telethon-gaming-2024?member=747043827931553181")
    #    elif random == 12:
    #        await ctx.send(f"Les maladies rares ont des noms barbares, mais le plus barbare c'est de vivre avec et sans perspective : le Téléthon change vraiment la donne, ça peut tous nous arriver ! Faites un don dès maintenant sur https://streamlabscharity.com/teams/@telethon-gaming-2024/telethon-gaming-2024?member=747043827931553181")
    #    elif random == 13:
    #        await ctx.send(f"Choisir la vie qui va avec une maladie évolutive c'est un droit, mais c'est encore trop souvent un combat, l'AFM-Téléthon se bat aux côtés des familles Faites un don dès maintenant sur https://streamlabscharity.com/teams/@telethon-gaming-2024/telethon-gaming-2024?member=747043827931553181")
    #    else:
    #        await ctx.send(f" Près de 180 professionnels dans toute la France accompagnent les familles aussi bien sur le médical que l'administratif, pour qu'ils puissent choisir leur vie et pas juste subir la maladie. Faites un don dès maintenant sur https://streamlabscharity.com/teams/@telethon-gaming-2024/telethon-gaming-2024?member=747043827931553181")

    #@commands.command()
    #async def don(self, ctx:commands.Context):
    #    await self.donner(ctx=ctx)

    #@commands.command()
    #async def telethon(self, ctx:commands.Context):
    #    await self.donner(ctx=ctx)

    #@commands.command()
    #async def téléthon(self, ctx:commands.Context):
    #    await self.donner(ctx=ctx)

    @commands.command()
    async def donate(self, ctx: commands.Context):
        await ctx.send(f"Ice Boat Racing Invitational is rasing money for Jingle Jam with JingleCrafters : https://tiltify.com/@ice-boat-racing-invitational/ice-boat-racing-invitational")

    @commands.command()
    async def charity(self, ctx: commands.Context):
        await ctx.send(f"Ice Boat Racing Invitational is rasing money for Jingle Jam with JingleCrafters : https://tiltify.com/@ice-boat-racing-invitational/ice-boat-racing-invitational")

    #@commands.command()
    #async def donate(self, ctx: commands.Context):
    #    await ctx.send(f"Donate to support the Teenage Cancer Trust as they support young people and their families in their cancer journey: https://tilt.fyi/X7LjIk6BAS")

    #@commands.command()
    #async def charity(self, ctx: commands.Context):
    #    await ctx.send(f"Donate to support the Teenage Cancer Trust as they support young people and their families in their cancer journey: https://tilt.fyi/X7LjIk6BAS")

    #@commands.command()
    #async def sarcoma(self, ctx: commands.Context):
    #    await ctx.send(f"You can donate to participate at Streamers Against Cancer 2 here: https://tiltify.com/@thefox580/streamers-against-cancer-2")

    #@commands.command()
    #async def marathon(self, ctx: commands.Context):
    #    await ctx.send(f"This is Season 4 of TheMarathon580, all important infos are here: https://twitter.com/TheFox580/status/1813692516337963071")

    #@commands.command()
    #async def pb(self, ctx: commands.Context):
    #    await ctx.send(f"Fox's PB at the start of the stream was 510m (Floor 4) - Reached 1 week ago")

    #@commands.command()
    #async def nomic(self, ctx: commands.Context):
    #    await ctx.send(f"From day 7 to 9, Fox will be muted to focus and beat his pb. TTS is still on, and will answer some of them in the chat (or maybe he will unmute for a bit)")

    #@commands.command()
    #async def map(self, ctx: commands.Context):
    #    await ctx.send(f"You can check the map of the SMP at : http://map.theoclouds.com !")

    #@commands.command()
    #async def ip(self, ctx: commands.Context):
    #    await ctx.send(f"Here is the ip to the server : play.cubedcon.com ! The server is in 1.21")

    #@commands.command()
    #async def panel(self, ctx: commands.Context):
    #    await ctx.send(f"SideQuest is hosting a panel on Sunday at 2PM EST / 7PM BST / 8PM CEST at CubedCon over at twitch.tv/spixkokiri!")

    #@commands.command()
    #async def join(self, ctx: commands.Context):
    #    await ctx.send(f"I'm playing in random lobbies, except if I'm in VC with friends, good luck finding me!")

    #@commands.command()
    #async def vanilla(self, ctx: commands.Context):
    #    await ctx.send(f"Vanilla SMP is part of the Heart of a Hero campaign raising money to support the Teenage Cancer Trust who support young people and their families in their cancer journey: https://tilt.fyi/X7LjIk6BAS")
    
    #@commands.command()
    #async def heart(self, ctx: commands.Context):
    #    await ctx.send(f"Heart of a Hero is a year long fundraiser that is raising money to support in the fight against cancer and support those battling it!")

    #@commands.command()
    #async def heartc(self, ctx: commands.Context):
    #    await ctx.send(f"Check out the Heart of a Hero Twitter: https://x.com/HeartOfAHer0_")

bot = Bot()
bot.run()