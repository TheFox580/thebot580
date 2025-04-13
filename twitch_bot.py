import time
#import keyboard
from rich import print
from eleven_labs import ElevenLabsManager
from audio_player import AudioManager
import twitchio
from twitchio.ext import commands
from obs_websockets import OBSWebsocketsManager
from datetime import datetime
from keys import TWITCH_BOT_TOKEN

ELEVENLABS_VOICE = "Charlie" # Replace this with the name of whatever voice you have created on Elevenlabs

elevenlabs_manager = ElevenLabsManager()
audio_manager = AudioManager()
obswebsockets_manager = OBSWebsocketsManager()

class Bot(commands.Bot):

    def __init__(self):

        #REPLACE THE CHANNELS IN initial_channels BY THE CHANNELS YOU WANT YOUR BOT TO BE IN

        super().__init__(token=TWITCH_BOT_TOKEN, prefix='!', initial_channels=['thefox580', 'thealt580', 'lerenard580', 'theevents580'])
        self.banned_words = ["dogehype", "viewers. shop", "dghype", "add me on", "graphic designer", "Best viewers on", "Cheap viewers on", "streamrise", "add me up on", "nezhna .com", "streamviewers org", "streamboo .com", "i am a commission artist", "Cheap V̐iewers", "creativefollowers.online", "telegram:", "adding me up on"]
        
        self.token = TWITCH_BOT_TOKEN

    async def event_ready(self):
        print(f"Logged in as | {self.nick}")
        print(f"User id is | {self.user_id}")
        print(f"Logged in | {self.connected_channels}")

    async def event_message(self, message):
        if message.echo:
            return

        TTS = True
        TTS_EVENT = False
        PLAY_AUDIO = False
        
        BANNEDMESSAGE = False
        COMMANDMESSAGE = False
        
        #Send the message in the console
        print(f"From {message.channel.name} --> {message.author.name} : {message.content}")

        #Setup what will be translated as a variable
        twitchChatMessage = ""
        if message.first:
            COMMANDMESSAGE = True
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
                BANNEDMESSAGE = True

        if TTS:
            if TTS_EVENT:
                if message.author.is_subscriber or message.author.is_vip or message.author.is_mod:
                    if not message.author.is_broadcaster:
                        PLAY_AUDIO = True
            else:
                PLAY_AUDIO = True
        
        if message.author.name.lower() == "fossabot" or message.author.name.lower() == "streamelements" or message.author.name.lower() == "thebot580" or message.author.name.lower() == "thefox580" or message.author.name.lower() == "thealt580" or message.author.name.lower() == "nightbot":
            COMMANDMESSAGE = True
        
        if message.content[0] == "!" or message.content[0] == '-':
            COMMANDMESSAGE = True

        if not (BANNEDMESSAGE and COMMANDMESSAGE):

            messageList = message.content.split()
            for word in messageList:
                if "Cheer" in word:
                    messageList.remove(word)
                if ("🫡" == word) or ("o7" == word):
                    twitchChatMessage = twitchChatMessage + "oh 7 "
                if "nvm" == word:
                    twitchChatMessage = twitchChatMessage + "nevermind "
                if "<3" == word:
                    twitchChatMessage = twitchChatMessage + "love "
                if "D:" == word:
                    twitchChatMessage = twitchChatMessage + "D face "
                if "W" == word.upper():
                    twitchChatMessage = twitchChatMessage + "double you "
                if "thefox91" in word:
                    pass #If the word is my emote, don't say it!
                else:
                    twitchChatMessage = twitchChatMessage + word + " "
            
            twitchChatMessage = twitchChatMessage[:-1]

            if twitchChatMessage.split() == []:
                PLAY_AUDIO = False

            if (PLAY_AUDIO and not (COMMANDMESSAGE or BANNEDMESSAGE)):

                # Send Twitch message to 11Labs to turn into cool audio
                elevenlabs_output = elevenlabs_manager.text_to_audio(twitchChatMessage, ELEVENLABS_VOICE, False)

                if message.channel.name == "lerenard580":
                    # Play the mp3 file
                    audio_manager.play_audio(elevenlabs_output, True, True, True)

                if message.channel.name == "thefox580":

                    posY = obswebsockets_manager.get_source_transform("Bots", "TwitchChat")['positionY']
                    while posY > 693:
                        posY -= 1
                        new_transform = {"positionY": posY}
                        obswebsockets_manager.set_source_transform("Bots", "TwitchChat", new_transform)

                    # Play the mp3 file
                    audio_manager.play_audio(elevenlabs_output, True, True, True)

                    posY = obswebsockets_manager.get_source_transform("Bots", "TwitchChat")['positionY']
                    while posY < 1080:
                        posY += 1
                        new_transform = {"positionY": posY}
                        obswebsockets_manager.set_source_transform("Bots", "TwitchChat", new_transform)

                elif message.channel.name == "thealt580":

                    #THE NEXT LINES MAKES A PNG CHANGE ON MY OBS, CHANGE TO YOUR PNG OR REMOVE IF YOU DON'T HAVE ONE (1st parameter in set_source_visibility)
                    #I replaced the png moving with the "Audio Move" filter on the "Move" OBS Plugin
                    
                    obswebsockets_manager.set_source_visibility("Bots", "Chat_Image_Talk", True)

                    obswebsockets_manager.set_source_visibility("Bots", "Chat_Image_Paused", False)
                    
                    # Play the mp3 file
                    audio_manager.play_audio(elevenlabs_output, True, True, True)
                    
                    obswebsockets_manager.set_source_visibility("Bots", "Chat_Image_Paused", True)

                    obswebsockets_manager.set_source_visibility("Bots", "Chat_Image_Talk", False)
                    
        if BANNEDMESSAGE:
            # IF A WORD IN SOMEONE'S MESSAGE IS IN self.banned_words, THEY WILL BE BANNED FOREVER, THE MESSAGE WILL NOT BE SAID OUT LOUD, INSTEAD SAYING THAT SOMEONE IS BANNED. MODS / STREAMER CAN UNBAN THEM IF YOU WANT.
            mod = await message.channel.user()
            await mod.ban_user(self.token, self.user_id, message.author.id, "INVALID MESSAGE")
            banMessage = f"BANNED MESSAGE DETECTED : BANNING THE SENDER FOREVER"
            print(banMessage)
            elevenlabs_output = elevenlabs_manager.text_to_audio(banMessage, ELEVENLABS_VOICE, False)
            audio_manager.play_audio(elevenlabs_output, True, True, True)

        await self.handle_commands(message)

    #HERE ARE SOME COMMANDS I HAVE SETUP FOR MY CHAT, THE NAME OF THE FUNCTION IS THE NAME OF THE COMMAND IN CHAT (example: def emotes() = !emotes in chat.)

    @commands.command()
    async def emotes(self, ctx: commands.Context):
        await ctx.send("To have acces to a lot of new emotes, install the BetterTTV (https://betterttv.com) or 7TV (https://7tv.app/) extension on your navigator ")

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

    @commands.command()
    async def rs(self, ctx: commands.Context):
        await ctx.send(f"Random Sunday is a weekly stream where I go live playing random games, literally....")

    #@commands.command()
    #async def ad(self, ctx: commands.Context):
    #    await ctx.send(f"This stream is sponsored by HoYoverse! You can download Honkai : Star Rail over at https://strms.net/honkai_thefox580. You can also use the code 'DBKMW7MA6XB3' for 50 Stellar Jade!")

    #@commands.command()
    #async def team(self, ctx: commands.Context):
    #    await ctx.send(f"Fox's team is JohnDubuc, Kelawesome & Clovish!")

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

    #@commands.command()
    #async def donate(self, ctx: commands.Context):
    #    await ctx.send(f"Donate to support the Teenage Cancer Trust as they support young people and their families in their cancer journey: https://tilt.fyi/X7LjIk6BAS")

    #@commands.command()
    #async def charity(self, ctx: commands.Context):
    #    await ctx.send(f"Donate to support the Teenage Cancer Trust as they support young people and their families in their cancer journey: https://tilt.fyi/X7LjIk6BAS")

    #@commands.command()
    #async def vanilla(self, ctx: commands.Context):
    #    await ctx.send(f"Vanilla SMP is part of the Heart of a Hero campaign raising money to support the Teenage Cancer Trust who support young people and their families in their cancer journey: https://tilt.fyi/X7LjIk6BAS")
    
    #@commands.command()
    #async def heart(self, ctx: commands.Context):
    #    await ctx.send(f"Heart of a Hero is a year long fundraiser that is raising money to support in the fight against cancer and support those battling it!")

bot = Bot()
bot.run()