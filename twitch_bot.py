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

ELEVENLABS_VOICE = "Charlie" # Replace this with the name of whatever voice you have created on Elevenlabs

stream_start_time = datetime.now()

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

        # Subscribe and listen to when a stream goes live..
        # For this example listen to our own stream...
        subscriptions.append(eventsub.StreamOnlineSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when a stream goes offline..
        subscriptions.append(eventsub.StreamOfflineSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when someone subscribes..
        subscriptions.append(eventsub.ChannelSubscribeSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when someone resubscribes..
        subscriptions.append(eventsub.ChannelSubscribeMessageSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when someone gift-subscribes..
        subscriptions.append(eventsub.ChannelSubscriptionGiftSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when someone cheers..
        subscriptions.append(eventsub.ChannelCheerSubscription(broadcaster_user_id=OWNER_ID))

        # Subscribe and listen to when someone follows..
        subscriptions.append(eventsub.ChannelFollowSubscription(broadcaster_user_id=OWNER_ID, moderator_user_id=BOT_ID))

        # Subscribe and listen to when someone raids..
        subscriptions.append(eventsub.ChannelRaidSubscription(to_broadcaster_user_id=OWNER_ID))

        for subscription in subscriptions:
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
            if "Cheer" in word:
                messageList.remove(word)
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

    # We use a listener in our Component to display the messages received.
    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:

        TTS = True
        TTS_EVENT = False
        PLAY_AUDIO = False
        
        BANNEDMESSAGE = False
        COMMANDMESSAGE = False

        print(f"[{payload.broadcaster.name}] - {payload.chatter.name}: {payload.text}")    

        #Setup what will be translated as a variable
        twitchChatMessage = payload.text
        if payload.type == "user_intro":
            COMMANDMESSAGE = True
            twitchChatMessage = f"FIRST TIME CHATTER --> {payload.chatter.name} said : "

        for word in self.banned_words:
            if word.lower() in payload.text.lower():
                BANNEDMESSAGE = True

        if TTS:
            if TTS_EVENT:
                
                if payload.chatter.subscriber or payload.chatter.vip or payload.chatter.moderator:
                    if not payload.chatter.broadcaster:
                        PLAY_AUDIO = True
            else:
                PLAY_AUDIO = True
        
        if payload.chatter.name.lower() == "fossabot" or payload.chatter.name.lower() == "streamelements" or payload.chatter.name.lower() == "thebot580" or payload.chatter.name.lower() == "thefox580" or payload.chatter.name.lower() == "thealt580" or payload.chatter.name.lower() == "nightbot":
            COMMANDMESSAGE = True
        
        if payload.text[0] == "!" or payload.text[0] == '-':
            COMMANDMESSAGE = True

        if not (BANNEDMESSAGE and COMMANDMESSAGE):

            twitchChatMessage = self.treat_message(twitchChatMessage)

            if twitchChatMessage.split() == []:
                PLAY_AUDIO = False

            if (PLAY_AUDIO and not (COMMANDMESSAGE or BANNEDMESSAGE)):

                # Send Twitch message to 11Labs to turn into cool audio
                elevenlabs_output = elevenlabs_manager.text_to_audio(twitchChatMessage, ELEVENLABS_VOICE, False)

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
                    
        if BANNEDMESSAGE:
            # IF A WORD IN SOMEONE'S MESSAGE IS IN self.banned_words, THEY WILL BE BANNED FOREVER, THE MESSAGE WILL NOT BE SAID OUT LOUD, INSTEAD SAYING THAT SOMEONE IS BANNED. MODS / STREAMER CAN UNBAN THEM IF YOU WANT.
            mod = payload.source_broadcaster
            await mod.ban_user(user=payload.chatter.user(), reason="INVALID MESSAGE")
            banMessage = "BANNED MESSAGE DETECTED : BANNING THE SENDER FOREVER"
            print(banMessage)
            elevenlabs_output = elevenlabs_manager.text_to_audio(banMessage, ELEVENLABS_VOICE, False)
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

    @commands.command()
    async def followage(self, ctx: commands.Context):
        if ctx.chatter.follow_info() == None:
            await ctx.send(f"Sorry {ctx.chatter.display_name}, but you are not following the channel...")
        else:
            follow_info = ctx.chatter.follow_info()
            await ctx.send(f"{ctx.chatter.display_name}, you've been following for {follow_info.followed_at}")

    @commands.command()
    async def lurk(self, ctx: commands.Context):
        await ctx.send(f"You just started lurking {ctx.chatter.display_name}, see ya soon !")

    @commands.command()
    async def unlurk(self, ctx: commands.Context):
        await ctx.send(f"Welcome back {ctx.chatter.display_name} !")

    @commands.command()
    async def time(self, ctx: commands.Context):
        await ctx.send(f"It is currently {datetime.now().strftime("%d/%m/%Y, %H:%M:%S")} CEST for Fox.")

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
        stream_start_time = datetime.now()
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
        stream_time_diff = stream_end_time-stream_start_time
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
        elevenlabs_output = elevenlabs_manager.text_to_audio(message, ELEVENLABS_VOICE, False)
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
        elevenlabs_output = elevenlabs_manager.text_to_audio(message, ELEVENLABS_VOICE, False)
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