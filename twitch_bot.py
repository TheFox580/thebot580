import asyncio
import logging
import sqlite3

import asqlite
import twitchio
from twitchio.ext import commands
from twitchio import eventsub

import json
import math
from audio_player import AudioManager
from obs_websockets import OBSWebsocketsManager
from datetime import datetime, timezone
from keys import TWITCH_BOT_CLIENT_ID, TWITCH_BOT_CLIENT_SECRET, OWNER_ID, BOT_ID, AZURE_TTS_VOICE
import requests
from tts import TTSManager

tts_manager = TTSManager(AZURE_TTS_VOICE)
audio_manager = AudioManager()
obswebsockets_manager = OBSWebsocketsManager()

LOGGER: logging.Logger = logging.getLogger("TheBot580")

class Bot(commands.Bot):
    def __init__(self, *, token_database: asqlite.Pool) -> None:
        self.token_database = token_database

        super().__init__(
            client_id=TWITCH_BOT_CLIENT_ID,
            client_secret=TWITCH_BOT_CLIENT_SECRET,
            bot_id=BOT_ID,
            owner_id=OWNER_ID,
            prefix="!",
        )

    async def setup_hook(self) -> None:
        # Add our component which contains our commands...
        await self.add_component(MyComponent(self))

        subscriptions = []

        # Subscribe to read chat (event_message) from our channel as the bot...
        # This creates and opens a websocket to Twitch EventSub...
        subscriptions.append(eventsub.ChatMessageSubscription(broadcaster_user_id=OWNER_ID, user_id=BOT_ID))

        # Subscribe and listen to when someone follows..
        subscriptions.append(eventsub.ChannelFollowSubscription(broadcaster_user_id=OWNER_ID, moderator_user_id=BOT_ID))

        # Subscribe and listen to when someone (re)sub(-gift)..
        subscriptions.append(eventsub.ChannelSubscribeSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.ChannelSubscribeMessageSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.ChannelSubscriptionGiftSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when someone cheers..
        subscriptions.append(eventsub.ChannelCheerSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when prediction starts, locks or ends..
        subscriptions.append(eventsub.ChannelPredictionBeginSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.ChannelPredictionLockSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.ChannelPredictionEndSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when poll starts or ends..
        subscriptions.append(eventsub.ChannelPollBeginSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.ChannelPollEndSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when a shoutout is sent in chat..
        subscriptions.append(eventsub.ShoutoutCreateSubscription(broadcaster_user_id=OWNER_ID, moderator_user_id=BOT_ID))
        
        # Subscribe and listen to when a stream goes on/offline..
        subscriptions.append(eventsub.StreamOnlineSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.StreamOfflineSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when hype train starts, updates or ends..
        subscriptions.append(eventsub.HypeTrainBeginSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.HypeTrainProgressSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.HypeTrainEndSubscription(broadcaster_user_id=OWNER_ID))

        """
        # CKC
        # Subscribe and listen to when shared chat starts, updates or ends..
        subscriptions.append(eventsub.SharedChatSessionBeginSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.SharedChatSessionUpdateSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.SharedChatSessionEndSubscription(broadcaster_user_id=OWNER_ID))"""

        # Subscribe and listen to when goal starts, updates or ends..
        subscriptions.append(eventsub.GoalBeginSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.GoalProgressSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.GoalEndSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when someone raids..
        subscriptions.append(eventsub.ChannelRaidSubscription(to_broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when the title or the game changes..
        subscriptions.append(eventsub.ChannelUpdateSubscription(broadcaster_user_id=OWNER_ID))

        for subscription in subscriptions:
            print(f"Subscribing to {subscription}")
            await self.subscribe_websocket(payload=subscription)
            #time.sleep(2) #I'm waiting 2 seconds inbetween each subsriptions because it looks like if you subscribe to events too fast they don't get registered?

    async def add_token(self, token: str, refresh: str) -> twitchio.authentication.ValidateTokenPayload:
        # Make sure to call super() as it will add the tokens interally and return us some data...
        resp: twitchio.authentication.ValidateTokenPayload = await super().add_token(token, refresh)

        # Store our tokens in a simple SQLite Database when they are authorized...
        query = """
        INSERT INTO tokens (user_id, token, refresh)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            token = excluded.token,
            refresh = excluded.refresh;
        """

        async with self.token_database.acquire() as connection:
            await connection.execute(query, (resp.user_id, token, refresh))

        LOGGER.info("Added token to the database for user: %s", resp.user_id)
        return resp

    async def load_tokens(self, path: str | None = None) -> None:
        # We don't need to call this manually, it is called in .login() from .start() internally...

        async with self.token_database.acquire() as connection:
            rows: list[sqlite3.Row] = await connection.fetchall("""SELECT * from tokens""")

        for row in rows:
            await self.add_token(row["token"], row["refresh"])

    async def setup_database(self) -> None:
        # Create our token table, if it doesn't exist..
        query = """CREATE TABLE IF NOT EXISTS tokens(user_id TEXT PRIMARY KEY, token TEXT NOT NULL, refresh TEXT NOT NULL)"""
        async with self.token_database.acquire() as connection:
            await connection.execute(query)

    async def event_ready(self) -> None:
        LOGGER.info("Successfully logged in as: %s", self.bot_id)

class MyComponent(commands.Component):
    def __init__(self, bot: Bot):
        # Passing args is not required...
        # We pass bot here as an example...
        self.banned_words = ["dogehype", "viewers. shop", "dghype", "add me on", "graphic designer", "Best viewers on", "Cheap viewers on", "streamrise", "add me up on", "nezhna .com", "streamviewers org", "streamboo .com", "i am a commission artist", "Cheap V̐iewers", "creativefollowers.online", "telegram:", "adding me up on", "Best view͙e̤rs", "smmtop11.online"]
        self.bot = bot

        twitchEmotes = self.getTwitchEmotes(OWNER_ID)

        self.emotes_dict : dict[str, list[str]] = { #Replace with your own BTTV, 7TV, FFZ and/or Twitch Emotes | Format : {"Platform":(["emote", "emote", "emote", ...], "prefix")}
            "7TV": #7TV Emotes
                self.get7TVEmotes(OWNER_ID),
            "BTTV": #BTTV Emotes
                self.getBTTVEmotes(OWNER_ID),
            "FFZ": #FFZ Emotes
                self.getFFZEmotes(OWNER_ID),
            "TwitchChannel": #Your Twitch Channel Emotes
                twitchEmotes[0],
            "Others": #Any other emotes that I don't know / Couldn't be bother to list (i.e. : Twitch Global Emotes or someone's Twitch Channel's Emotes)
                twitchEmotes[1]
            }
        self.emotes_combo : list = ["", 0] #Holds a list like : [str("Emote Name"), int(number of instance of this emote in a row)]
        
        self.shared_chat_users : list = []
        self.hype_train_level : int = -1
        self.hype_train_level_complete : float = 0
        self.start_time : datetime = datetime.now()
        self.lurkers = []
        self.tts = True

    def getBTTVEmotes(self, broadcaster_id:str) -> list[str]:
        emotes : list[str] = []
        req = requests.get(f'https://api.betterttv.net/3/cached/users/twitch/{broadcaster_id}')
        if req.ok:
            res = req.json()
            for emote in res["sharedEmotes"]:
                emotes.append(emote["code"])
            return emotes
        return []
    
    def get7TVEmotes(self, broadcaster_id:str) -> list[str]:
        emotes : list[str] = []

        req = requests.get(f'https://api.7tv.app/v3/users/twitch/{broadcaster_id}')
        if req.ok:
            res = req.json()
            emote_set = res["emote_set_id"]

            req = requests.get(f'https://api.7tv.app/v3/emote-sets/{emote_set}')
            res = req.json()
            for emote in res["emotes"]:
                emotes.append(emote["name"])
            return emotes
        return []
    
    def getFFZEmotes(self, broadcaster_id:str) -> list[str]:
        emotes : list[str] = []

        req = requests.get(f'https://api.frankerfacez.com/v1/room/id/{broadcaster_id}')

        if req.ok :
            res = req.json()
            emoteSet  = res["room"]["set"]
            currentSet = res["sets"][str(emoteSet)]
            for emote in currentSet["emoticons"]:
                emotes.append(emote["name"])
            return emotes
        return []
    
    def getTwitchEmotes(self, broadcaster_id:str) -> tuple[list[str], list[str]]:
        emotes : tuple[list[str], list[str]] = ([], [])

        params = {"client_id": TWITCH_BOT_CLIENT_ID, "client_secret": TWITCH_BOT_CLIENT_SECRET, "grant_type":"client_credentials"}

        req = requests.post("https://id.twitch.tv/oauth2/token", params=params)

        if not req.ok:
            return ([], [])
        
        res = req.json()
        access_token = res["access_token"]

        headers = {"Authorization": f"Bearer {access_token}", "Client-Id": TWITCH_BOT_CLIENT_ID}

        req = requests.get(f'https://api.twitch.tv/helix/chat/emotes?broadcaster_id={broadcaster_id}', headers=headers)

        if not req.ok :
            return ([], [])
        
        res = req.json()
        emote1 = []
        for emote in res["data"]:
            emote1.append(emote["name"])

        req = requests.get(f'https://api.twitch.tv/helix/chat/emotes/global', headers=headers)

        if not req.ok :
            return ([], [])
        
        res = req.json()
        emote2 = []
        for emote in res["data"]:
            emote2.append(emote["name"])

        emotes : tuple[list[str], list[str]] = (emote1, emote2)

        return emotes


    def treat_message(self, message:str) -> str:

        final_message = ""
        messageList = message.split()
        for word in messageList:
            word = word.replace("_", " ")
            if "Cheer" in word: #We don't want it to say the bits amount!
                pass
            elif ("🫡" == word) or ("o7" == word):
                final_message += "oh 7 "
            elif "D:" == word:
                final_message += "D face "
            elif "D:" == word:
                final_message += "D face "
            elif ("</3" == word) or ("<3" == word):
                final_message += "love "
            elif "https" in word:
                pass
            elif self.message_has_an_emote(word, self.emotes_dict):
                pass
            else:
                final_message += word + " "
        
        return final_message[:-1]

    def format_tier(self, tier:str, is_gift:bool=False) -> str:
        if not is_gift:
            if tier == "1000":
                return "1 ou avec Prime"
        return tier[0]
    
    def message_has_an_emote(self, message:str, emote_dict:dict[str, list[str]]) -> bool:
        messageList = message.split()
        for word in messageList:
            for key in emote_dict.keys():
                emotes_looked_at = emote_dict[key]
                if word in emotes_looked_at:
                    return True
        return False
    
    def message_has_emote(self, message:str, emote:str, emote_dict:dict[str, list[str]]) -> bool:
        if self.message_has_an_emote(message, emote_dict):
            messageList = message.split()
            return emote in messageList
        return False
    
    def get_first_emote_in_message(self, message:str, emote_dict:dict[str, list[str]]) -> str:
        if self.message_has_an_emote(message, emote_dict):
            messageList = message.split()
            for word in messageList:
                for key in emote_dict.keys():
                    emotes_looked_at = emote_dict[key]
                    if word in emotes_looked_at:
                        return word
        raise ValueError
    
    def format_time_since(self, biggest:datetime, smallest:datetime, leap_year_warning:bool=False) -> str:
        time_diff = biggest-smallest

        secs = int(time_diff.total_seconds())
        mins = int(secs // 60)
        secs -= mins*60
        hours = int(mins // 60)
        mins -= hours*60
        days = int(hours // 24)
        hours -= days*24
        years = int(days // 365.2422)
        months_but_it_s_based_from_the_years_because_i_dont_want_to_do_annoying_calculations = (days / 365.2422) - years
        months = int(months_but_it_s_based_from_the_years_because_i_dont_want_to_do_annoying_calculations*12)
        days -= int(years*365.2242+months*30.436875)

        seconds_text = "seconde"
        minutes_text = "minute"
        if secs != 1:
            seconds_text += "s"
        if mins != 1:
            minutes_text += "s"

        time_text = f"{mins} {minutes_text} et {secs} {seconds_text}" #I'm always including the minutes just so that I don't have to handle the "and". Big Brain

        if leap_year_warning:
            time_text += " (Il peut y avoir un décalage a cause des années bisextilles)"

        if hours > 0:
            if hours == 1:
                time_text = f"{hours} heure, {time_text}"
            else:
                time_text = f"{hours} heures, {time_text}"
        if days > 0:
            if days == 1:
                time_text = f"{days} jour, {time_text}"
            else:
                time_text = f"{days} jours, {time_text}"
        if months > 0:
            time_text = f"{months} mois, {time_text}"
        if years > 0:
            if years == 1:
                time_text = f"{years} année, {time_text}"
            else:
                time_text = f"{years} années, {time_text}"
        
        return time_text

    # We use a listener in our Component to display the messages received.
    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:

        tts_event = False
        play_audio = False
        
        banned_message = False
        command_message = False

        print(f"[{payload.broadcaster.display_name}] - {payload.chatter.display_name}: {payload.text}")

        #Setup what will be translated as a variable
        twitchChatMessage = payload.text
        if payload.type == "user_intro":
            command_message = True
            twitchChatMessage = f"FIRST TIME CHATTER --> {payload.chatter.name} à dit : "

        blocked_terms : list[str] = []
        async for blocked_term in payload.broadcaster.fetch_blocked_terms(moderator=BOT_ID):
            term : twitchio.BlockedTerm = blocked_term
            blocked_terms.append(term.text.lower())
            

        for word in self.banned_words:
            if word.lower() in payload.text.lower():
                banned_message = True
                if word.lower() not in blocked_terms:
                    await payload.broadcaster.add_blocked_term(moderator=BOT_ID, text=word.lower())
                    print(f"{word} à été ajouté en tant que termes bloqué sur votre chaine.")

        if self.tts:
            if tts_event:
                
                if payload.chatter.subscriber or payload.chatter.vip or payload.chatter.moderator:
                    if not payload.chatter.broadcaster:
                        play_audio = True
            else:
                play_audio = True

        if payload.chatter.name in ["fossabot", "streamelements", "thebot580", "nightbot", payload.broadcaster.name]: #Bots + broadcaster
            command_message = True
        elif payload.text[0] == "!" or payload.text[0] == '-':
            command_message = True

        if not (banned_message or command_message):

            if self.emotes_combo != ["", 0]: #If we currently have a combo
                if self.message_has_emote(twitchChatMessage, self.emotes_combo[0], self.emotes_dict): #If it is the right emote
                    self.emotes_combo[1] += 1
                    print(f"+1 au combo {self.emotes_combo[0]} grace à {payload.chatter.display_name} (Maintenant {self.emotes_combo[1]}) ")
                else:
                    print(f"Le combo de {self.emotes_combo[1]}x {self.emotes_combo[0]} à été arreté par {payload.chatter.display_name}")
                    if self.emotes_combo[1] >= 5:
                        await payload.broadcaster.send_message(
                            sender=BOT_ID,
                            message=f"Combo de {self.emotes_combo[1]}x {self.emotes_combo[0]}! POGGIES",
                        )
                    self.emotes_combo : list = ["", 0] #Resetting Emotes Combo, because the emote we were looking for wasn't sent
            else:
                if self.message_has_an_emote(twitchChatMessage, self.emotes_dict): #If the message has at least an emote
                    emote : str = self.get_first_emote_in_message(twitchChatMessage, self.emotes_dict)
                    self.emotes_combo : list = [emote, 1]
                    print(f"Nouveau combo d'emotes : {self.emotes_combo[0]}. Commencé par {payload.chatter.display_name}")

            twitchChatMessage = self.treat_message(twitchChatMessage)

            if twitchChatMessage.split() == []:
                play_audio = False

            if play_audio:

                # Send Twitch message to Azure to turn into cool audio
                output = tts_manager.text_to_speech(twitchChatMessage)

                if payload.broadcaster.name == "lerenard580":
                    # Play the file
                    audio_manager.play_audio(output, True, True, True)
                    
        if banned_message:
            # IF A WORD IN SOMEONE'S MESSAGE IS IN self.banned_words, THEY WILL BE BANNED FOREVER, THE MESSAGE WILL NOT BE SAID OUT LOUD, INSTEAD SAYING THAT SOMEONE IS BANNED. MODS / STREAMER CAN UNBAN THEM IF YOU WANT.
            await payload.chatter.ban(moderator=BOT_ID, reason="MESSAGE INVALIDE")
            banMessage = "MOT BANNI DETECTE : LE MESSAGE NE VA PAS ETRE DIT"
            print(banMessage)


    # CHANNEL COMMANDS

    @commands.command(aliases=["hello", "howdy", "hey"])
    async def hi(self, ctx: commands.Context) -> None:
        """Simple command that says hello!

        !hi, !hello, !howdy, !hey
        """
        await ctx.reply(f"Salut {ctx.chatter.mention}!")
    
    @commands.command()
    async def emotes(self, ctx: commands.Context) -> None:
        await ctx.reply("Pour avoir acceès à plein d'emotes gratuitement, installe l'extension BetterTTV (https://betterttv.com) ou 7TV (https://7tv.app/) sur ton navigateur")

    @commands.group(invoke_fallback=True)
    async def socials(self, ctx: commands.Context) -> None:
        """Group command for our social links.

        !socials
        """
        await ctx.reply("https://www.discord.gg/9tmdgHWaMU, https://www.youtube.com/@lerenard580")

    @socials.command(name="discord")
    async def socials_discord(self, ctx: commands.Context) -> None:
        """Sub command of socials that sends only our discord invite.

        !socials discord
        """
        await ctx.reply("The discord : https://www.discord.gg/9tmdgHWaMU")

    @socials.command(name="youtube")
    async def socials_youtube(self, ctx: commands.Context) -> None:
        """Sub command of socials that sends only our discord invite.

        !socials discord
        """
        await ctx.reply("The Youtube channel : https://www.youtube.com/@lerenard580")

    @commands.command(aliases=["follow",'followsince'])
    async def followage(self, ctx: commands.Context):
        print(ctx.chatter)
        if type(ctx.chatter) == twitchio.Chatter:
            follow_info = await ctx.chatter.follow_info()
            print(follow_info)
            if follow_info == None:
                await ctx.reply(f"Désolé {ctx.chatter.display_name}, mais tu ne me follow pas...")
            else:
                follow_time = follow_info.followed_at
                await ctx.reply(f"{ctx.chatter.display_name}, tu me follow depuis {self.format_time_since(datetime.now(timezone.utc), follow_time, True)}. ({follow_time.strftime("%d/%m/%Y à %H:%M:%S %Z")})")

    @commands.command()
    async def uptime(self, ctx: commands.Context):
        await ctx.reply(f"Je suis en live depuis {self.format_time_since(datetime.now(timezone.utc), self.start_time)} (Le stream a commencé vers {self.start_time.strftime("%d/%m/%Y à %H:%M:%S %Z")}).")

    @commands.command()
    async def lurk(self, ctx: commands.Context):
        if ctx.chatter.name not in self.lurkers:
            self.lurkers.append(ctx.chatter.name)
            await ctx.reply(f"Merci de lurk {ctx.chatter.display_name}, à bientot!")
        else:
            await ctx.reply(f"Tu étais déjà en lurk, mais à bientot {ctx.chatter.display_name}.")

    @commands.command()
    async def unlurk(self, ctx: commands.Context):
        if ctx.chatter.name in self.lurkers:
            self.lurkers.remove(ctx.chatter.name)
            await ctx.reply(f"Bienvenue de retour {ctx.chatter.display_name}!")
        else:
            await ctx.reply(f"Tu ne lurkais pas, mais bienvenue de retour quand meme {ctx.chatter.display_name}.")

    @commands.command()
    async def time(self, ctx: commands.Context):
        await ctx.reply(f"Il est actuellement {datetime.now().strftime("%B %d %Y, %H:%M:%S")} pour moi.")
    
    @commands.command()
    async def today(self, ctx: commands.Context):
        channelInfo : twitchio.ChannelInfo = await ctx.broadcaster.fetch_channel_info()
        await ctx.send(channelInfo.title.split('} ')[1])
    
    @commands.command()
    async def tts(self, ctx: commands.Context):
        if ctx.chatter.moderator or ctx.chatter.broadcaster: # type: ignore # type: ignore
            self.tts = not self.tts
            if self.tts:
                await ctx.reply(f"TTS viens d'etre activé.")
                return
            await ctx.reply(f"TTS viens d'etre désactivé.")
            return
        
        if self.tts:
            await ctx.reply(f"TTS est actuellement activé.")
            return
        await ctx.reply(f"TTS est actuellement désactivé.")
    
    #@commands.command()
    #async def subtember(self, ctx: commands.Context):
    #    await ctx.send(f"NEW : BEFORE THE END OF THE MONTH, FOR EVERY 5+ GIFTED SUBS, VALORANT WILL GIVE ADDITIONAL SUBS FOR EVERYONE! For the next {self.format_time_since(datetime.fromtimestamp(1759338000), datetime.now())}, you can get up to 30% off your subscription thanks to this year's SUBtember! If you want to support me, you can do so by going to https://www.twitch.tv/subs/thefox580 !")
    
    #@commands.command(aliases=["donate"])
    #async def charity(self, ctx: commands.Context):
    #    await ctx.send(f"We're raising money for the Water Warrior initiative! Donate here: https://tiltify.com/+the-water-warriors/forsaken-islands-fusion-frenzy")
    
    @commands.command(aliases=["bot"])
    async def version(self, ctx: commands.Context):
        await ctx.reply(f"TheBot580 est un bot custom basé sur Babagaboosh, une application du Youtubeur / Streameur DougDoug. Il tourne actuellement sous la version 2.0_fr (En utilisant TwitchIO 3.2.0 & Python 3.13.12). Vous pouvez allez voir le projet à https://github.com/TheFox580/thebot580", me=True)
    
    @commands.command()
    async def age(self, ctx: commands.Context):
        await ctx.send(f"Je suis agée de {self.format_time_since(datetime.now(), datetime.fromtimestamp(1139072400), True)}.")
    
    @commands.command()
    async def look(self, ctx: commands.Context, *, content: str):

        username = content.split()[0]

        req = requests.get(f"https://api.mcsrranked.com/users/{username}")
        data = json.loads(req.text)
        if data["status"] == "success":
            data = data['data']
            stats = data["statistics"]["season"]
            totalGamesPlayed = stats["playedMatches"]["ranked"]
            gamesWon = stats["wins"]["ranked"]
            gamesLost = stats["loses"]["ranked"]
            gamesTied = totalGamesPlayed - gamesWon - gamesLost
            pb = stats["bestTime"]["ranked"]
            if pb == None:
                pb = ("no", "pb", "yet")
            else:
                pb = (math.floor((pb / (1000*60)) % 60), math.floor((pb / 1000) % 60), math.floor((pb % 1000)))
            ffRate = round(stats["forfeits"]["ranked"] / totalGamesPlayed*100, 2)
            await ctx.reply(f"{username} | Elo: {data["eloRate"]} (Haut/Bas: {data["seasonResult"]["highest"]}/{data["seasonResult"]["lowest"]}) | #{data["eloRank"]} === Joué {totalGamesPlayed} parties | W/D/L {gamesWon}/{gamesTied}/{gamesLost} === PB: {pb[0]}:{pb[1]}.{pb[2]} === {ffRate}% Rage quit", me=True)
            return
        await ctx.reply(f"Aucun joueur avec le pseudo \"{username}\"trouvé")
    
    @commands.command()
    @commands.is_moderator()
    async def setgame(self, ctx: commands.Context, *, content: str) -> None:
        game : twitchio.Game | None = await ctx.bot.fetch_game(name=content)
        print(game)
        if game == None:
            await ctx.reply(f"Jeu non trouvé, la catégorie n'a pas été mise à jour.")
        else:
            await ctx.broadcaster.modify_channel(game_id=game.id)
    
    @commands.command()
    @commands.is_moderator()
    async def settitle(self, ctx: commands.Context, *, content: str) -> None:
        await ctx.broadcaster.modify_channel(title=content)


    # CHANNEL INTERACTIONS

    @commands.Component.listener()
    async def event_follow(self, payload: twitchio.ChannelFollow) -> None:
        print("Évènement reçu : Follow")
        channel = payload.broadcaster
        await channel.send_message(
            sender=BOT_ID,
            message=f"Merci {payload.user.display_name} pour le follow!",
        )

    @commands.Component.listener()
    async def event_subscription(self, payload: twitchio.ChannelSubscribe) -> None:
        print("Évènement reçu : 'Sub'")
        channel = payload.broadcaster
        sub_tier = self.format_tier(payload.tier)
        if not payload.gift:
            await channel.send_message(
                sender=BOT_ID,
                message=f"{payload.user.display_name} s'est abonné en tier {sub_tier}!",
            )
    
    @commands.Component.listener()
    async def event_subscription_message(self, payload: twitchio.ChannelSubscriptionMessage) -> None:
        print("Évènement reçu : 'Resub'")
        channel = payload.broadcaster
        sub_tier = self.format_tier(payload.tier)
        streak = ""
        if payload.streak_months != None and payload.streak_months > 0:
            streak = f" Iel s'est abonné pendant {payload.streak_months} mois d'affilé!"
        await channel.send_message(
            sender=BOT_ID,
            message=f"{payload.user.display_name} s'est réabonné en tier {sub_tier} pour le {payload.months} mois!{streak}",
        )
        message = f"{payload.user.display_name} s'est réabonné en tier {sub_tier} pour le {payload.months} mois!{streak} Iel à dit: \"{self.treat_message(payload.text)}\""
        output = tts_manager.text_to_speech(message)
        audio_manager.play_audio(output, True, True, True)

    @commands.Component.listener()
    async def event_subscription_gift(self, payload: twitchio.ChannelSubscriptionGift) -> None:
        print("Évènement reçu : 'Sub Gift'")
        channel = payload.broadcaster
        sub_tier = self.format_tier(payload.tier, True)
        display_name = "Un utilisateur annonyme"
        if type(payload.user.display_name) == str: # type: ignore
            display_name = payload.user.display_name # type: ignore
        if payload.anonymous:
            await channel.send_message(
                sender=BOT_ID,
                message=f"Un utilisateur annonyme à donné {payload.total} subs de tier {sub_tier} à la communauté! Au total, il y a eu {payload.cumulative_total} sub gifts d'utilisateur annonymes à la communauté!",
            )
        else:
            await channel.send_message(
                sender=BOT_ID,
                message=f"{display_name} à donné {payload.total} subs de tier {sub_tier} à la communauté! Au total, {display_name} à donné {payload.cumulative_total} sub gifts à la communauté!"
            )

    @commands.Component.listener()
    async def event_cheer(self, payload: twitchio.ChannelCheer) -> None:
        print("Évènement reçu : 'Bits'")
        channel = payload.broadcaster
        message = ""
        display_name = "Un utilisateur annonyme"
        if type(payload.user.display_name) == str: # type: ignore
            display_name = payload.user.display_name # type: ignore
        if payload.anonymous:
            await channel.send_message(
                sender=BOT_ID,
                message=f"Un utilisateur annonyme à donné {payload.bits} bits!",
            )
            message = f"Un utilisateur annonyme à donné {payload.bits} bits! Iel à dit: {self.treat_message(payload.message)}"
        else:
            await channel.send_message(
                sender=BOT_ID,
                message=f"{display_name} à donné {payload.bits} bits!",
            )
            message = f"{display_name} à donné {payload.bits} bits! Iel à dit: {self.treat_message(payload.message)}"
        output = tts_manager.text_to_speech(message)
        audio_manager.play_audio(output, True, True, True)

    @commands.Component.listener()
    async def event_prediction_start(self, payload:twitchio.ChannelPredictionBegin) -> None:
        print("Évènement reçu : Début de prédiction")
        channel = payload.broadcaster
        prediction_title = payload.title
        prediction_outcomes = payload.outcomes
        prediction_outcomes_str = f"{prediction_outcomes.pop(0).title}"
        for outcome in prediction_outcomes:
            prediction_outcomes_str += f", {outcome.title}"
        prediction_locks = payload.locks_at
        diff = prediction_locks - datetime.now()
        secs = int(diff.total_seconds())
        mins = int(secs // 60)
        await channel.send_message(
            sender=BOT_ID,
            message=f"Une nouvelle prédiction à commencé! \"{prediction_title}\" | Les choix sont : {prediction_outcomes_str}. Cette prédiction se bloque dans {mins} minute(s)."
        )

    @commands.Component.listener()
    async def event_prediction_lock(self, payload:twitchio.ChannelPredictionLock) -> None:
        print("Évènement reçu : Prediction bloquée")
        channel = payload.broadcaster
        prediction_title = payload.title
        prediction_outcomes = payload.outcomes
        prediction_total = 0
        prediction_highest = prediction_outcomes[0]
        if prediction_highest.channel_points != None:
            prediction_total += prediction_highest.channel_points
        prediction_outcomes_str = f"{prediction_outcomes.pop(0).title}"
        for outcome in prediction_outcomes:
            if outcome.channel_points != None:
                prediction_total += outcome.channel_points
                prediction_outcomes_str += f", {outcome.title}"
                if prediction_highest.channel_points != None and outcome.channel_points > prediction_highest.channel_points:
                    prediction_highest = outcome
        channel_points = 0
        if prediction_highest.channel_points != None:
            channel_points = prediction_highest.channel_points
        await channel.send_message(
            sender=BOT_ID,
            message=f"La prédiction \"{prediction_title}\" est maintenant bloquée! \"{prediction_highest.title}\" est le plus gros choix aved {round(channel_points/prediction_total*100, 2)}% | Les choix sont : {prediction_outcomes_str}."
        )

    @commands.Component.listener()
    async def event_prediction_end(self, payload:twitchio.ChannelPredictionEnd) -> None:
        print("Évènement reçu : Fin de prédiction")
        channel = payload.broadcaster
        prediction_title = payload.title
        if payload.status == 'canceled':
            await channel.send_message(
                sender=BOT_ID,
                message=f"La prédiction \"{prediction_title}\" à été annulée! Tout les points de chaines seront remboursés."
            )
        else:
            prediction_winner = payload.winning_outcome
            prediction_outcomes = payload.outcomes
            prediction_total = 0
            prediction_highest = prediction_outcomes[0]
            if prediction_highest.channel_points != None:
                prediction_total += prediction_highest.channel_points
            prediction_outcomes_str = f"{prediction_outcomes.pop(0).title}"
            for outcome in prediction_outcomes:
                if outcome.channel_points != None:
                    prediction_total += outcome.channel_points
                    prediction_outcomes_str += f", {outcome.title}"
                    if prediction_winner.channel_points != None and outcome.channel_points > prediction_winner.channel_points: # type: ignore
                        prediction_highest = outcome
            channel_points = 0
            if prediction_winner.channel_points != None: # type: ignore
                channel_points = prediction_winner.channel_points # type: ignore
            await channel.send_message(
                sender=BOT_ID,
                message=f"La prédiction \"{prediction_title}\" s'est terminée ! \"{prediction_winner.title}\" est le choix gagnant avec {round(channel_points/prediction_total*100, 2)}% (C'est {prediction_total} TheDollar580 pour {len(prediction_winner.users)} viewers) | Les choix étaient : {prediction_outcomes_str}." # type: ignore
            )

    @commands.Component.listener()
    async def event_poll_begin(self, payload:twitchio.ChannelPollBegin) -> None:
        print("Évènement reçu : Début de sondage")
        channel = payload.broadcaster
        poll_title = payload.title
        poll_choices = payload.choices
        poll_choices_str = f"{poll_choices.pop(0).title}"
        for choice in poll_choices:
            poll_choices_str += f", {choice.title}"
        poll_end = payload.ends_at
        diff = poll_end - datetime.now()
        secs = int(diff.total_seconds())
        mins = int(secs // 60)
        await channel.send_message(
            sender=BOT_ID,
            message=f"Un nouveau sondage à démarré ! \"{poll_title}\" | Les choix sont : {poll_choices_str}. Ce sondage s'arrete dans {mins} minute(s)."
        )

    @commands.Component.listener()
    async def event_poll_end(self, payload:twitchio.ChannelPollEnd) -> None:
        print("Évènement reçu : Fin de sondage")
        channel = payload.broadcaster
        poll_title = payload.title
        poll_choices = payload.choices
        poll_winner = poll_choices[0]
        poll_choices_str = f"{poll_choices.pop(0).title}"
        for choice in poll_choices:
            poll_choices_str += f", {choice.title}"
            if choice.votes != None and poll_winner.votes != None and choice.votes > poll_winner.votes:
                poll_winner = choice
        await channel.send_message(
            sender=BOT_ID,
            message=f"Les réponses ont été donnés! {poll_winner.title} a gagné \"{poll_title}\" avec {poll_winner.votes} votes | Les choix étaient : {poll_choices_str}."
        )

    @commands.Component.listener()
    async def event_stream_online(self, payload: twitchio.StreamOnline) -> None:
        print("Évènement reçu : Début du live")
        self.start_time = datetime.now()
        await payload.broadcaster.send_message(
            sender=BOT_ID,
            message=f"{payload.broadcaster.display_name} est maintenant en live",
        )

    @commands.Component.listener()
    async def event_stream_offline(self, payload: twitchio.StreamOffline) -> None:
        print("Évènement reçu : Fin du live")
        stream_time_diff = self.format_time_since(datetime.now(), self.start_time)
        await payload.broadcaster.send_message(
            sender=BOT_ID,
            message=f"Le stream est maintenant offline. {payload.broadcaster.display_name} était en live pendant {stream_time_diff}",
        )

    @commands.Component.listener()
    async def event_hype_train(self, payload:twitchio.HypeTrainBegin) -> None:
        print("Évènement reçu : Début du train de la hype")
        channel = payload.broadcaster
        train_level = payload.level
        self.hype_train_level = train_level
        shared_text = ""
        is_shared = payload.shared_train
        if is_shared:
            shared_text = "Partagé"
        golden_kappa_text = ""
        if payload.type == "golden_kappa":
            golden_kappa_text = "du Kappa Doré"
        elif payload.type == "treasure":
            golden_kappa_text = "Trésor"
        train_goal = payload.goal
        train_progress = payload.progress
        self.hype_train_level_complete = round(train_progress/train_goal*100,2) #A percentage of level completion
        await channel.send_message(
            sender=BOT_ID,
            message=f"Un Train {golden_kappa_text}{shared_text} vient de commencer ! Nous sommes à {self.hype_train_level_complete}% du niveau {train_level}!"
        )

    @commands.Component.listener()
    async def event_hype_train_progress(self, payload:twitchio.HypeTrainProgress) -> None:
        print("Évènement reçu : Le train de la hype à progressé")
        channel = payload.broadcaster
        train_level = payload.level
        if train_level > self.hype_train_level: # type: ignore
            self.hype_train_level = train_level
            shared_text = ""
            is_shared = payload.shared_train
            if is_shared:
                shared_text = "Partagé"
            golden_kappa_text = ""
            if payload.type == "golden_kappa":
                golden_kappa_text = "du Kappa Doré"
            elif payload.type == "treasure":
                golden_kappa_text = "Trésor"
            train_goal = payload.goal
            train_progress = payload.progress
            self.hype_train_level_complete = round(train_progress/train_goal*100,2) #A percentage of level completion
            await channel.send_message(
                sender=BOT_ID,
                message=f"Un Train {golden_kappa_text}{shared_text} vient de passer au niveau supérieur ! Nous sommes à {self.hype_train_level_complete}% du niveau {train_level}!"
            )

    @commands.Component.listener()
    async def event_hype_train_end(self, payload:twitchio.HypeTrainEnd) -> None:
        print("Évènement reçu : Fin du train de la hype")
        channel = payload.broadcaster
        train_level = payload.level
        self.hype_train_level = -1
        shared_text = ""
        is_shared = payload.shared_train
        if is_shared:
            shared_text = "Partagé"
        golden_kappa_text = ""
        if payload.type == "golden_kappa":
            golden_kappa_text = "du Kappa Doré"
        elif payload.type == "treasure":
            golden_kappa_text = "Trésor"
        train_countdown_until = payload.cooldown_until
        diff = train_countdown_until - datetime.now()
        secs = int(diff.total_seconds())
        mins = int(secs // 60)
        await channel.send_message(
            sender=BOT_ID,
            message=f"Un Train {golden_kappa_text}{shared_text} vient de partir... Nous avons atteint {self.hype_train_level_complete}% du niveau {train_level}! Le prochain Train de la Hype peut revenir dans {mins} minutes."
        )

    @commands.Component.listener()
    async def event_shared_chat_begin(self, payload:twitchio.SharedChatSessionBegin) -> None:
        print("Évènement reçu : Début du Shared Chat")
        channel = payload.broadcaster
        host = payload.host
        participants = payload.participants
        participants_str = payload.host.display_name
        self.shared_chat_users.append(host)
        for participant in participants:
            if participant not in self.shared_chat_users:
                self.shared_chat_users.append(participant)
            participants_str += f", {participant.display_name}" # type: ignore
        await channel.send_message(
            sender=BOT_ID,
            message=f"{host.display_name} à commencé un shared chat avec {participants_str}."
        )

    @commands.Component.listener()
    async def event_shared_chat_update(self, payload:twitchio.SharedChatSessionUpdate) -> None:
        print("Évènement reçu : Mise a jour du Shared Chat")
        channel = payload.broadcaster
        host = payload.host
        participants = payload.participants
        participants.append(host)
        participants_str = payload.host.display_name
        diff = len(self.shared_chat_users) - len(participants)
        if diff < 0: #If a user was added
            self.shared_chat_users = [host]
            for participant in participants:
                if participant not in self.shared_chat_users:
                    self.shared_chat_users.append(participant)
                participants_str += f", {participant.display_name}" # type: ignore
            await channel.send_message(
                sender=BOT_ID,
                message=f"{host.display_name} à ajouté {abs(diff)} utilisateur(s) dans le Shared Chat. Les participants sont {participants_str}."
            )
        else: #If a user was removed
            self.shared_chat_users = [host]
            for participant in participants:
                if participant not in self.shared_chat_users:
                    self.shared_chat_users.append(participant)
                participants_str += f", {participant.display_name}" # type: ignore
            await channel.send_message(
                sender=BOT_ID,
                message=f"{host.display_name} à retiré {diff} utilisateur(s) dans le Shared Chat. Les participants sont {participants_str}."
            )

    @commands.Component.listener()
    async def event_shared_chat_end(self, payload:twitchio.SharedChatSessionEnd) -> None:
        print("Évènement reçu : Fin du Shared Chat")
        channel = payload.broadcaster
        host = payload.host
        self.shared_chat_users = []
        await channel.send_message(
            sender=BOT_ID,
            message=f"{host.display_name} à terminé le Shared Chat."
        )

    @commands.Component.listener()
    async def event_goal_begin(self, payload:twitchio.GoalBegin) -> None:
        print("Évènement reçu : Début du Goal")
        channel = payload.broadcaster
        goal_name = payload.description
        goal_amount = payload.current_amount
        goal_end_amount = payload.target_amount
        goal_type = payload.type
        if goal_type in ['subscription_count', 'new_subscription', 'new_subscription_count']:
            goal_type = 'subs'
        elif goal_type in ['new_bit', 'new_cheer']:
            goal_type = 'bits'
        else:
            goal_type = 'followers'
        await channel.send_message(
            sender=BOT_ID,
            message=f"Un nouveau goal de {goal_type} à commencé! {goal_name} ({goal_amount}/{goal_end_amount})"
        )

    @commands.Component.listener()
    async def event_goal_progress(self, payload:twitchio.GoalProgress) -> None:
        print("Évènement reçu : Progression du Goal")
        channel = payload.broadcaster
        goal_name = payload.description
        goal_amount = payload.current_amount
        goal_end_amount = payload.target_amount
        await channel.send_message(
            sender=BOT_ID,
            message=f"{goal_name} mis à jour! ({goal_amount}/{goal_end_amount})"
        )

    @commands.Component.listener()
    async def event_goal_end(self, payload:twitchio.GoalEnd) -> None:
        print("Évènement reçu : Fin du Goal")
        channel = payload.broadcaster
        goal_name = payload.description
        goal_end_amount = payload.target_amount
        goal_type = payload.type
        if goal_type in ['subscription_count', 'new_subscription', 'new_subscription_count']:
            goal_type = 'subs'
        elif goal_type in ['new_bit', 'new_cheer']:
            goal_type = 'bits'
        else:
            goal_type = 'followers'
        await channel.send_message(
            sender=BOT_ID,
            message=f"{goal_name} a été completé! ({goal_end_amount} {goal_type})"
        )

    @commands.Component.listener()
    async def event_raid(self, payload: twitchio.ChannelRaid) -> None:
        print("Évènement reçu : Nouveau Raid")
        channel = payload.to_broadcaster
        raider = payload.from_broadcaster
        await channel.send_message(
            sender=BOT_ID,
            message=f"Merci beaucoup {raider.display_name} pour le raid de {payload.viewer_count} viewers!",
        )
        await channel.send_shoutout(
            to_broadcaster=raider,
            moderator=BOT_ID,
        )
    
    @commands.Component.listener()
    async def event_channel_update(self, payload: twitchio.ChannelUpdate) -> None:
        print("Évènement reçu : Mise a jour de la chaine")
        channel = payload.broadcaster
        category = payload.category_name
        title = payload.title
        await channel.send_message(
            sender=BOT_ID,
            message=f"Titre mis a jour: \"{title}\". Catégorie mise a jour: \"{category}\"."
        )

    @commands.Component.listener()
    async def event_shoutout_create(self, payload: twitchio.ShoutoutCreate) -> None:
        print("Évènement reçu : Shoutout créé")
        channel = payload.broadcaster
        shoutout_receiver = payload.to_broadcaster
        channel_info = await shoutout_receiver.fetch_channel_info()
        game = await channel_info.fetch_game()
        if game != None:
            await channel.send_message(
                sender=BOT_ID,
                message=f"{shoutout_receiver.display_name} était en train de stream \"{game.name}\"! Si vous appréciez, n'hésitez pas à aller follow!"
            )
            return
        await channel.send_message(
            sender=BOT_ID,
            message=f"{shoutout_receiver.display_name} était en train de stream avec {payload.viewer_count} viewers! Bienvenue!"
        )

def main() -> None:
    twitchio.utils.setup_logging(level=logging.INFO)

    async def runner() -> None:
        async with asqlite.create_pool("tokens.db") as tdb, Bot(token_database=tdb) as bot:
            await bot.setup_database()
            await bot.start()


    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        LOGGER.warning("Shutting down due to KeyboardInterrupt...")


if __name__ == "__main__":
    main()