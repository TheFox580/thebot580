import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timezone

import asqlite
import twitchio
from twitchio import eventsub
from twitchio.ext import commands

from audio_player import AudioManager
from keys import (
    AZURE_TTS_VOICE,
    BOT_ID,
    HAS_ONBOARDED,
    LANG,
    OWNER_ID,
    TWITCH_BOT_CLIENT_ID,
    TWITCH_BOT_CLIENT_SECRET,
)
from obs_websockets import OBSWebsocketsManager
from tts import TTSManager
from banned_words import getBannedWords

tts_manager = TTSManager(AZURE_TTS_VOICE)
audio_manager = AudioManager()
obswebsockets_manager = OBSWebsocketsManager()

LOGGER: logging.Logger = logging.getLogger("TheBot580")

with open(f"lang/{LANG}.json", 'r', encoding="utf-8") as lang_file:
    lang_doc = json.load(lang_file)

def translation(input: str) -> str:
    search = lang_doc
    explored = ""

    for key in input.split("."):
        if key not in search.keys():
            raise KeyError(f"Key '{key}' does not exist in '{explored[:-1]}' from 'lang/{LANG}.json'.")
        search = search[key]
        explored += f"{key}."

    return search

class Bot(commands.AutoBot):
    def __init__(
        self,
        *,
        token_database: asqlite.Pool,
        subs: list[eventsub.SubscriptionPayload],
        owner: str,
    ) -> None:
        self.token_database = token_database

        super().__init__(
            client_id=TWITCH_BOT_CLIENT_ID,
            client_secret=TWITCH_BOT_CLIENT_SECRET,
            bot_id=BOT_ID,
            owner_id=OWNER_ID,
            prefix="!",
            subscriptions=subs,
            force_subscribe=True,
        )

    async def setup_hook(self) -> None:
        # Add our component which contains our commands...
        await self.add_component(MyComponent(self))

    async def event_oauth_authorized(
        self, payload: twitchio.authentication.UserTokenPayload
    ) -> None:
        await self.add_token(payload.access_token, payload.refresh_token)

        if not payload.user_id:
            return

        if payload.user_id == self.bot_id:
            return

        subscriptions: list[eventsub.SubscriptionPayload] = []

        # Subscribe to read chat (event_message) from our channel as the bot...
        # This creates and opens a websocket to Twitch EventSub...
        subscriptions.append(
            eventsub.ChatMessageSubscription(
                broadcaster_user_id=payload.user_id, user_id=self.bot_id
            )
        )

        # Subscribe and listen to when someone follows..
        subscriptions.append(
            eventsub.ChannelFollowSubscription(
                broadcaster_user_id=payload.user_id, moderator_user_id=self.bot_id
            )
        )

        # Subscribe and listen to when a shoutout is sent / received..
        subscriptions.append(
            eventsub.ShoutoutCreateSubscription(
                broadcaster_user_id=payload.user_id, moderator_user_id=self.bot_id
            )
        )
        subscriptions.append(
            eventsub.ShoutoutReceiveSubscription(
                broadcaster_user_id=payload.user_id, moderator_user_id=self.bot_id
            )
        )

        # Subscribe and listen to when a stream goes on/offline..
        subscriptions.append(
            eventsub.StreamOnlineSubscription(broadcaster_user_id=payload.user_id)
        )
        subscriptions.append(
            eventsub.StreamOfflineSubscription(broadcaster_user_id=payload.user_id)
        )

        # Subscribe and listen to when someone raids..
        subscriptions.append(
            eventsub.ChannelRaidSubscription(to_broadcaster_user_id=payload.user_id)
        )

        # Subscribe and listen to when the title or the game changes..
        subscriptions.append(
            eventsub.ChannelUpdateSubscription(broadcaster_user_id=payload.user_id)
        )

        # These events are disabled for now, as they are kinda broken. I plan on fixing them in the next update.
        # Subscribe and listen to when shared chat starts, updates or ends..
        subscriptions.append(
            eventsub.SharedChatSessionBeginSubscription(broadcaster_user_id=OWNER_ID)
        )
        subscriptions.append(
            eventsub.SharedChatSessionUpdateSubscription(broadcaster_user_id=OWNER_ID)
        )
        subscriptions.append(
            eventsub.SharedChatSessionEndSubscription(broadcaster_user_id=OWNER_ID)
        )

        subscriptions.append(
            eventsub.ChatNotificationSubscription(
              broadcaster_user_id=OWNER_ID, user_id=BOT_ID
            )
        )

        # Affiliate & Partner only subscriptions:
        if HAS_ONBOARDED:
            # Subscribe and listen to when someone (re)sub(-gift)..
            subscriptions.append(
                eventsub.ChannelSubscribeSubscription(
                    broadcaster_user_id=payload.user_id
                )
            )
            subscriptions.append(
                eventsub.ChannelSubscribeMessageSubscription(
                    broadcaster_user_id=payload.user_id
                )
            )
            subscriptions.append(
                eventsub.ChannelSubscriptionGiftSubscription(
                    broadcaster_user_id=payload.user_id
                )
            )

            # Subscribe and listen to when someone cheers..
            subscriptions.append(
                eventsub.ChannelCheerSubscription(broadcaster_user_id=payload.user_id)
            )

            # Subscribe and listen to when prediction starts, progresses, locks or ends..
            subscriptions.append(
                eventsub.ChannelPredictionBeginSubscription(
                    broadcaster_user_id=payload.user_id
                )
            )
            subscriptions.append(
                eventsub.ChannelPredictionProgressSubscription(
                    broadcaster_user_id=payload.user_id
                )
            )
            subscriptions.append(
                eventsub.ChannelPredictionLockSubscription(
                    broadcaster_user_id=payload.user_id
                )
            )
            subscriptions.append(
                eventsub.ChannelPredictionEndSubscription(
                    broadcaster_user_id=payload.user_id
                )
            )

            # Subscribe and listen to when poll starts, updates or ends..
            subscriptions.append(
                eventsub.ChannelPollBeginSubscription(
                    broadcaster_user_id=payload.user_id
                )
            )
            subscriptions.append(
                eventsub.ChannelPollProgressSubscription(
                    broadcaster_user_id=payload.user_id
                )
            )
            subscriptions.append(
                eventsub.ChannelPollEndSubscription(broadcaster_user_id=payload.user_id)
            )

            # Subscribe and listen to when hype train starts, updates or ends..
            subscriptions.append(
                eventsub.HypeTrainBeginSubscription(broadcaster_user_id=payload.user_id)
            )
            subscriptions.append(
                eventsub.HypeTrainProgressSubscription(
                    broadcaster_user_id=payload.user_id
                )
            )
            subscriptions.append(
                eventsub.HypeTrainEndSubscription(broadcaster_user_id=payload.user_id)
            )

            # Subscribe and listen to when goal starts, updates or ends..
            subscriptions.append(
                eventsub.GoalBeginSubscription(broadcaster_user_id=payload.user_id)
            )
            subscriptions.append(
                eventsub.GoalProgressSubscription(broadcaster_user_id=payload.user_id)
            )
            subscriptions.append(
                eventsub.GoalEndSubscription(broadcaster_user_id=payload.user_id)
            )

            # Subscribe and listen to when Channel Points are redeemed..
            subscriptions.append(
                eventsub.ChannelPointsAutoRedeemSubscription(
                    broadcaster_user_id=payload.user_id
                )
            )
            subscriptions.append(
                eventsub.ChannelPointsRedeemAddSubscription(
                    broadcaster_user_id=payload.user_id
                )
            )
            subscriptions.append(
                eventsub.CustomPowerupRedeemAddSubscription(
                    broadcaster_user_id=payload.user_id
                )
            )

            subscriptions.append(
                eventsub.AdBreakBeginSubscription(broadcaster_user_id=payload.user_id),
            )

        resp: twitchio.MultiSubscribePayload = await self.multi_subscribe(subscriptions)
        if resp.errors:
            LOGGER.warning(
                translation("logger.warning.fail_to_subscribe"), resp.errors, payload.user_id
            )

        return await super().event_oauth_authorized(payload)

    async def add_token(
        self, token: str, refresh: str
    ) -> twitchio.authentication.ValidateTokenPayload:
        # Make sure to call super() as it will add the tokens interally and return us some data...
        resp: twitchio.authentication.ValidateTokenPayload = await super().add_token(
            token, refresh
        )

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

        LOGGER.info(translation("logger.info.add_token"), resp.user_id)
        return resp

    async def event_ready(self) -> None:
        LOGGER.info(translation("logger.info.login_success"), self.bot_id)


class MyComponent(commands.Component):
    def __init__(self, bot: Bot):
        # Passing args is not required...
        # We pass bot here as an example...
        self.banned_words = getBannedWords()
        self.bot = bot

        self.shared_chat_users: list = []
        self.hype_train_level: int = -1
        self.hype_train_level_complete: float = 0
        self.lurkers = []
        self.activate_tts = True

    def treat_message(self, message: str) -> str:
        final_message = ""
        if "Cheer" in message:  # We don't want it to say the bits amount!
            return ""
        messageList = message.split()
        for word in messageList:
            word = word.replace("_", " ")
            if ("🫡" == word) or ("o7" == word):
                final_message += "oh 7 "
            elif "D:" == word:
                final_message += "D face "
            elif "D:" == word:
                final_message += "D face "
            elif "<3" == word:
                final_message += "love "
            elif "</3" == word:
                final_message += "don't love "
            elif "https" in word:
                pass
            else:
                final_message += word + " "

        return final_message[:-1]

    def format_tier(self, tier: str, is_gift: bool = False) -> str:
        if not is_gift:
            if tier == "1000":
                return translation("functions.format_tier.tier_1_or_prime")
        return tier[0]

    def format_time_since(
        self, biggest: datetime, smallest: datetime, leap_year_warning: bool = False
    ) -> str:
        time_diff = biggest - smallest

        secs = int(time_diff.total_seconds())
        mins = int(secs // 60)
        secs -= mins * 60
        hours = int(mins // 60)
        mins -= hours * 60
        days = int(hours // 24)
        hours -= days * 24
        years = int(days // 365.2422)
        months_but_it_s_based_from_the_years_because_i_dont_want_to_do_annoying_calculations = (
            (days / 365.2422) - years
        )
        months = int(
            months_but_it_s_based_from_the_years_because_i_dont_want_to_do_annoying_calculations
            * 12
        )
        days -= int(years * 365.2242 + months * 30.436875)

        seconds_text = translation("functions.format_time_since.second.base")
        minutes_text = translation("functions.format_time_since.minute.base")
        if secs != 1:
            seconds_text += translation("functions.format_time_since.second.plural")
        if mins != 1:
            minutes_text += translation("functions.format_time_since.minute.plural")

        time_text = translation("functions.format_time_since.text").format(mins, minutes_text, secs, seconds_text)

        if leap_year_warning:
            time_text += translation("functions.format_time_since.leap_year")

        if hours > 0:
            if hours == 1:
                time_text = translation("functions.format_time_since.hour.one").format(hours, time_text)
            else:
                time_text = translation("functions.format_time_since.hour.multiple").format(hours, time_text)
        if days > 0:
            if days == 1:
                time_text = translation("functions.format_time_since.day.one").format(days, time_text)
            else:
                time_text = translation("functions.format_time_since.day.multiple").format(days, time_text)
        if months > 0:
            if months == 1:
                time_text = translation("functions.format_time_since.month.one").format(months, time_text)
            else:
                time_text = translation("functions.format_time_since.month.multiple").format(months, time_text)
        if years > 0:
            if years == 1:
                time_text = translation("functions.format_time_since.year.one").format(years, time_text)
            else:
                time_text = translation("functions.format_time_since.year.multiple").format(years, time_text)

        return time_text

    # We use a listener in our Component to display the messages received.
    @commands.Component.listener("event_message")
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        tts_event = False
        play_audio = False

        banned_message = False
        command_message = False

        print(
            translation("event.message.print").format(payload.broadcaster.display_name, payload.chatter.display_name, payload.text, translation("event.message.from_broadcast") if payload.source_broadcaster is not None else '')
        )

        # Setup what will be translated as a variable
        twitchChatMessage = payload.text
        if payload.type == "user_intro":
            command_message = True
            twitchChatMessage = translation("event.message.first_time").format(payload.chatter.name, twitchChatMessage)

        blocked_terms: list[str] = []
        async for blocked_term in payload.broadcaster.fetch_blocked_terms(
            moderator=BOT_ID
        ):
            term: twitchio.BlockedTerm = blocked_term
            blocked_terms.append(term.text.lower())

        for word in self.banned_words:
            if word.lower() in payload.text.lower():
                banned_message = True
                if word.lower() not in blocked_terms:
                    await payload.broadcaster.add_blocked_term(
                        moderator=BOT_ID, text=word.lower()
                    )
                    print(translation("event.message.block").format(word))
                    await payload.delete(moderator=BOT_ID)

        if self.activate_tts:
            if tts_event:
                if (
                    payload.chatter.subscriber
                    or payload.chatter.vip
                    or payload.chatter.moderator
                ):
                    if not payload.chatter.broadcaster:
                        play_audio = True
            else:
                play_audio = True

        if payload.chatter.name in [
            "fossabot",
            "streamelements",
            "thebot580",
            "nightbot",
            payload.broadcaster.name,
        ]:  # Bots + broadcaster
            command_message = True
        elif payload.text[0] == "!" or payload.text[0] == "-":
            command_message = True
        elif payload.source_broadcaster is not None:
            command_message = True

        if not (banned_message or command_message):
            twitchChatMessage = self.treat_message(twitchChatMessage)

            if twitchChatMessage.split() == []:
                play_audio = False

            elif twitchChatMessage.split(".") == []:
                play_audio = False

            if payload.broadcaster.id != OWNER_ID:  # Only play TTS from my chat
                play_audio = False

            if play_audio and not (command_message or banned_message):
                # Send Twitch message to Azure to turn into cool audio
                output = tts_manager.text_to_speech(twitchChatMessage)

                # Play the file
                audio_manager.play_audio(output, True, True, True)

        if banned_message:
            # IF A WORD IN SOMEONE'S MESSAGE IS IN self.banned_words, THEY WILL BE BANNED FOREVER, THE MESSAGE WILL NOT BE SAID OUT LOUD, INSTEAD SAYING THAT SOMEONE IS BANNED. MODS / STREAMER CAN UNBAN THEM IF YOU WANT.
            await payload.chatter.ban(moderator=BOT_ID, reason=translation("event.message.ban"))

    # CHANNEL COMMANDS

    @commands.command(aliases=["hello", "howdy", "hey"])
    async def hi(self, ctx: commands.Context) -> None:
        """Simple command that says hello!

        !hi, !hello, !howdy, !hey
        """
        await ctx.reply(translation("commands.hi").format(ctx.chatter.mention))

    @commands.group(invoke_fallback=True)
    async def socials(self, ctx: commands.Context) -> None:
        """Group command for our social links.

        !socials
        """
        await ctx.reply(translation("commands.socials.all"))

    @socials.command(name="discord")
    async def socials_discord(self, ctx: commands.Context) -> None:
        """Sub command of socials that sends only our discord invite.

        !socials discord
        """
        await ctx.reply(translation("commands.socials.discord"))

    @socials.command(name="youtube")
    async def socials_youtube(self, ctx: commands.Context) -> None:
        """Sub command of socials that sends only our discord invite.

        !socials discord
        """
        await ctx.reply(translation("commands.socials.youtube"))

    @commands.command(aliases=["follow", "followsince"])
    async def followage(self, ctx: commands.Context):
        print(ctx.chatter)
        if type(ctx.chatter) is twitchio.Chatter:
            follow_info = await ctx.chatter.follow_info()
            print(follow_info)
            if follow_info is None:
                await ctx.reply(translation("commands.followage.fail").format(ctx.chatter.display_name))
            else:
                follow_time = follow_info.followed_at
                await ctx.reply(translation("commands.followage.success").format(ctx.chatter.display_name, self.format_time_since(datetime.now(timezone.utc), follow_time, True), follow_time.strftime('%d/%m/%Y at %H:%M:%S %Z')))

    @commands.command()
    async def lurk(self, ctx: commands.Context):
        if ctx.chatter.name not in self.lurkers:
            self.lurkers.append(ctx.chatter.name)
            await ctx.reply(translation("commands.lurk.success").format(ctx.chatter.display_name))
        else:
            await ctx.reply(translation("commands.lurk.fail").format(ctx.chatter.display_name))

    @commands.command()
    async def unlurk(self, ctx: commands.Context):
        if ctx.chatter.name in self.lurkers:
            self.lurkers.remove(ctx.chatter.name)
            await ctx.reply(translation("commands.unlurk.success").format(ctx.chatter.display_name))
        else:
            await ctx.reply(translation("commands.unlurk.fail").format(ctx.chatter.display_name))

    @commands.command()
    @commands.is_lead_moderator()
    async def tts(self, ctx: commands.Context):
        if ctx.chatter.moderator or ctx.chatter.broadcaster:
            self.activate_tts = not self.activate_tts
            if self.activate_tts:
                await ctx.reply(translation("commands.tts.change.on"))
                return
            await ctx.reply(translation("commands.tts.change.off"))
            return

        if self.activate_tts:
            await ctx.reply(translation("commands.tts.check.on"))
            return
        await ctx.reply(translation("commands.tts.check.off"))

    @commands.command(aliases=["bot"])
    async def version(self, ctx: commands.Context):
        await ctx.reply(
            translation("commands.version"),
            me=True,
        )

    @commands.command()
    @commands.is_moderator()
    async def setgame(self, ctx: commands.Context, *, content: str) -> None:
        game: twitchio.Game | None = await ctx.bot.fetch_game(name=content)
        print(game)
        if game is None:
            await ctx.reply(
                translation("commands.setgame.fail")
            )
        else:
            await ctx.broadcaster.modify_channel(game_id=game.id)

    @commands.command()
    @commands.is_moderator()
    async def settitle(self, ctx: commands.Context, *, content: str) -> None:
        await ctx.broadcaster.modify_channel(title=content)

    # CHANNEL INTERACTIONS

    @commands.Component.listener("event_follow")
    async def event_follow(self, payload: twitchio.ChannelFollow) -> None:
        print(translation("event.follow.print"))
        channel = payload.broadcaster
        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.follow.message").format(payload.user.display_name),
        )

    @commands.Component.listener()
    async def event_subscription(self, payload: twitchio.ChannelSubscribe) -> None:
        print(translation("event.new_sub.print"))
        channel = payload.broadcaster
        sub_tier = self.format_tier(payload.tier)
        if not payload.gift:
            await channel.send_message(
                sender=BOT_ID,
                message=translation("event.new_sub.message").format(payload.user.display_name, sub_tier),
            )

    @commands.Component.listener()
    async def event_subscription_message(
        self, payload: twitchio.ChannelSubscriptionMessage
    ) -> None:
        print(translation("event.resub.print"))
        channel = payload.broadcaster
        sub_tier = self.format_tier(payload.tier)
        streak = ""
        if payload.streak_months is not None and payload.streak_months > 0:
            streak = translation("event.resub.streak").format(payload.streak_months)
        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.resub.message").format(payload.user.display_name, sub_tier, payload.months, streak),
        )

    @commands.Component.listener("event_subscription_gift")
    async def event_subscription_gift(
        self, payload: twitchio.ChannelSubscriptionGift
    ) -> None:
        print(translation("event.sub_gift.print"))
        channel = payload.broadcaster
        sub_tier = self.format_tier(payload.tier, True)
        display_name = ""
        if type(payload.user.display_name) is str:  # type: ignore
            display_name = payload.user.display_name  # type: ignore
        if payload.anonymous:
            await channel.send_message(
                sender=BOT_ID,
                message=translation("event.sub_gift.message.anonymous").format(payload.total, sub_tier, payload.cumulative_total),
            )
        else:
            await channel.send_message(
                sender=BOT_ID,
                message=translation("event.sub_gift.message.regular").format(display_name, payload.total, sub_tier, payload.cumulative_total),
            )

    @commands.Component.listener("event_cheer")
    async def event_cheer(self, payload: twitchio.ChannelCheer) -> None:
        print(translation("event.cheer.print"))
        channel = payload.broadcaster
        display_name = translation("event.cheer.anonymous")
        if not payload.anonymous:
            display_name = payload.user.display_name
        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.cheer.message").format(display_name, payload.bits),
        )

    @commands.Component.listener("event_prediction_begin")
    async def event_prediction_begin(
        self, payload: twitchio.ChannelPredictionBegin
    ) -> None:
        print(translation("event.prediction.begin.print"))
        channel = payload.broadcaster
        prediction_title = payload.title
        prediction_outcomes = payload.outcomes
        prediction_outcomes_str = prediction_outcomes.pop(0).title
        for outcome in range(1, len(prediction_outcomes)):
            prediction_outcomes_str += f", {prediction_outcomes[outcome].title}"
        prediction_locks = payload.locks_at
        diff = prediction_locks - datetime.now()
        secs = int(diff.total_seconds())
        mins = int(secs // 60)
        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.prediction.begin.message").format(prediction_title, prediction_outcomes_str, mins),
        )

    @commands.Component.listener("event_prediction_progress")
    async def event_prediction_progress(
        self, payload: twitchio.ChannelPredictionProgress
    ) -> None:
        print(translation("event.prediction.progress.print"))
        channel = payload.broadcaster
        prediction_title = payload.title
        prediction_outcomes = payload.outcomes
        prediction_outcomes_str = prediction_outcomes.pop(0).title
        for outcome in range(1, len(prediction_outcomes)):
            prediction_outcomes_str += f", {prediction_outcomes[outcome].title}"
        prediction_locks = payload.locks_at
        diff = prediction_locks - datetime.now()
        secs = int(diff.total_seconds())
        mins = int(secs // 60)
        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.prediction.progress.message").format(mins),
        )

    @commands.Component.listener("event_prediction_lock")
    async def event_prediction_lock(
        self, payload: twitchio.ChannelPredictionLock
    ) -> None:
        print(translation("event.prediction.lock.print"))
        channel = payload.broadcaster
        prediction_title = payload.title
        prediction_outcomes = payload.outcomes
        prediction_total = 0
        prediction_highest = prediction_outcomes[0]
        if prediction_highest.channel_points is not None:
            prediction_total += prediction_highest.channel_points
        prediction_outcomes_str = f"{prediction_outcomes.pop(0).title}"
        for outcome in prediction_outcomes:
            if outcome.channel_points is not None:
                prediction_total += outcome.channel_points
                prediction_outcomes_str += f", {outcome.title}"
                if (
                    prediction_highest.channel_points is not None
                    and outcome.channel_points > prediction_highest.channel_points
                ):
                    prediction_highest = outcome
        channel_points = 0
        if prediction_highest.channel_points is not None:
            channel_points = prediction_highest.channel_points

        if prediction_total == 0:
            await channel.end_prediction(id=payload.id, status="CANCELED")

        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.prediction.lock.message").format(prediction_title, prediction_highest.title, round(channel_points / prediction_total * 100, 2), prediction_outcomes_str),
        )

    @commands.Component.listener("event_prediction_end")
    async def event_prediction_end(
        self, payload: twitchio.ChannelPredictionEnd
    ) -> None:
        print(translation("event.prediction.end.print"))
        channel = payload.broadcaster
        prediction_title = payload.title
        if payload.status == "canceled":
            await channel.send_message(
                sender=BOT_ID,
                message=translation("event.prediction.end.message.cancelled").format(prediction_title),
            )
        else:
            prediction_winner = payload.winning_outcome
            prediction_outcomes = payload.outcomes
            prediction_total = 0
            prediction_highest = prediction_outcomes[0]
            if prediction_highest.channel_points is not None:
                prediction_total += prediction_highest.channel_points
            prediction_outcomes_str = f"{prediction_outcomes.pop(0).title}"
            for outcome in prediction_outcomes:
                if outcome.channel_points is not None:
                    prediction_total += outcome.channel_points
                    prediction_outcomes_str += f", {outcome.title}"
                    if (
                        prediction_winner.channel_points is not None  # type: ignore
                        and outcome.channel_points > prediction_winner.channel_points  # type: ignore
                    ):  # type: ignore
                        prediction_highest = outcome
            channel_points = 0
            if prediction_winner.channel_points is not None:  # type: ignore
                channel_points = prediction_winner.channel_points  # type: ignore
            await channel.send_message(
                sender=BOT_ID,
                message=translation("event.prediction.end.message.resolved").format(prediction_title, prediction_winner.title, round(channel_points / prediction_total * 100, 2), prediction_total, len(prediction_winner.users), prediction_outcomes_str),
            )

    @commands.Component.listener("event_poll_begin")
    async def event_poll_begin(self, payload: twitchio.ChannelPollBegin) -> None:
        print(translation("event.poll.begin.print"))
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
            message=translation("event.poll.begin.message").format(poll_title, poll_choices_str, mins),
        )

    @commands.Component.listener("event_poll_progress")
    async def event_poll_progress(self, payload: twitchio.ChannelPollProgress) -> None:
        print(translation("event.poll.progress.print"))
        channel = payload.broadcaster
        poll_title = payload.title
        poll_choices = payload.choices
        poll_end = payload.ends_at
        diff = poll_end - datetime.now()
        secs = int(diff.total_seconds())
        mins = int(secs // 60)
        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.poll.progress.print").format(poll_title, mins),
        )

    @commands.Component.listener("event_poll_end")
    async def event_poll_end(self, payload: twitchio.ChannelPollEnd) -> None:
        print(translation("event.poll.end.print"))
        channel = payload.broadcaster
        poll_title = payload.title
        poll_choices = payload.choices
        poll_winner = poll_choices[0]
        poll_choices_str = f"{poll_choices.pop(0).title}"
        for choice in poll_choices:
            poll_choices_str += f", {choice.title}"
            if (
                choice.votes is not None
                and poll_winner.votes is not None
                and choice.votes > poll_winner.votes
            ):
                poll_winner = choice
        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.poll.end.message").format(poll_winner.title, poll_title, poll_winner.votes, poll_choices_str),
        )

    @commands.Component.listener("event_stream_online")
    async def event_stream_online(self, payload: twitchio.StreamOnline) -> None:
        print(translation("event.stream.online.print"))
        # Event dispatched when a user goes live from the subscription we made above...

        # Keep in mind we are assuming this is for ourselves
        # others may not want your bot randomly sending messages...
        self.start_time = datetime.now()
        await payload.broadcaster.send_message(
            sender=BOT_ID,
            message=translation("event.stream.online.message").format(payload.broadcaster.display_name),
        )

    @commands.Component.listener("event_stream_offline")
    async def event_stream_offline(self, payload: twitchio.StreamOffline) -> None:
        print(translation("event.stream.offline.print"))
        # Event dispatched when a user goes live from the subscription we made above...

        # Keep in mind we are assuming this is for ourselves
        # others may not want your bot randomly sending messages...
        await payload.broadcaster.send_message(
            sender=BOT_ID,
            message=translation("event.stream.offline.message"),
        )

    @commands.Component.listener("event_hype_train")
    async def event_hype_train_begin(self, payload: twitchio.HypeTrainBegin) -> None:
        print(translation("event.hype_train.begin.print"))
        channel = payload.broadcaster
        train_level = payload.level
        self.hype_train_level = train_level
        shared_text = ""
        is_shared = payload.shared_train
        if is_shared:
            shared_text = translation("event.hype_train.shared")
        train_goal = payload.goal
        train_progress = payload.progress
        self.hype_train_level_complete = round(
            train_progress / train_goal * 100, 2
        )  # A percentage of level completion
        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.hype_train.begin.message").format(shared_text, translation(f"event.hype_train.type.{payload.type}"), self.hype_train_level_complete, train_level),
        )

    @commands.Component.listener("event_hype_train_progress")
    async def event_hype_train_progress(
        self, payload: twitchio.HypeTrainProgress
    ) -> None:
        print(translation("event.hype_train.progress.print"))
        channel = payload.broadcaster
        train_level = payload.level
        if train_level > self.hype_train_level:
            self.hype_train_level = train_level
            shared_text = ""
            is_shared = payload.shared_train
            if is_shared:
                shared_text = translation("event.hype_train.shared")
            train_goal = payload.goal
            train_progress = payload.progress
            self.hype_train_level_complete = round(
                train_progress / train_goal * 100, 2
            )  # A percentage of level completion
            await channel.send_message(
                sender=BOT_ID,
                message=translation("event.hype_train.start.message").format(shared_text, translation(f"event.hype_train.type.{payload.type}"), self.hype_train_level_complete, train_level),
            )

    @commands.Component.listener("event_hype_train_end")
    async def event_hype_train_end(self, payload: twitchio.HypeTrainEnd) -> None:
        print(translation("event.hype_train.end.print"))
        channel = payload.broadcaster
        train_level = payload.level
        self.hype_train_level = -1
        shared_text = ""
        is_shared = payload.shared_train
        if is_shared:
            shared_text = translation("event.hype_train.shared")
        special_text = translation(f"event.hype_train.type.{payload.type}")
        train_countdown_until = payload.cooldown_until
        diff = (
            datetime.fromtimestamp(train_countdown_until.timestamp()) - datetime.now()
        )
        secs = int(diff.total_seconds())
        mins = int(secs // 60)
        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.hype_train.end.message").format(shared_text, translation(f"event.hype_train.type.{payload.type}"), self.hype_train_level_complete, train_level, mins),
        )

    @commands.Component.listener("event_shared_chat_begin")
    async def event_shared_chat_begin(
        self, payload: twitchio.SharedChatSessionBegin
    ) -> None:
        print(translation("event.shared_chat.begin.print"))
        channel = payload.broadcaster
        host = payload.host
        participants = payload.participants
        participants_str = ""
        for participant in participants:
            if participant.id != host.id:
                if participant not in self.shared_chat_users:
                    self.shared_chat_users.append(participant)
                participants_str += (
                    f"{'' if len(participants_str) == 0 else ', '}{participant.display_name}"  # type: ignore
                )
        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.shared_chat.begin.message").format(host.display_name, participants_str),
        )

    @commands.Component.listener("event_shared_chat_update")
    async def event_shared_chat_update(
        self, payload: twitchio.SharedChatSessionUpdate
    ) -> None:
        print(translation("event.shared_chat.update.print"))
        channel = payload.broadcaster
        host = payload.host
        participants = payload.participants
        participants_str = ""
        diff = len(self.shared_chat_users) - (len(participants) - 1)
        if diff < 0:  # If a user was added
            for participant in participants:
                if participant.id != host.id:
                    if participant not in self.shared_chat_users:
                        self.shared_chat_users.append(participant)
                participants_str += (
                    f"{'' if len(participants_str) == 0 else ', '}{participant.display_name}"  # type: ignore
                )
            await channel.send_message(
                sender=BOT_ID,
                message=translation("event.shared_chat.update.message.added").format(host.display_name, abs(diff), participants_str),
            )
        else:  # If a user was removed
            self.shared_chat_users = []
            for participant in participants:
                if participant.id != host.id:
                    self.shared_chat_users.append(participant)
                participants_str += (
                    f"{'' if len(participants_str) == 0 else ', '}{participant.display_name}"  # type: ignore
                )
            await channel.send_message(
                sender=BOT_ID,
                message=translation("event.shared_chat.update.message.removed").format(host.display_name, diff, participants_str),
            )

    @commands.Component.listener("event_shared_chat_end")
    async def event_shared_chat_end(
        self, payload: twitchio.SharedChatSessionEnd
    ) -> None:
        print(translation("event.shared_chat.end.print"))
        channel = payload.broadcaster
        host = payload.host
        self.shared_chat_users = []
        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.shared_chat.end.message").format(host.display_name),
        )

    @commands.Component.listener("event_goal_begin")
    async def event_goal_begin(self, payload: twitchio.GoalBegin) -> None:
        print(translation("event.goal.begin.print"))
        channel = payload.broadcaster
        goal_name = payload.description
        goal_amount = payload.current_amount
        goal_end_amount = payload.target_amount
        goal_type = payload.type
        goal_type_str = translation("event.goal.type.follow")
        if goal_type in [
            "subscription_count",
            "new_subscription",
            "new_subscription_count",
        ]:
            goal_type_str = translation("event.goal.type.subscription")
        elif goal_type in ["new_bit", "new_cheer"]:
            goal_type_str = translation("event.goal.type.cheer")
        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.goal.begin.message").format(goal_type_str, goal_name, goal_amount, goal_end_amount),
        )

    @commands.Component.listener("event_goal_progress")
    async def event_goal_progress(self, payload: twitchio.GoalProgress) -> None:
        print(translation("event.goal.progress.print"))
        channel = payload.broadcaster
        goal_name = payload.description
        goal_amount = payload.current_amount
        goal_end_amount = payload.target_amount
        goal_type = payload.type
        goal_type_str = translation("event.goal.type.follow")
        if goal_type in [
            "subscription_count",
            "new_subscription",
            "new_subscription_count",
        ]:
            goal_type_str = translation("event.goal.type.subscription")
        elif goal_type in ["new_bit", "new_cheer"]:
            goal_type_str = translation("event.goal.type.cheer")
        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.goal.progress.message").format(goal_type_str, goal_name, goal_amount, goal_end_amount),
        )

    @commands.Component.listener("event_goal_end")
    async def event_goal_end(self, payload: twitchio.GoalEnd) -> None:
        print(translation("event.goal.end.print"))
        channel = payload.broadcaster
        goal_name = payload.description
        goal_end_amount = payload.target_amount
        goal_type = payload.type
        goal_type_str = translation("event.goal.type.follow")
        if goal_type in [
            "subscription_count",
            "new_subscription",
            "new_subscription_count",
        ]:
            goal_type_str = translation("event.goal.type.subscription")
        elif goal_type in ["new_bit", "new_cheer"]:
            goal_type_str = translation("event.goal.type.cheer")
        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.goal.end.message").format(goal_name, goal_end_amount, goal_type_str),
        )

    @commands.Component.listener("event_raid")
    async def event_raid(self, payload: twitchio.ChannelRaid) -> None:
        print(translation("event.raid.print"))
        channel = payload.to_broadcaster
        raider = payload.from_broadcaster
        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.raid.message").format(raider.display_name, payload.viewer_count),
        )
        await channel.send_shoutout(
            to_broadcaster=raider,
            moderator=BOT_ID,
        )

    @commands.Component.listener("event_channel_update")
    async def event_channel_update(self, payload: twitchio.ChannelUpdate) -> None:
        print(translation("event.channel_update.print"))
        channel = payload.broadcaster
        category = payload.category_name
        title = payload.title
        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.channel_update.message").format(title, category),
        )

    @commands.Component.listener("event_shoutout_create")
    async def event_shoutout_create(self, payload: twitchio.ShoutoutCreate) -> None:
        print(translation("event.shoutout.create.print"))
        channel = payload.broadcaster
        shoutout_receiver = payload.to_broadcaster
        channel_info = await shoutout_receiver.fetch_channel_info()
        game = await channel_info.fetch_game()
        if game is not None:
            await channel.send_message(
                sender=BOT_ID,
                message=translation("event.shoutout.create.message.with_game").format(shoutout_receiver.display_name, game.name),
            )
            return
        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.shoutout.create.message.without_game").format(shoutout_receiver.display_name, payload.viewer_count),
        )

    @commands.Component.listener("event_shoutout_receive")
    async def event_shoutout_receive(self, payload: twitchio.ShoutoutReceive) -> None:
        print(translation("event.shoutout.receive.print"))
        channel = payload.broadcaster
        shoutout_sender = payload.from_broadcaster
        channel_info = await shoutout_sender.fetch_channel_info()
        game = await channel_info.fetch_game()
        if game is not None:
            await channel.send_message(
                sender=BOT_ID,
                message=translation("event.shoutout.receive.message.with_game").format(shoutout_sender.display_name, game.name),
            )
            return
        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.shoutout.receive.message.without_game").format(shoutout_sender.display_name, payload.viewer_count),
        )

    @commands.Component.listener("event_automatic_redemption_add")
    async def event_automatic_redemption_add(
        self, payload: twitchio.ChannelPointsAutoRedeemAdd
    ) -> None:
        print(translation("event.auto_channel_points.print"))
        channel = payload.broadcaster  # The channel it happened on
        user = payload.user  # The user who redeemed this reward
        reward = payload.reward  # The reward object
        reward_type = reward.type # The type of reward
        reward_cost = (
            reward.channel_points
        )  # The cost of the reward, in channel points (NOT BITS)
        reward_id = payload.id  # The reward ID of this reward
        reward_redeemed_at = payload.redeemed_at  # When the reward was redeemed

        emote_unlocked = reward.emote  # The emote unlocked from reward_type in "reward_type in ['random_sub_emote_unlock', 'chosen_sub_emote_unlock']"
        user_input = payload.user_input

        chat_message = payload.text

        # While most attributes won't be used, it's always good to have them down for later.

        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.auto_channel_points.message").format(user.display_name, translation(f"event.auto_channel_points.type.{reward_type}"), reward_cost),
        )

    @commands.Component.listener("event_custom_redemption_add")
    async def event_custom_redemption_add(
        self, payload: twitchio.ChannelPointsRedemptionAdd
    ) -> None:
        print(translation("event.channel_points.print"))
        channel = payload.broadcaster  # The channel it happened on
        user = payload.user  # The user who redeemed this reward
        reward = payload.reward  # The reward object
        reward_color = reward.colour  # The color background of the reward
        reward_cooldown = (
            reward.cooldown_until
        )  # The time until the reward can be redeemed again
        reward_cost = reward.cost  # The cost of the reward, in channel points
        reward_redeem_count = reward.current_stream_redeems  # How many times this reward has been redeemed (based on "reward_max_per_stream"") -> None if the streamer isn't live or no limit is set
        reward_defaut_image = reward.default_image  # A dictionnary of the default image
        reward_enabled = reward.enabled  # If this reward is visible to the viewers
        reward_global_cooldown = (
            reward.global_cooldown
        )  # The cooldown time before the reward can be redeemed again
        reward_id = reward.id  # The reward ID of this reward
        reward_title = reward.title  # The title of this reward
        reward_is_instock = (
            reward.in_stock
        )  # If the reward is in stock, False if the viewers can't see it
        reward_need_input = (
            reward.input_required
        )  # Whether an input is required or not for this reward
        reward_max_per_stream = reward.max_per_stream  # How many times this reward can be redeemed -> None if this reward doesn't have a limit
        reward_max_per_user_per_stream = reward.max_per_user_per_stream  # How many times a user can redeem this reward per stream -> None if this reward doesn't have a limit
        reward_is_paused = (
            reward.paused
        )  # If the reward is paused, True if the viewers can't see it
        reward_prompt = reward.prompt  # The description of the reward
        reward_redeemed_at = payload.redeemed_at  # When the reward was redeemed
        reward_status = payload.status  # The reward status (defaults to 'unfulfilled')

        user_input = (
            payload.user_input
        )  # The input provided by the user, "" if none was (/ was needed)

        # While most attributes won't be used, it's always good to have them down for later.

        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.channel_points.message").format(user.display_name, reward_title, reward_cost),
        )

    @commands.Component.listener("event_custom_power_up_redemption_add")
    async def event_custom_power_up_redemption_add(self, payload: twitchio.CustomPowerupRedemptionAdd) -> None:
      print(translation("event.auto_powerups.print"))
      channel = payload.broadcaster  # The channel it happened on
      user = payload.user  # The user who redeemed this powerup
      powerup = payload.custom_powerup  # The powerup object
      powerup_cost = powerup.bits  # The cost of the powerup, in channel points
      powerup_id = powerup.id  # The powerup ID of this powerup
      powerup_title = powerup.title  # The title of this powerup
      powerup_prompt = powerup.prompt  # The description of the powerup
      powerup_redeemed_at = payload.redeemed_at  # When the powerup was redeemed
      powerup_status = payload.status  # The powerup status (defaults to 'unfulfilled')

      user_input = (
          payload.user_input
      )  # The input provided by the user, "" if none was given /needed

      # While most attributes won't be used, it's always good to have them down for later.

      await channel.send_message(
          sender=BOT_ID,
          message=translation("event.powerups.message").format(user.display_name, powerup_title, powerup_cost),
      )

    @commands.Component.listener("event_ad_break")
    async def event_ad_break(self, payload: twitchio.ChannelAdBreakBegin) -> None:
        print(translation("event.ad_break.print"))
        channel = payload.broadcaster
        started_at = payload.started_at
        duration = payload.duration

        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.ad_break.message").format(self.format_time_since(datetime.fromtimestamp(started_at.timestamp() + duration), datetime.now())),
        )

    @commands.Component.listener("event_chat_notification")
    async def event_chat_notification(self, payload: twitchio.ChatNotification) -> None:
        print(translation("event.chat_notification.print"))
        channel = payload.broadcaster
        user = payload.chatter
        type = payload.notice_type

        if type == "watch_streak" and payload.watch_streak is not None:
            streak_amount = payload.watch_streak.streak
            channel_points_awarded = payload.watch_streak.points

            await channel.send_message(
                sender=BOT_ID,
                message=translation("event.chat_notification.watch_streak.message").format(user.display_name, streak_amount),
            )


async def setup_database(
    db: asqlite.Pool,
) -> tuple[list[tuple[str, str]], list[eventsub.SubscriptionPayload]]:
    # Create our token table, if it doesn't exist..
    query = """CREATE TABLE IF NOT EXISTS tokens(user_id TEXT PRIMARY KEY, token TEXT NOT NULL, refresh TEXT NOT NULL)"""
    async with db.acquire() as connection:
        await connection.execute(query)

        # Fetch any existing tokens...
        rows: list[sqlite3.Row] = await connection.fetchall("""SELECT * from tokens""")

        tokens: list[tuple[str, str]] = []
        subs: list[eventsub.SubscriptionPayload] = []

        for row in rows:
            tokens.append((row["token"], row["refresh"]))

            if row["user_id"] == BOT_ID:
                continue

            subs.extend(
                [
                    eventsub.ChatMessageSubscription(
                        broadcaster_user_id=OWNER_ID, user_id=BOT_ID
                    ),
                    eventsub.ChannelFollowSubscription(
                        broadcaster_user_id=OWNER_ID, moderator_user_id=BOT_ID
                    ),
                    eventsub.ShoutoutCreateSubscription(
                        broadcaster_user_id=OWNER_ID, moderator_user_id=BOT_ID
                    ),
                    eventsub.ShoutoutReceiveSubscription(
                        broadcaster_user_id=OWNER_ID, moderator_user_id=BOT_ID
                    ),
                    eventsub.StreamOnlineSubscription(broadcaster_user_id=OWNER_ID),
                    eventsub.StreamOfflineSubscription(broadcaster_user_id=OWNER_ID),
                    eventsub.ChannelRaidSubscription(to_broadcaster_user_id=OWNER_ID),
                    eventsub.ChannelUpdateSubscription(broadcaster_user_id=OWNER_ID),
                    eventsub.SharedChatSessionBeginSubscription(
                        broadcaster_user_id=OWNER_ID
                    ),
                    eventsub.SharedChatSessionUpdateSubscription(
                        broadcaster_user_id=OWNER_ID
                    ),
                    eventsub.SharedChatSessionEndSubscription(
                        broadcaster_user_id=OWNER_ID
                    ),
                    eventsub.ChatNotificationSubscription(
                      broadcaster_user_id=OWNER_ID, user_id=BOT_ID
                    )
                ]
            )

            if HAS_ONBOARDED:
                subs.extend(
                    [
                        eventsub.ChannelSubscribeSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
                        eventsub.ChannelSubscribeMessageSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
                        eventsub.ChannelSubscriptionGiftSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
                        eventsub.ChannelCheerSubscription(broadcaster_user_id=OWNER_ID),
                        eventsub.ChannelPredictionBeginSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
                        eventsub.ChannelPredictionLockSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
                        eventsub.ChannelPredictionEndSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
                        eventsub.ChannelPollBeginSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
                        eventsub.ChannelPollEndSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
                        eventsub.ChannelCheerSubscription(broadcaster_user_id=OWNER_ID),
                        eventsub.ChannelPredictionBeginSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
                        eventsub.ChannelPredictionProgressSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
                        eventsub.ChannelPredictionLockSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
                        eventsub.ChannelPredictionEndSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
                        eventsub.ChannelPollBeginSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
                        eventsub.ChannelPollProgressSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
                        eventsub.ChannelPollEndSubscription(broadcaster_user_id=OWNER_ID),
                        eventsub.HypeTrainBeginSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
                        eventsub.HypeTrainProgressSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
                        eventsub.HypeTrainEndSubscription(broadcaster_user_id=OWNER_ID),
                        eventsub.GoalBeginSubscription(broadcaster_user_id=OWNER_ID),
                        eventsub.GoalProgressSubscription(broadcaster_user_id=OWNER_ID),
                        eventsub.GoalEndSubscription(broadcaster_user_id=OWNER_ID),
                        eventsub.ChannelPointsAutoRedeemSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
                        eventsub.ChannelPointsRedeemAddSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
                        eventsub.AdBreakBeginSubscription(broadcaster_user_id=OWNER_ID),
                    ]
                )

    return tokens, subs


def main() -> None:
    twitchio.utils.setup_logging(level=logging.INFO)

    async def runner() -> None:
        async with asqlite.create_pool("tokens.db") as tdb:
            tokens, subs = await setup_database(tdb)
            async with Bot(token_database=tdb, subs=subs, owner=OWNER_ID) as bot:
                for pair in tokens:
                    await bot.add_token(*pair)
                await bot.start(load_tokens=False)

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        LOGGER.warning(translation("logger.warning.keyboard_interrupt"))


if __name__ == "__main__":
    main()
