import asyncio
import logging
import sqlite3

import asqlite
import twitchio
from twitchio.ext import commands
from twitchio import eventsub

from eleven_labs import ElevenLabsManager
from audio_player import AudioManager
from obs_websockets import OBSWebsocketsManager
from datetime import datetime
from keys import TWITCH_BOT_CLIENT_ID, TWITCH_BOT_CLIENT_SECRET, OWNER_ID, BOT_ID

ELEVENLABS_VOICE : str = "Brian" # Replace this with the name of whatever voice you have created on Elevenlabs

START_TIME : datetime = datetime.now()
SHARED_CHAT_USERS : list = []
HYPE_TRAIN_LEVEL : int = -1

elevenlabs_manager = ElevenLabsManager()
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
        
        # Subscribe and listen to when a stream goes on/offline..
        subscriptions.append(eventsub.StreamOnlineSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.StreamOfflineSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when someone (re)sub(-gift)..
        subscriptions.append(eventsub.ChannelSubscribeSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.ChannelSubscribeMessageSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.ChannelSubscriptionGiftSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when someone cheers..
        subscriptions.append(eventsub.ChannelCheerSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when someone follows..
        subscriptions.append(eventsub.ChannelFollowSubscription(broadcaster_user_id=OWNER_ID, moderator_user_id=BOT_ID))

        # Subscribe and listen to when someone raids..
        subscriptions.append(eventsub.ChannelRaidSubscription(to_broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when the title or the game changes..
        subscriptions.append(eventsub.ChannelUpdateSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when shared chat starts, updates or ends..
        subscriptions.append(eventsub.SharedChatSessionBeginSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.SharedChatSessionUpdateSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.SharedChatSessionEndSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when poll starts or ends..
        subscriptions.append(eventsub.ChannelPollBeginSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.ChannelPollEndSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when prediction starts, locks or ends..
        subscriptions.append(eventsub.ChannelPredictionBeginSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.ChannelPredictionLockSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.ChannelPredictionEndSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when goal starts, updates or ends..
        subscriptions.append(eventsub.GoalBeginSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.GoalProgressSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.GoalEndSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when hype train starts, updates or ends..
        subscriptions.append(eventsub.HypeTrainBeginSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.HypeTrainProgressSubscription(broadcaster_user_id=OWNER_ID))
        subscriptions.append(eventsub.HypeTrainEndSubscription(broadcaster_user_id=OWNER_ID))

        for subscription in subscriptions:
            print(f"Subscribing to {subscription}")
            await self.subscribe_websocket(payload=subscription)

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
        self.banned_words = ["dogehype", "viewers. shop", "dghype", "add me on", "graphic designer", "Best viewers on", "Cheap viewers on", "streamrise", "add me up on", "nezhna .com", "streamviewers org", "streamboo .com", "i am a commission artist", "Cheap V̐iewers", "creativefollowers.online", "telegram:", "adding me up on"]
        self.bot = bot

    def treat_message(self, message:str) -> str:

        final_message = ""
        messageList = message.split()
        for word in messageList:
            if "Cheer" in word: #We already handle cheer messages
                pass
            if ("🫡" == word) or ("o7" == word):
                final_message += "oh 7 "
            if "nvm" == word:
                final_message += + "nevermind "
            if "<3" == word:
                final_message += + "love "
            if "D:" == word:
                final_message += + "D face "
            if "W" == word.upper():
                final_message += + "double you "
            else:
                final_message += word + " "
        
        return final_message[:-1]

    def format_tier(self, tier:str, is_gift:bool=False) -> str:
        if not is_gift:
            if tier == "1000":
                return "1 or Prime"
        return tier[0]
    def format_time_since(self, time:datetime) -> str:
        tz = time.tzinfo
        now = datetime.now(tz)
        time_diff = now-time

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

        seconds_text = "second"
        minutes_text = "minute"
        if secs != 1:
            seconds_text += "s"
        if mins != 1:
            minutes_text += "s"

        time_text = f"{mins} {minutes_text} and {secs} {seconds_text}. (Time might be offset by a few days due to leap years.)" #I'm always including the minutes just so that I don't have to handle the "and". Big Brain
        if hours > 0:
            if hours == 1:
                time_text = f"{hours} hour, {time_text}"
            else:
                time_text = f"{hours} hours, {time_text}"
        if days > 0:
            if days == 1:
                time_text = f"{days} day, {time_text}"
            else:
                time_text = f"{days} days, {time_text}"
        if months > 0:
            if months == 1:
                time_text = f"{months} month, {time_text}"
            else:
                time_text = f"{months} months, {time_text}"
        if years > 0:
            if years == 1:
                time_text = f"{years} year, {time_text}"
            else:
                time_text = f"{years} years, {time_text}"
        
        return time_text

    # We use a listener in our Component to display the messages received.
    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:

        tts = True
        tts_event = False
        play_audio = False
        
        banned_message = False
        command_message = False

        print(f"[{payload.broadcaster.name}] - {payload.chatter.name}: {payload.text}")    

        #Setup what will be translated as a variable
        twitchChatMessage = payload.text
        if payload.type == "user_intro":
            command_message = True
            twitchChatMessage = f"FIRST TIME CHATTER --> {payload.chatter.name} said : "

        for word in self.banned_words:
            if word.lower() in payload.text.lower():
                banned_message = True

        if tts:
            if tts_event:
                
                if payload.chatter.subscriber or payload.chatter.vip or payload.chatter.moderator:
                    if not payload.chatter.broadcaster:
                        play_audio = True
            else:
        
        if payload.chatter.name.lower() == "fossabot" or payload.chatter.name.lower() == "streamelements" or payload.chatter.name.lower() == "thebot580" or payload.chatter.name.lower() == "thefox580" or payload.chatter.name.lower() == "thealt580" or payload.chatter.name.lower() == "nightbot":
            COMMANDMESSAGE = True
        
        if payload.text[0] == "!" or payload.text[0] == '-':
            COMMANDMESSAGE = True

        if not (BANNEDMESSAGE and COMMANDMESSAGE):
                play_audio = True
            command_message = True
            command_message = True
        if not (banned_message or command_message):

            twitchChatMessage = self.treat_message(twitchChatMessage)

            if twitchChatMessage.split() == []:
                play_audio = False

            if (play_audio and not (command_message or banned_message)):

                # Send Twitch message to 11Labs to turn into cool audio
                elevenlabs_output = elevenlabs_manager.text_to_audio(twitchChatMessage, ELEVENLABS_VOICE)

                if payload.broadcaster.name == "lerenard580":
                    # Play the mp3 file
                    audio_manager.play_audio(elevenlabs_output, True, True, True)

                if payload.broadcaster.name == "thefox580":

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

                elif payload.broadcaster.name == "thealt580":

                    #THE NEXT LINES MAKES A PNG CHANGE ON MY OBS, CHANGE TO YOUR PNG OR REMOVE IF YOU DON'T HAVE ONE (1st parameter in set_source_visibility)
                    #I replaced the png moving with the "Audio Move" filter on the "Move" OBS Plugin
                    
                    obswebsockets_manager.set_source_visibility("Bots", "Chat_Image_Talk", True)

                    obswebsockets_manager.set_source_visibility("Bots", "Chat_Image_Paused", False)
                    
                    # Play the mp3 file
                    audio_manager.play_audio(elevenlabs_output, True, True, True)
                    
                    obswebsockets_manager.set_source_visibility("Bots", "Chat_Image_Paused", True)

                    obswebsockets_manager.set_source_visibility("Bots", "Chat_Image_Talk", False)
                    
        if banned_message:
            # IF A WORD IN SOMEONE'S MESSAGE IS IN self.banned_words, THEY WILL BE BANNED FOREVER, THE MESSAGE WILL NOT BE SAID OUT LOUD, INSTEAD SAYING THAT SOMEONE IS BANNED. MODS / STREAMER CAN UNBAN THEM IF YOU WANT.
            mod = payload.source_broadcaster
            await mod.ban_user(user=payload.chatter.user(), reason="INVALID MESSAGE")
            banMessage = "BANNED MESSAGE DETECTED : BANNING THE SENDER FOREVER"
            print(banMessage)
            elevenlabs_output = elevenlabs_manager.text_to_audio(banMessage, ELEVENLABS_VOICE)
            audio_manager.play_audio(elevenlabs_output, True, True, True)

    @commands.command(aliases=["hello", "howdy", "hey"])
    async def hi(self, ctx: commands.Context) -> None:
        """Simple command that says hello!

        !hi, !hello, !howdy, !hey
        """
        await ctx.reply(f"Hello {ctx.chatter.mention}!")
    
    @commands.command()
    async def emotes(self, ctx: commands.Context) -> None:
        await ctx.send("To have acces to a lot of new emotes, install the BetterTTV (https://betterttv.com) or 7TV (https://7tv.app/) extension on your navigator")

    @commands.group(invoke_fallback=True)
    async def socials(self, ctx: commands.Context) -> None:
        """Group command for our social links.

        !socials
        """
        await ctx.send("https://www.discord.gg/9tmdgHWaMU, https://www.youtube.com/@thefox580, https://www.twitch.tv/thefox580")

    @socials.command(name="discord")
    async def socials_discord(self, ctx: commands.Context) -> None:
        """Sub command of socials that sends only our discord invite.

        !socials discord
        """
        await ctx.send("The discord : https://www.discord.gg/9tmdgHWaMU")

    @socials.command(name="youtube")
    async def socials_youtube(self, ctx: commands.Context) -> None:
        """Sub command of socials that sends only our discord invite.

        !socials discord
        """
        await ctx.send("The Youtube channel : https://www.youtube.com/@thefox580")

    @commands.command(aliases=["follow",'followsince'])
    async def followage(self, ctx: commands.Context):
        follow_info = await ctx.chatter.follow_info()
        if follow_info == None:
            await ctx.send(f"Sorry {ctx.chatter.display_name}, but you are not following the channel...")
        else:
            follow_time = follow_info.followed_at
            await ctx.send(f"{ctx.chatter.display_name}, you've been following for {self.format_time_since(follow_time)} (Followed on {follow_time.strftime("%d/%m/%Y at %H:%M:%S %Z")})")

    @commands.command()
    async def lurk(self, ctx: commands.Context):
        await ctx.send(f"You just started lurking {ctx.chatter.display_name}, see ya soon !")

    @commands.command()
    async def unlurk(self, ctx: commands.Context):
        await ctx.send(f"Welcome back {ctx.chatter.display_name} !")

    @commands.command()
    async def time(self, ctx: commands.Context):
        await ctx.send(f"It is currently {datetime.now().strftime("%d/%m/%Y, %H:%M:%S %Z")} for Fox.")

    @commands.command(aliases=["charity"])
    async def donate(self, ctx: commands.Context):
        await ctx.send(f"Donate to support the Teenage Cancer Trust as they support young people and their families in their cancer journey: https://tilt.fyi/UypO9dkP0I")

    @commands.command(aliases=["fi"])
    async def forakenisle(self, ctx: commands.Context):
        await ctx.send(f"Forsaken Isle is back for a 3rd season! And this time, they're raising money alongside the Heart of a Hero campaign, raising money to support the Teenage Cancer Trust who support young people and their families in their cancer journey: https://tilt.fyi/X7LjIk6BAS")
    
    @commands.command()
    async def heart(self, ctx: commands.Context):
        await ctx.send(f"Heart of a Hero is a year long fundraiser that is raising money to support in the fight against cancer and support those battling it!")
    
    @commands.command(aliases=["bot"])
    async def version(self, ctx: commands.Context):
        await ctx.send(f"TheBot580 is a custom bot I made in python, based on DougDoug's Babagaboosh's app. It is currently running on version 2.0 (Using TwitchIO 3.0.0b4 & Python 3.13.3)")
    
    @commands.command(aliases=["tc"])
    async def twitchcon(self, ctx: commands.Context):
        await ctx.send(f"I'll be in Rotterdam from Thursday, May 29th to Monday, June 2nd! Of course, I'll be attending TwitchCon Rotterdam 2025 on Saturday & Sunday, but I will also be at WraithStation's \"Minecraft Quiz & Games In The Park\" on Friday! But wait, there's more! Every night, at around 9PM CEST, I'm gonna be cooking on stream!")

    #@commands.command()
    #@commands.is_moderator()
    #async def setgame(self, ctx: commands.Context, *, content: str) -> None:
    #    text = content.split()
    #    text.pop(0)
    #    new_text = ""
    #    for word in text:
    #        new_text += word + " "
    #    await ctx.send(f"Set game category to {new_text}")

    @commands.Component.listener()
    async def event_stream_online(self, payload: twitchio.StreamOnline) -> None:
        # Event dispatched when a user goes live from the subscription we made above...

        # Keep in mind we are assuming this is for ourselves
        # others may not want your bot randomly sending messages...
        START_TIME = datetime.now()
        await payload.broadcaster.send_message(
            sender=BOT_ID,
            message=f"{payload.broadcaster.display_name} is now live",
        )

    @commands.Component.listener()
    async def event_stream_offline(self, payload: twitchio.StreamOffline) -> None:
        # Event dispatched when a user goes live from the subscription we made above...

        # Keep in mind we are assuming this is for ourselves
        # others may not want your bot randomly sending messages...
        stream_end_time = datetime.now()
        stream_time_diff = stream_end_time-START_TIME
        secs = int(stream_time_diff.total_seconds())
        mins = int(secs // 60)
        hours = int(mins // 60)
        await payload.broadcaster.send_message(
            sender=BOT_ID,
            message=f"The stream is now offline. {payload.broadcaster.display_name} has been live for the past {hours} hour(s), {mins-60*hours} minute(s) and {secs-60*mins-60*hours} second(s)",
        )

    @commands.Component.listener()
    async def event_subscription(self, payload: twitchio.ChannelSubscribe) -> None:
        print("Received event : 'New User Subscription'")
        channel = payload.broadcaster
        sub_tier = self.format_tier(payload.tier)
        if not payload.gift:
            await channel.send_message(
                sender=BOT_ID,
                message=f"{payload.user.display_name} subscribed with a Tier {sub_tier} subscription!",
            )

    @commands.Component.listener()
    async def event_subscription_gift(self, payload: twitchio.ChannelSubscriptionGift) -> None:
        print("Received event : 'User Sub Gifting'")
        channel = payload.broadcaster
        sub_tier = self.format_tier(payload.tier, True)
        if payload.anonymous:
            await channel.send_message(
                sender=BOT_ID,
                message=f"An anonymous user gifted {payload.total} Tier {sub_tier} subs to the community! In total, there has been {payload.cumulative_total} sub gifts from anonymous users to the community!",
            )
        else:
            await channel.send_message(f"{payload.user.display_name} gifted {payload.total} Tier {sub_tier} subs to the community! In total, {payload.user.display_name} has gifted {payload.cumulative_total} subs to the community!")
    
    @commands.Component.listener()
    async def event_subscription_message(self, payload: twitchio.ChannelSubscriptionMessage) -> None:
        print("Received event : 'User Resubscription'")
        channel = payload.broadcaster
        sub_tier = self.format_tier(payload.tier)
        await channel.send_message(
            sender=BOT_ID,
            message=f"{payload.user.display_name} resubscribed with a Tier {sub_tier} subscription for {payload.months} months! They've subscribed for {payload.streak_months} months in a row!",
        )
        message = f"{payload.user.display_name} resubscribed with a Tier {sub_tier} subscription for {payload.months} months! They've subscribed for {payload.streak_months} months in a row! They said: \"{self.treat_message(payload.text)}\""
        elevenlabs_output = elevenlabs_manager.text_to_audio(message, ELEVENLABS_VOICE)
        audio_manager.play_audio(elevenlabs_output, True, True, True)

    @commands.Component.listener()
    async def event_cheer(self, payload: twitchio.ChannelCheer) -> None:
        print("Received event : 'User Cheer'")
        channel = payload.broadcaster
        message = ""
        if payload.anonymous:
            await channel.send_message(
                sender=BOT_ID,
                message=f"An anonymous user cheered {payload.bits} bits!",
            )
            message = f"An anonymous user cheered {payload.bits} bits! They said: {self.treat_message(payload.message)}"
        else:
            await channel.send_message(
                sender=BOT_ID,
                message=f"{payload.user.display_name} cheered {payload.bits} bits!",
            )
            message = f"{payload.user.display_name} cheered {payload.bits} bits! They said: {self.treat_message(payload.message)}"
        elevenlabs_output = elevenlabs_manager.text_to_audio(message, ELEVENLABS_VOICE)
        audio_manager.play_audio(elevenlabs_output, True, True, True)

    @commands.Component.listener()
    async def event_follow(self, payload: twitchio.ChannelFollow) -> None:
        print("Received event : User Follow")
        channel = payload.broadcaster
        await channel.send_message(
            sender=BOT_ID,
            message=f"Thank you {payload.user} for the follow!",
        )

    @commands.Component.listener()
    async def event_raid(self, payload: twitchio.ChannelRaid) -> None:
        print("Received event : New Raid")
        channel = payload.to_broadcaster
        raider = payload.from_broadcaster
        await channel.send_message(
            sender=BOT_ID,
            message=f"Thank you so much {raider.display_name} for the raid with {payload.viewer_count} viewers!",
        )
        await channel.send_shoutout(
            to_broadcaster=raider,
            moderator=BOT_ID,
        )
    
    @commands.Component.listener()
    async def event_channel_update(self, payload: twitchio.ChannelUpdate) -> None:
        print("Received event : Channel Update")
        channel = payload.broadcaster
        category = payload.category_name
        title = payload.title
        await channel.send_message(
            sender=BOT_ID,
            message=f"Updated title to \"{title}\" and category to \"{category}\"."
        )

    @commands.Component.listener()
    async def event_shared_chat_begin(self, payload:twitchio.SharedChatSessionBegin) -> None:
        print("Received event : Shared Chat session started")
        channel = payload.broadcaster
        host = payload.host
        participants = payload.participants
        participants_str = payload.host.display_name
        SHARED_CHAT_USERS.append(host)
        for participant in participants:
            SHARED_CHAT_USERS.append(participant)
            participants_str += f", {participant.display_name}"
        await channel.send_message(
            sender=BOT_ID,
            message=f"{host.display_name} has started a shared chat session with {participants_str}."
        )

    @commands.Component.listener()
    async def event_shared_chat_update(self, payload:twitchio.SharedChatSessionUpdate) -> None:
        print("Received event : Shared Chat session updated")
        channel = payload.broadcaster
        host = payload.host
        participants = payload.participants
        participants_str = payload.host.display_name
        diff = len(SHARED_CHAT_USERS) - len(participants.append(host))
        if diff < 0: #If a user was added
            SHARED_CHAT_USERS = [host]
            for participant in participants:
                SHARED_CHAT_USERS.append(participant)
                participants_str += f", {participant.display_name}"
            await channel.send_message(
                sender=BOT_ID,
                message=f"{host.display_name} has added {abs(diff)} users to the shared chat. The participants now are {participants_str}."
            )
        else: #If a user was removed
            SHARED_CHAT_USERS = [host]
            for participant in participants:
                SHARED_CHAT_USERS.append(participant)
                participants_str += f", {participant.display_name}"
            await channel.send_message(
                sender=BOT_ID,
                message=f"{host.display_name} has removed {diff} users to the shared chat. The participants now are {participants_str}."
            )

    @commands.Component.listener()
    async def event_shared_chat_end(self, payload:twitchio.SharedChatSessionEnd) -> None:
        print("Received event : Shared Chat session ended")
        channel = payload.broadcaster
        host = payload.host
        SHARED_CHAT_USERS = []
        await channel.send_message(
            sender=BOT_ID,
            message=f"{host.display_name} has ended the shared chat session."
        )

    @commands.Component.listener()
    async def event_poll_begin(self, payload:twitchio.ChannelPollBegin) -> None:
        print("Received event : Poll started")
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
            message=f"A new poll has been started ! \"{poll_title}\" | Choices are : {poll_choices_str}. This poll ends in {mins} minute(s)."
        )

    @commands.Component.listener()
    async def event_poll_end(self, payload:twitchio.ChannelPollEnd) -> None:
        print("Received event : Poll ended")
        channel = payload.broadcaster
        poll_title = payload.title
        poll_choices = payload.choices
        poll_winner = poll_choices[0]
        poll_choices_str = f"{poll_choices.pop(0).title}"
        for choice in poll_choices:
            poll_choices_str += f", {choice.title}"
            if choice.votes > poll_winner.votes:
                poll_winner = choice
        await channel.send_message(
            sender=BOT_ID,
            message=f"Anwsers are in! {poll_winner.title} won \"{poll_title}\" with {poll_winner.votes} votes | Choices were : {poll_choices_str}."
        )

    @commands.Component.listener()
    async def event_prediction_start(self, payload:twitchio.ChannelPredictionBegin) -> None:
        print("Received event : Prediction started")
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
            message=f"A new prediction has been started ! \"{prediction_title}\" | Outcomes are : {prediction_outcomes_str}. This prediction locks in {mins} minute(s)."
        )

    @commands.Component.listener()
    async def event_prediction_lock(self, payload:twitchio.ChannelPredictionLock) -> None:
        print("Received event : Prediction locked")
        channel = payload.broadcaster
        prediction_title = payload.title
        prediction_outcomes = payload.outcomes
        prediction_total = 0
        prediction_highest = prediction_outcomes[0]
        if prediction_highest.channel_points != None:
            prediction_total += prediction_highest.channel_points
        prediction_outcomes_str = f"{prediction_outcomes.pop(0).title}"
        for outcome in prediction_outcomes:
            prediction_total += outcome.channel_points
            prediction_outcomes_str += f", {outcome.title}"
            if outcome.channel_points > prediction_highest.channel_points:
                prediction_highest = outcome
        await channel.send_message(
            sender=BOT_ID,
            message=f"The \"{prediction_title}\" prediction has been locked! {prediction_highest.title} is the highest outcome with {round(prediction_highest.channel_points/prediction_total*100, 2)}% | Outcomes are : {prediction_outcomes_str}."
        )

    @commands.Component.listener()
    async def event_prediction_end(self, payload:twitchio.ChannelPredictionEnd) -> None:
        print("Received event : Prediction ended")
        channel = payload.broadcaster
        prediction_title = payload.title
        if payload.status == 'canceled':
            await channel.send_message(
                sender=BOT_ID,
                message=f"The \"{prediction_title}\" prediction has been canceled! All channel points will be refunded."
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
                prediction_total += outcome.channel_points
                prediction_outcomes_str += f", {outcome.title}"
                if outcome.channel_points > prediction_highest.channel_points:
                    prediction_highest = outcome
            await channel.send_message(
                sender=BOT_ID,
                message=f"The \"{prediction_title}\" prediction has been ended! {prediction_winner.title} is the winning outcome with {round(prediction_winner.channel_points/prediction_total*100, 2)}% (That's {prediction_total} TheDollar580 for {len(prediction_winner.users)} chatters) | Outcomes were : {prediction_outcomes_str}."
            )

    @commands.Component.listener()
    async def event_goal_begin(self, payload:twitchio.GoalBegin) -> None:
        print("Received event : Goal Begin")
        channel = payload.broadcaster
        goal_name = payload.description
        goal_amount = payload.current_amount
        goal_end_amount = payload.target_amount
        goal_type = payload.type
        if goal_type in ['subscription_count', 'new_subscription', 'new_subscription_count']:
            goal_type = 'subscription'
        elif goal_type in ['new_bit', 'new_cheer']:
            goal_type = 'cheer'
        await channel.send_message(
            sender=BOT_ID,
            message=f"A new {goal_type} goal has begun! {goal_name} ({goal_amount}/{goal_end_amount})"
        )

    @commands.Component.listener()
    async def event_goal_progress(self, payload:twitchio.GoalProgress) -> None:
        print("Received event : Goal Begin")
        channel = payload.broadcaster
        goal_name = payload.description
        goal_amount = payload.current_amount
        goal_end_amount = payload.target_amount
        await channel.send_message(
            sender=BOT_ID,
            message=f"{goal_name} updated! ({goal_amount}/{goal_end_amount})"
        )

    @commands.Component.listener()
    async def event_goal_end(self, payload:twitchio.GoalEnd) -> None:
        print("Received event : Goal Begin")
        channel = payload.broadcaster
        goal_name = payload.description
        goal_end_amount = payload.target_amount
        goal_type = payload.type
        if goal_type in ['subscription_count', 'new_subscription', 'new_subscription_count']:
            goal_type = 'subscribers'
        elif goal_type in ['new_bit', 'new_cheer']:
            goal_type = 'bits'
        else:
            goal_type = 'followers'
        await channel.send_message(
            sender=BOT_ID,
            message=f"{goal_name} has been completed! ({goal_end_amount} {goal_type})"
        )

    @commands.Component.listener()
    async def event_hype_train(self, payload:twitchio.HypeTrainBegin) -> None:
        print("Received event : Hype Train started")
        channel = payload.broadcaster
        train_level = payload.level
        HYPE_TRAIN_LEVEL = train_level
        golden_kappa_text = ""
        is_golden_kappa = payload.golden_kappa
        if is_golden_kappa:
            golden_kappa_text = "Golden Kappa "
        train_goal = payload.goal
        train_progress = payload.progress
        train_level_complete = round(train_progress/train_goal*100,2) #A percentage of level completion
        await channel.send_message(
            sender=BOT_ID,
            message=f"A {golden_kappa_text}Hype Train has just started! We're {train_level_complete}% through level {train_level}!"
        )

    @commands.Component.listener()
    async def event_hype_train_progress(self, payload:twitchio.HypeTrainProgress) -> None:
        print("Received event : Hype Train progressed")
        channel = payload.broadcaster
        train_level = payload.level
        if train_level > HYPE_TRAIN_LEVEL:
            HYPE_TRAIN_LEVEL = train_level
            golden_kappa_text = ""
            is_golden_kappa = payload.golden_kappa
            if is_golden_kappa:
                golden_kappa_text = "Golden Kappa "
            train_goal = payload.goal
            train_progress = payload.progress
            train_level_complete = round(train_progress/train_goal*100,2) #A percentage of level completion
            await channel.send_message(
                sender=BOT_ID,
                message=f"The {golden_kappa_text}Hype Train has leveled up! We're {train_level_complete}% through level {train_level}!"
            )

    @commands.Component.listener()
    async def event_hype_train_end(self, payload:twitchio.HypeTrainEnd) -> None:
        print("Received event : Hype Train ended")
        channel = payload.broadcaster
        train_level = payload.level
        HYPE_TRAIN_LEVEL = -1
        golden_kappa_text = ""
        is_golden_kappa = payload.golden_kappa
        if is_golden_kappa:
            golden_kappa_text = "Golden Kappa "
        train_goal = payload.goal
        train_progress = payload.progress
        train_level_complete = round(train_progress/train_goal*100,2) #A percentage of level completion
        train_countdown_until = payload.cooldown_until
        diff = train_countdown_until - datetime.now()
        secs = int(diff.total_seconds())
        mins = int(secs // 60)
        await channel.send_message(
            sender=BOT_ID,
            message=f"The {golden_kappa_text}Hype Train has left the chat... We reached {train_level_complete}% of level {train_level}! The next Hype Train can come back in {mins} minutes."
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