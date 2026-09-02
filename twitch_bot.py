import asyncio
import json
import logging
import math
import random
import sqlite3
import emoji
from datetime import datetime, timezone
from threading import Timer

import asqlite
import requests
import twitchio
from twitchio import eventsub, user, web
from twitchio.ext import commands

import mcci
import mongo
import socket_client
from audio_player import AudioManager
from keys import (
    AZURE_TTS_VOICE,
    BOT_ID,
    HAS_ONBOARDED,
    LANG,
    MONGODB_URL,
    OWNER_ID,
    TWITCH_BOT_CLIENT_ID,
    TWITCH_BOT_CLIENT_SECRET,
    HTTP_PORT_MAIN
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

        adapter = web.AiohttpAdapter(port=HTTP_PORT_MAIN)

        super().__init__(
            client_id=TWITCH_BOT_CLIENT_ID,
            client_secret=TWITCH_BOT_CLIENT_SECRET,
            bot_id=BOT_ID,
            owner_id=OWNER_ID,
            prefix="!",
            subscriptions=subs,
            force_subscribe=True,
            adapter=adapter
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

        # Subscribe and listen to when a shoutout is sent in chat..
        subscriptions.append(
            eventsub.ShoutoutCreateSubscription(
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
            eventsub.SharedChatSessionBeginSubscription(broadcaster_user_id=payload.user_id)
        )
        subscriptions.append(
            eventsub.SharedChatSessionUpdateSubscription(broadcaster_user_id=payload.user_id)
        )
        subscriptions.append(
            eventsub.SharedChatSessionEndSubscription(broadcaster_user_id=payload.user_id)
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

            # Subscribe and listen to when prediction starts, locks or ends..
            subscriptions.append(
                eventsub.ChannelPredictionBeginSubscription(
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
                eventsub.AdBreakBeginSubscription(broadcaster_user_id=payload.user_id),
            )

            subscriptions.append(
              eventsub.ChatNotificationSubscription(broadcaster_user_id=payload.user_id, user_id=BOT_ID)
            )

            subscriptions.append(
              eventsub.CustomPowerupRedeemAddSubscription(broadcaster_user_id=payload.user_id)
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

        self.socket = socket_client.SocketClient()

        self.getAccessToken()

        self.emotes_dict: dict[
            str, dict[str, str]
        ] = {  # Format : {"platform": {"emote_name": "emote_url"}}
            "7TV":  # 7TV Emotes
            self.get7TVEmotes(OWNER_ID),
            "BTTV":  # BTTV Emotes
            self.getBTTVEmotes(OWNER_ID),
            "FFZ":  # FFZ Emotes
            self.getFFZEmotes(OWNER_ID),
            "Twitch": self.getTwitchEmotes(OWNER_ID),
        }
        self.emotes_list = self.getEmoteList()

        self.badges_dict: dict[str, dict[str, str]] = self.getTwitchBadges(OWNER_ID)

        self.chat_emotes_combo: list = [
            "",
            0,
        ]  # Holds a list like : [str("Emote Name"), int(number of instance of this emote in a row)]

        self.shared_chat_users: list[user.PartialUser] = []
        self.hype_train_level: int = -1
        self.hype_train_level_complete: float = 0
        self.start_time: datetime = datetime.now()
        self.lurkers: list[str] = []
        self.activate_tts: bool = True
        self.tts_queue: list[str] = []
        self.alerts_queue: list[tuple[str, dict]] = []
        self.currently_playing_tts: bool = False
        self.message_sent: int = 0
        self.db: mongo.Database = mongo.Database(MONGODB_URL)
        self.streamer = None
        self.colors: dict[str, str] = {}
        # self.db.update(
        #    "twitch_api",
        #    "messages",
        #    {"user_id": OWNER_ID},
        #    {"$set": {"user_id": OWNER_ID, "messages": []}},
        # )

        self.socket.send("start", {"Bot": True})

    async def getStreamerUser(self):
        self.streamer = await self.bot.fetch_user(id=OWNER_ID)

    def getBTTVEmotes(self, broadcaster_id: str) -> dict[str, str]:
        emotes: dict[str, str] = {}
        req = requests.get(
            f"https://api.betterttv.net/3/cached/users/twitch/{broadcaster_id}"
        )
        if not req.ok:
            return emotes
        res = req.json()

        emotes_list = res["sharedEmotes"]
        for emote in emotes_list:
            emotes[emote["code"]] = (
                "https://cdn.betterttv.net/emote/" + emote["id"] + "/2x"
            )
        return emotes

    def get7TVEmotes(self, broadcaster_id: str) -> dict[str, str]:
        emotes: dict[str, str] = {}

        req = requests.get("https://api.7tv.app/v3/emote-sets/global")
        res = req.json()
        for emote in res["emotes"]:
            emotes[emote["data"]["name"]] = (
                "https:"
                + emote["data"]["host"]["url"]
                + "/"
                + emote["data"]["host"]["files"][0]["name"]
            )

        req = requests.get(f"https://api.7tv.app/v3/users/twitch/{broadcaster_id}")
        if req.ok:
            res = req.json()
            emote_set = res["emote_set_id"]

            req = requests.get(f"https://api.7tv.app/v3/emote-sets/{emote_set}")
            res = req.json()
            for emote in res["emotes"]:
                emotes[emote["data"]["name"]] = (
                    "https:"
                    + emote["data"]["host"]["url"]
                    + "/"
                    + emote["data"]["host"]["files"][0]["name"]
                )
        return emotes

    def getFFZEmotes(self, broadcaster_id: str) -> dict[str, str]:
        emotes: dict[str, str] = {}

        req = requests.get(f"https://api.frankerfacez.com/v1/room/id/{broadcaster_id}")

        if not req.ok:
            return emotes

        res = req.json()
        emoteSet = res["room"]["set"]
        currentSet = res["sets"][str(emoteSet)]
        for emote in currentSet["emoticons"]:
            emotes[emote["name"]] = emote["urls"]["2"]
        return emotes

    def getAccessToken(self):
        params = {
            "client_id": TWITCH_BOT_CLIENT_ID,
            "client_secret": TWITCH_BOT_CLIENT_SECRET,
            "grant_type": "client_credentials",
        }

        req = requests.post("https://id.twitch.tv/oauth2/token", params=params)

        if not req.ok:
            LOGGER.warning(translation("logger.warning.fail_token_fetch"))
            return

        res = req.json()
        self.access_token = res["access_token"]

    def getTwitchEmotes(self, broadcaster_id: str) -> dict[str, str]:
        emotes: dict[str, str] = {}

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Client-Id": TWITCH_BOT_CLIENT_ID,
        }

        req = requests.get(
            f"https://api.twitch.tv/helix/chat/emotes?broadcaster_id={broadcaster_id}",
            headers=headers,
        )

        if not req.ok:
            return emotes

        res = req.json()
        for emote in res["data"]:
            link = emote["images"]["url_2x"]
            if "animated" in emote["format"]:
                link = link.replace("/static/", "/animated/")
            emotes[emote["name"]] = link

        req = requests.get(
            "https://api.twitch.tv/helix/chat/emotes/global", headers=headers
        )

        if not req.ok:
            return emotes

        res = req.json()
        for emote in res["data"]:
            link = emote["images"]["url_2x"]
            if "animated" in emote["format"]:
                link = link.replace("/static/", "/animated/")
            link = link.replace("/light/", "/dark/")
            emotes[emote["name"]] = link

        return emotes

    def getTwitchBadges(self, broadcaster_id: str) -> dict[str, dict[str, str]]:
        badges = {}

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Client-Id": TWITCH_BOT_CLIENT_ID,
        }

        req = requests.get(
            "https://api.twitch.tv/helix/chat/badges/global",
            headers=headers,
        )

        if not req.ok:
            return badges

        res = req.json()

        for badge in res["data"]:
            badge_comp = {}
            for version in badge["versions"]:
                badge_comp[version["id"]] = version["image_url_1x"][:-2]
            badges[badge["set_id"]] = badge_comp

        req = requests.get(
            f"https://api.twitch.tv/helix/chat/badges?broadcaster_id={broadcaster_id}",
            headers=headers,
        )

        if not req.ok:
            return badges

        res = req.json()

        for badge in res["data"]:
            badge_comp = {}
            for version in badge["versions"]:
                badge_comp[version["id"]] = version["image_url_1x"][:-2]
            badges[badge["set_id"]] = badge_comp

        return badges

    def getChatterColor(self, user_id: str) -> str:

        if user_id in self.colors.keys():
            return self.colors[user_id]

        color: str = "#%06x" % random.randint(0, 0xFFFFFF)

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Client-Id": TWITCH_BOT_CLIENT_ID,
        }

        params = {"user_id": user_id}

        req = requests.get(
            "https://api.twitch.tv/helix/chat/color", headers=headers, params=params
        )

        if not req.ok:
            self.color[user_id] = color
            return color

        res = req.json()

        for user in res["data"]:
            color = user["color"] if user["color"] != "" else color
            self.color[user_id] = color
            return color

        self.color[user_id] = color
        return color

    def getEmoteList(self) -> list[str]:
        emotes_list: list[str] = []
        for emotes in self.emotes_dict.values():
            for emote_text in emotes.keys():
                emotes_list.append(emote_text)

        return emotes_list

    def roundToNNearest(self, time: int, n: int):
        time = round(time/n)
        return time*n

    def treat_message(self, message: str, cheer: bool = False) -> str:
        final_message = ""
        if not cheer:
            if "Cheer" in message:  # If the message is being treated as a non cheer message and has "Cheer" in it, just don't read it
                return ""
        messageList = message.split()
        for word in messageList:
            word = word.replace("_", " ")
            if ("🫡" == word) or ("o7" == word):
                final_message += "o 7 "
            elif "D:" == word:
                final_message += "D face "
            elif "<3" == word:
                final_message += "love "
            elif "</3" == word:
                final_message += "don't love "
            elif "https" in word:
                pass
            elif "@" in word: #Don't say mentions out loud
                pass
            elif "Cheer" in word:  # We don't want it to say the bits amount!
                pass
            elif emoji.is_emoji(word):
                pass
            else:
                final_message += word + " "

        return final_message[:-1]

    def format_tier(self, tier: str, is_gift: bool = False) -> str:
        if not is_gift:
            if tier == "1000":
                return translation("functions.format_tier.tier_1_or_prime")
        return tier[0]

    def message_has_an_emote(self, message: str) -> bool:
        messageList = message.split()
        for word in messageList:
            if word in self.emotes_list:
                return True
        return False

    def message_has_emote(self, message: str, emote: str) -> bool:
        if self.message_has_an_emote(message):
            messageList = message.split()
            return emote in messageList
        return False

    def get_emotes_in_message(self, message: str) -> list[str]:
        emotes: list[str] = []
        if self.message_has_an_emote(message):
            messageList = message.split()
            for word in messageList:
                if word in self.emotes_list:
                    emotes.append(word)
        return emotes

    def get_first_emote_in_message(self, message: str) -> str:
        emotes = self.get_emotes_in_message(message)
        if len(emotes) > 0:
            return emotes[0]
        raise ValueError

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

    def get_month(self, month: int) -> str:
        while month < 0:
            month += 12
        while month > 12:
            month -= 12
        return translation(f"functions.get_month.{month}")

    def get_day(self, week_day: int) -> str:
        while week_day < 0:
            week_day += 7
        while week_day > 7:
            week_day -= 7
        return translation(f"functions.get_day.{week_day}")


    def play_tts_queue(self, has_png: bool) -> None:
        if len(self.alerts_queue) > 0:
            if not self.currently_playing_tts:
                self.currently_playing_tts = True

                if has_png:
                    posY = obswebsockets_manager.get_source_transform(
                        "Bots", "TwitchChat"
                    )["positionY"]

                    while posY > 693:
                        posY -= 1
                        new_transform = {"positionY": posY}
                        obswebsockets_manager.set_source_transform(
                            "Bots", "TwitchChat", new_transform
                        )

                    obswebsockets_manager.set_source_visibility("Bots", "TTS Queue", True)

            alert_message: tuple[str, dict] = self.alerts_queue.pop(0)
            obswebsockets_manager.set_text("TTS Queue", translation("functions.play_tts_queue.tts_queue").format(self.getTTSQueueLength()))

            tts_message = alert_message[0]
            socket_message = alert_message[1]

            # Send Twitch message to Azure to turn into cool audio
            tts_file = tts_manager.text_to_speech(tts_message)
            print(tts_file)

            tts_length = audio_manager.get_audio_length(tts_file)

            socket_message["time_to_live"] = tts_length

            self.socket.send("new_alert_bot", socket_message)

            print(translation("functions.play_tts_queue.playing_message").format(tts_message))
            audio_manager.play_audio(tts_file, sleep_during_playback=False, play_using_music=True)

            wait_end_tts = Timer(tts_length, self.play_tts_queue, [has_png], {}) #Waiting until end of TTS to give it some time to breath
            wait_end_tts.start()

            delete_tts_at_end = Timer(tts_length, audio_manager.delete_file, [tts_file], {}) #Delete TTS at the end
            delete_tts_at_end.start()

        elif len(self.tts_queue) > 0 and self.activate_tts: # If there's TTS in the queue
            if not self.currently_playing_tts:
                self.currently_playing_tts = True

                if has_png:
                    posY = obswebsockets_manager.get_source_transform(
                        "Bots", "TwitchChat"
                    )["positionY"]

                    while posY > 693:
                        posY -= 1
                        new_transform = {"positionY": posY}
                        obswebsockets_manager.set_source_transform(
                            "Bots", "TwitchChat", new_transform
                        )

                    obswebsockets_manager.set_source_visibility("Bots", "TTS Queue", True)

            tts_message = self.tts_queue.pop(0)
            obswebsockets_manager.set_text("TTS Queue", translation("functions.play_tts_queue.tts_queue").format(self.getTTSQueueLength()))

            # Send Twitch message to Azure to turn into cool audio
            tts_file = tts_manager.text_to_speech(tts_message)
            print(tts_file)

            tts_length = audio_manager.get_audio_length(tts_file)

            # self.socket.send("new_tts_bot", {
            #     "tts_loc": tts_file,
            #     "text": tts_message,
            #     "duration": tts_length,
            #     "username": payload.chatter.name
            # })

            print(translation("functions.play_tts_queue.playing_message").format(tts_message))
            audio_manager.play_audio(tts_file, sleep_during_playback=False, play_using_music=True)

            delete_tts_at_end = Timer(tts_length, audio_manager.delete_file, [tts_file], {}) #Delete TTS at the end
            delete_tts_at_end.start()

            wait_end_tts = Timer(tts_length, self.play_tts_queue, [has_png], {}) #Waiting until end of TTS to give it some time to breath
            wait_end_tts.start()

        else:
            if has_png:

                obswebsockets_manager.set_source_visibility("Bots", "TTS Queue", False)

                posY = obswebsockets_manager.get_source_transform(
                    "Bots", "TwitchChat"
                )["positionY"]

                has_tts = False

                while posY < 1080:
                    posY += 1
                    new_transform = {"positionY": posY}
                    obswebsockets_manager.set_source_transform(
                        "Bots", "TwitchChat", new_transform
                    )

                    has_tts = len(self.alerts_queue) > 0
                    if has_tts: #If a TTS pops up when the bot goes down (visually), stop it and play the tts message
                        break

                if has_tts:
                    self.play_tts_queue(has_png)

            self.currently_playing_tts = False

    def getTTSQueueLength(self):
        return len(self.tts_queue) + len(self.alerts_queue)

    def checkHTMLColor(self, text: str) -> str:
        if text[0] != "#":
           return ""

        value = text.split('#')[1]

        if len(value) != 6:
            return ""

        for letter in value:
            ascii_value = ord(letter)

            if 48 <= ascii_value <= 57:
                continue

            elif 65 <= ascii_value <= 70:
                continue

            elif 97 <= ascii_value <= 102:
                continue

            return ""

        return text

    async def ban_user(self, user: twitchio.User | twitchio.Chatter | twitchio.PartialUser, reason: str):
        if self.streamer is not None:
            mods: list[twitchio.PartialUser] = list(await self.streamer.fetch_moderators(first=100))
            if user.id in list(map(lambda mod: mod.id, mods)):
                LOGGER.info(translation("logger.info.filter.bypass"), translation("logger.info.filter.role.moderator"), translation("logger.info.filter.type.ban"))
                return
            vips: list[twitchio.PartialUser] = list(await self.streamer.fetch_vips())
            if user.id in list(map(lambda vip: vip.id, vips)):
                LOGGER.info(translation("logger.info.filter.bypass"), translation("logger.info.filter.role.vip"), translation("logger.info.filter.type.ban"))
                return
            await self.streamer.ban_user(moderator=BOT_ID, user=user, reason=reason)
        else:
            LOGGER.error(translation("logger.error.no_streamer"))

    async def timeout_user(self, user: twitchio.User | twitchio.Chatter | twitchio.PartialUser, reason: str, duration: int):
        if self.streamer is not None:
            mods: list[twitchio.PartialUser] = list(await self.streamer.fetch_moderators(first=100))
            if user.id in list(map(lambda mod: mod.id, mods)):
                LOGGER.info(translation("logger.info.filter.bypass"), translation("logger.info.filter.role.moderator"), translation("logger.info.filter.type.timeout"))
                return
            vips: list[twitchio.PartialUser] = list(await self.streamer.fetch_vips())
            if user.id in list(map(lambda vip: vip.id, vips)):
                LOGGER.info(translation("logger.info.filter.bypass"), translation("logger.info.filter.role.vip"), translation("logger.info.filter.type.timeout"))
                return
            await self.streamer.timeout_user(moderator=BOT_ID, user=user, reason=reason, duration=duration)
        else:
            LOGGER.error(translation("logger.error.no_streamer"))

    @commands.Component.listener("event_message")
    async def event_message_overlay(self, payload: twitchio.ChatMessage) -> None:
        banned_message = False
        command_message = False

        print(
            translation("event.message.print").format(payload.broadcaster.display_name, payload.chatter.display_name, payload.text, translation("event.message.from_broadcast") if payload.source_broadcaster is not None else '')
        )

        if self.streamer is None:
          await self.getStreamerUser()

        if payload.type == "user_intro":
            command_message = True
            twitchChatMessage = translation("event.message.first_time").format(payload.chatter.name, twitchChatMessage)
            return

        elif payload.type != "text": #This is most likely a reward, don't display it
            command_message = True
            return

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
                    await self.timeout_user(user=payload.chatter, duration=120, reason="You used a banned term.")
                    banned_message = True
                    return

        if payload.chatter.name in [
            "fossabot",
            "streamelements",
            "thebot580",
            "nightbot",
        ]:  # Bots
            command_message = True
        elif payload.text[0] == "!" or payload.text[0] == "-":
            command_message = True

        if not (banned_message or command_message):
            # Send new message to server

            twitchChatMessage = ""
            emote_urls = {}
            gif_url = ""

            for messageFragment in payload.fragments:
                if messageFragment.type == "emote":
                    emote_urls[messageFragment.text] = (
                        f"https://static-cdn.jtvnw.net/emoticons/v2/{messageFragment.emote.id}/default/dark/2.0"
                    )
                    twitchChatMessage += messageFragment.text + " "

                    self.emotes_dict["Twitch"][messageFragment.text] = f"https://static-cdn.jtvnw.net/emoticons/v2/{messageFragment.emote.id}/default/dark/2.0"
                    self.emotes_list.append(messageFragment.text)

                elif messageFragment.type == "gif":
                    gif_url = messageFragment.gif.url

                elif messageFragment.type == "text":
                    twitchChatMessage += messageFragment.text + " "

            #Check for 7TV, BTTV & FFZ (& how many emotes there are)
            emotes = self.get_emotes_in_message(twitchChatMessage)

            if len(emotes) + emoji.emoji_count(twitchChatMessage) > 6:
                await self.timeout_user(user=payload.chatter, duration=5, reason=translation("event.message.emote.limit"))
                return

            for emote in emotes:
                for emotes_platform in self.emotes_dict.values():
                    if emote in emotes_platform.keys():
                        emote_urls[emote] = emotes_platform[emote]

            source_broadcaster_pfp_url: str | None = None

            if payload.source_broadcaster is not None:
                source_broadcaster = await payload.source_broadcaster.user()
                source_broadcaster_pfp_url = source_broadcaster.profile_image.url

            color = (
                payload.color.html
                if payload.color is not None
                else "#%06x" % random.randint(0, 0xFFFFFF)
            )

            self.message_sent += 1
            if self.chat_emotes_combo != ["", 0]:  # If we currently have a combo
                if self.message_has_emote(
                    twitchChatMessage, self.chat_emotes_combo[0]
                ):  # If it is the right emote
                    self.chat_emotes_combo[1] += 1
                    print(
                        translation("event.message.emote.add").format(self.chat_emotes_combo[0], payload.chatter.display_name, self.chat_emotes_combo[1])
                    )
                else:
                    print(
                        translation("event.message.emote.end.print").format(self.chat_emotes_combo[1], self.chat_emotes_combo[0], payload.chatter.display_name)
                    )
                    if self.chat_emotes_combo[1] >= 5:
                        await payload.broadcaster.send_message(
                            sender=BOT_ID,
                            message=translation("event.message.emote.end.message").format(self.chat_emotes_combo[1], self.chat_emotes_combo[0]),
                        )
                    self.chat_emotes_combo = [
                        "",
                        0,
                    ]  # Resetting Emotes Combo, because the emote we were looking for wasn't sent
            else:
                if self.message_has_an_emote(
                    twitchChatMessage
                ):  # If the message has at least an emote
                    emote: str = self.get_first_emote_in_message(twitchChatMessage)
                    self.chat_emotes_combo = [emote, 1]
                    print(
                        translation("event.message.emote.start").format(self.chat_emotes_combo[0], payload.chatter.display_name)
                    )

            if not (command_message or banned_message):

                preferences = {
                    "user_id": payload.chatter.id,
                    "user_name": payload.chatter.name,
                    "message_color": "#ffffff",
                    "background_color": "#000000",
                    "message_font": "",
                }

                if self.db.has("twitch_api", "chatter_preferences", {"user_id": payload.chatter.id}):
                    db_preferences = self.db.getData("twitch_api", "chatter_preferences", {"user_id": payload.chatter.id})[0]

                    db_preferences.pop("_id")

                    for key in db_preferences.keys():
                        preferences[key] = db_preferences[key]

                message = {
                    "badges": [
                        self.badges_dict[badge.set_id][badge.id] for badge in payload.badges
                    ],
                    "reply": {
                        "id": payload.reply.parent_message_id,
                        "username": payload.reply.parent_user.display_name,
                        "color": self.getChatterColor(payload.reply.parent_user.id)
                    } if payload.reply is not None else None,
                    "preferences": preferences,
                    "chatter": payload.chatter.display_name,
                    "color": color,
                    "emotes": emote_urls,
                    "gif": gif_url,
                    "message": {
                        "text": twitchChatMessage,
                        "id": payload.id
                    },
                    "username": payload.chatter.name,
                    "shared_chat_pfp": source_broadcaster_pfp_url,
                }

                self.socket.send("new_message_bot", message)

        if banned_message:
            await self.ban_user(user=payload.chatter, reason=translation("event.message.ban"))

    @commands.Component.listener("event_message")
    async def event_message_tts(self, payload: twitchio.ChatMessage) -> None:
        tts_event = False
        play_audio = self.activate_tts

        if payload.type != "text": #This is most likely a reward, don't display it
            play_audio = False
            return

        if tts_event:
           if (
               payload.chatter.subscriber
               or payload.chatter.vip
               or payload.chatter.moderator
           ):
               if not payload.chatter.broadcaster:
                   play_audio = True and self.activate_tts

        if payload.chatter.name in [
            "fossabot",
            "streamelements",
            "thebot580",
            "nightbot",
        ]:  # Bots + broadcaster
            play_audio = False

        elif payload.text[0] == "!" or payload.text[0] == "-":
            play_audio = False

        elif payload.source_broadcaster is not None:
            play_audio = False

        twitchChatMessage = self.treat_message(payload.text)

        if twitchChatMessage.split() == []:
            play_audio = False

        elif twitchChatMessage.split(".") == []:
            play_audio = False

        if payload.broadcaster.id != OWNER_ID:  # Only play TTS from my chat
            play_audio = False

        if len(twitchChatMessage) > 256:
            play_audio = False

        blocked_terms: list[str] = []
        async for blocked_term in payload.broadcaster.fetch_blocked_terms(
            moderator=BOT_ID
        ):
            term: twitchio.BlockedTerm = blocked_term
            blocked_terms.append(term.text.lower())

        for word in self.banned_words:
            if word.lower() in payload.text.lower():
                play_audio = False

        if play_audio:

            self.tts_queue.append(twitchChatMessage) #Adding the TTS to the queue
            obswebsockets_manager.set_text("TTS Queue", translation("functions.play_tts_queue.tts_queue").format(self.getTTSQueueLength()))

            if not self.currently_playing_tts:
                self.play_tts_queue(obswebsockets_manager.is_connected() if payload.broadcaster.name == "thefox580" else False)

    # CHANNEL COMMANDS

    @commands.command(aliases=["hello", "howdy", "hey"])
    async def hi(self, ctx: commands.Context) -> None:
        """Simple command that says hello!

        !hi, !hello, !howdy, !hey
        """
        await ctx.reply(translation("commands.hi").format(ctx.chatter.mention))

    @commands.command()
    async def emotes(self, ctx: commands.Context) -> None:
        await ctx.reply(
            translation("commands.emotes")
        )

    @commands.group(invoke_fallback=True)
    async def socials(self, ctx: commands.Context) -> None:
        """Group command for our social links.

        !socials
        """
        await ctx.reply(
            translation("commands.socials.all")
        )

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
    async def uptime(self, ctx: commands.Context):
        await ctx.reply(
            translation("commands.uptime").format(self.format_time_since(datetime.now(timezone.utc), self.start_time), self.start_time.strftime('%d/%m/%Y at %H:%M:%S %Z (%A)'))
        )

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
    async def time(self, ctx: commands.Context):
        await ctx.reply(
            translation("commands.time").format(datetime.now().strftime('%B %d %Y, %H:%M:%S %Z (%A)'))
        )

    @commands.command()
    async def today(self, ctx: commands.Context):
        channelInfo: twitchio.ChannelInfo = await ctx.broadcaster.fetch_channel_info()
        await ctx.send(channelInfo.title.split("} ")[1])

    @commands.command()
    async def ai(self, ctx: commands.Context):
        await ctx.reply(translation("commands.ai"))

    @commands.command()
    async def tts(self, ctx: commands.Context):
        if ctx.chatter.moderator or ctx.chatter.broadcaster: # type: ignore
            self.activate_tts = not self.activate_tts
            if self.activate_tts:
                await ctx.reply(translation("commands.tts.change.on"))
                self.play_tts_queue(obswebsockets_manager.is_connected() if ctx.broadcaster.name == "thefox580" else False)
                return
            await ctx.reply(translation("commands.tts.change.off"))
            return

        if self.activate_tts:
            await ctx.reply(translation("commands.tts.check.on"))
            return
        await ctx.reply(translation("commands.tts.check.off"))

    @commands.command()
    async def subtember(self, ctx: commands.Context):
       await ctx.send(translation("commands.subtember").format(self.format_time_since(datetime.fromtimestamp(1790874000), datetime.now()), ctx.broadcaster.name))

    @commands.command()
    async def gifs(self, ctx: commands.Context):
        sub: twitchio.UserSubscription | None = await ctx.chatter.fetch_subscription(broadcaster=OWNER_ID)
        if sub is not None:
            if sub.tier != "1000":
                await ctx.send(translation("commands.gifs.sub.success"))
                return
            await ctx.send(translation("commands.gifs.sub.fail"))
            return
        await ctx.send(translation("commands.gifs.not_sub"))

    @commands.command(aliases=["donate"])
    async def charity(self, ctx: commands.Context):
        await ctx.send_announcement(
            translation("commands.charity"),
            color="green",
        )

    @commands.command(aliases=["bot"])
    async def version(self, ctx: commands.Context):
        await ctx.reply(
            translation("commands.version"),
            me=True,
        )

    @commands.command(aliases=["music"])
    async def song(self, ctx: commands.Context):
        req = requests.get("http://localhost:1608/")
        res = req.json()

        status = res["status_id"]

        if status == 3:
            await ctx.reply(translation("commands.song.stopped"))
        elif status == 2:
            await ctx.reply(translation("commands.song.paused"))
        else:
            title = res["title"]
            artists = res["artists"]

            artists_str = artists[0]
            for i in range(1, len(artists)):
                if i < len(artists)-1:
                    artists_str += f", {artists[i]}"
                else:
                    artists_str += f" and {artists[i]}"

            total_time = math.floor(res["duration"] / 1000)
            current_time = math.floor(res["progress"] / 1000)

            album = translation("commands.song.playing.album").format(res["album"]) if album in res.keys() else ""

            await ctx.reply(translation("commands.song.playing.message").format(title, album, artists_str, math.floor(current_time/60), "0" if current_time % 60 < 10 else "", current_time % 60, math.floor(total_time/60), "0" if total_time % 60 < 10 else "", total_time%60))

    @commands.command()
    async def age(self, ctx: commands.Context):
        await ctx.send(
            translation("commands.age").format(self.format_time_since(datetime.now(), datetime.fromtimestamp(1139072400), True))
        )

    @commands.command()
    async def rankedlook(self, ctx: commands.Context, *, content: str):
        username = content.split()[0]

        req = requests.get(f"https://api.mcsrranked.com/users/{username}")
        data = json.loads(req.text)
        if data["status"] == "success":
            data = data["data"]
            stats = data["statistics"]["season"]
            totalGamesPlayed = stats["playedMatches"]["ranked"]
            gamesWon = stats["wins"]["ranked"]
            gamesLost = stats["loses"]["ranked"]
            gamesTied = totalGamesPlayed - gamesWon - gamesLost
            pb = stats["bestTime"]["ranked"]
            if pb is None:
                pb = ("no", "pb", "yet")
            else:
                pb = (
                    math.floor((pb / (1000 * 60)) % 60),
                    math.floor((pb / 1000) % 60),
                    math.floor((pb % 1000)),
                )
            ffRate = round(stats["forfeits"]["ranked"] / totalGamesPlayed * 100, 2)
            await ctx.reply(
                translation("commands.elo.success").format(username, data['eloRate'], data['seasonResult']['highest'], data['seasonResult']['lowest'], data['eloRank'], totalGamesPlayed, gamesWon, gamesTied, gamesLost, pb[0], pb[1], pb[2], ffRate),
                me=True,
            )
            return
        await ctx.reply(translation("commands.elo.fail").format(username))

    @commands.command()
    async def mccilook(self, ctx: commands.Context, *, content: str):
        username = content.split()[0]

        mcci_data = mcci.MCCI_STATS(username)

        if mcci_data.isFound():
            await ctx.reply(mcci_data.getSimpleInfos())
            return

        await ctx.reply(translation("commands.mcci.fail").format(username))

    @commands.command()
    @commands.is_broadcaster()
    async def trigger(self, ctx: commands.Context, *, content: str):
        # !trigger alert {"type": "follow", "username": "thefox580"}
        # self.socket.send("alert", {"type": "follow", "username": "thefox580"})

        channel = content.split()[0]
        message = content.split(channel + " ")[1]

        self.socket.send(channel, json.loads(message))

        await ctx.reply("Sent custom trigger")

    @commands.command()
    @commands.is_lead_moderator()
    @commands.is_broadcaster()
    async def color(self, ctx: commands.Context):
        if ctx.chatter is user.Chatter:
            await ctx.reply(
                translation("commands.color.success").format(ctx.chatter.color.html if ctx.chatter.color is not None else None)
            )
            await ctx.reply(
                translation("commands.color.fail").format(self.getChatterColor(ctx.chatter.id))
            )

    @commands.command()
    async def backseat(self, ctx: commands.Context):
        await ctx.send_announcement(translation("commands.backseat"), color="green")

    @commands.command()
    async def schedule(self, ctx: commands.Context):
        week_schedule = self.db.getData("twitch_api", "schedule_week", {"start_week" : { "$lt": datetime.now() }, "end_week" : { "$gte": datetime.now() } })

        if len(week_schedule) > 0:
            this_week = week_schedule[0]
            streams = list(sorted(filter(lambda x: (x["time"] > datetime.now().timestamp()), this_week["days"]), key=lambda stream: stream["time"]))
            if len(streams) > 0:
                next_stream = streams[0]
                time = datetime.fromtimestamp(next_stream["time"])
                await ctx.send(translation("commands.schedule.week.success").format(next_stream["title"], next_stream["category"], self.get_day(time.weekday()), time.day, f"0{time.hour}" if time.hour < 10 else time.hour, f"0{time.minute}" if time.minute < 10 else time.minute))
            else:
                await ctx.send(translation("commands.schedule.week.fail"))
        else:
            await ctx.send(translation("commands.schedule.fail"))

    @commands.command()
    async def pb(self, ctx: commands.Context):
        await ctx.reply(translation("commands.pb").format("19:55.516"))

    @commands.command()
    async def archipelago(self, ctx: commands.Context):
        link = "https://thewebsite580.vercel.app/archipelago/tracker/HsT0nGBVSuW3NBbkdYRhBw/overlay"
        await ctx.reply(translation("commands.archipelago"))

    @commands.command(aliases=["inside", "trading", "it"])
    @commands.cooldown(
        rate=1, per=60 * 10, key=commands.BucketType.chatter
    )  # Cooldown for 1 / 10mins
    async def ad(self, ctx: commands.Context):
        await ctx.send_announcement(
            translation("commands.ad")
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

        color = self.getChatterColor(payload.user.id)

        alert_message = {
            "type": "follow",
            "username": payload.user.display_name,
            "color": color,
            "time_to_live": 5,
        }

        self.socket.send("new_alert_bot", alert_message)

    @commands.Component.listener("event_subscription")
    async def event_subscription(self, payload: twitchio.ChannelSubscribe) -> None:
        print(translation("event.new_sub.print"))
        channel = payload.broadcaster

        if not payload.gift:
            sub_tier = self.format_tier(payload.tier)

            color = self.getChatterColor(payload.user.id)

            alert_message = {
                "type": "first_sub",
                "username": payload.user.display_name,
                "color": color,
                "sub_type": sub_tier,
            }

            message = translation("event.new_sub.message").format(payload.user.display_name, sub_tier)

            self.alerts_queue.append((message, alert_message))

            await channel.send_message(
                sender=BOT_ID,
                message=message,
            )

            if not self.currently_playing_tts:
                self.play_tts_queue(obswebsockets_manager.is_connected() if channel.name == "thefox580" else False)

    @commands.Component.listener("event_subscription_message")
    async def event_subscription_message(
        self, payload: twitchio.ChannelSubscriptionMessage
    ) -> None:
        print(translation("event.resub.print"))
        channel = payload.broadcaster
        sub_tier = self.format_tier(payload.tier)
        streak = ""
        if payload.streak_months is not None and payload.streak_months > 0:
            streak = translation("event.resub.streak").format(payload.streak_months)

        message = translation("event.resub.message").format(payload.user.display_name, sub_tier, payload.months, streak)

        await channel.send_message(
            sender=BOT_ID,
            message=message,
        )

        message = translation("event.resub.tts").format(message, self.treat_message(payload.text))

        color = self.getChatterColor(payload.user.id)

        emote_urls = {}

        for emote in payload.emotes:
            emote_urls[payload.text[emote.begin : emote.end]] = (
                f"https://static-cdn.jtvnw.net/emoticons/v2/{emote.id}/default/dark/2.0"
            )

        alert_message = {
            "type": "resub",
            "username": payload.user.display_name,
            "message": payload.text,
            "amount": payload.months,
            "color": color,
            "emotes": emote_urls,
            "sub_type": sub_tier,
        }

        self.alerts_queue.append((message, alert_message))
        if not self.currently_playing_tts:
            self.play_tts_queue(obswebsockets_manager.is_connected() if channel.name == "thefox580" else False)

    @commands.Component.listener("event_subscription_gift")
    async def event_subscription_gift(
        self, payload: twitchio.ChannelSubscriptionGift
    ) -> None:
        print(translation("event.sub_gift.print"))
        channel = payload.broadcaster
        sub_tier = self.format_tier(payload.tier, True)
        message = ""
        display_name = ""
        if type(payload.user.display_name) is str:
            display_name = payload.user.display_name

        message = translation("event.sub_gift.message.anonymous").format(payload.total, sub_tier, payload.cumulative_total)

        if not payload.anonymous:
            message = translation("event.sub_gift.message.regular").format(display_name, payload.total, sub_tier, payload.cumulative_total)

        await channel.send_message(
            sender=BOT_ID,
            message=message,
        )

        color = (
            self.getChatterColor(payload.user.id) if payload.user is not None else None
        )

        alert_message = {
            "type": "gift_sub",
            "username": payload.user.display_name
            if payload.user is not None
            else "Anonymous",
            "amount": payload.total,
            "color": color,
            "sub_type": sub_tier,
            "total_amount": payload.cumulative_total,
        }

        self.alerts_queue.append((message, alert_message))
        if not self.currently_playing_tts:
            self.play_tts_queue(obswebsockets_manager.is_connected() if channel.name == "thefox580" else False)

    @commands.Component.listener("event_cheer")
    async def event_cheer(self, payload: twitchio.ChannelCheer) -> None:
        print(translation("event.cheer.print"))
        channel = payload.broadcaster
        message = ""
        display_name = translation("event.cheer.anonymous")
        if type(payload.user.display_name) is str:
            display_name = payload.user.display_name

        await channel.send_message(
            sender=BOT_ID,
            message=translation("event.cheer.message").format(display_name, payload.bits),
        )

        message = translation("event.cheer.tts").format(message, self.treat_message(payload.message, True))

        color = (
            self.getChatterColor(payload.user.id) if payload.user is not None else None
        )

        emote_urls = {}

        for emote in self.get_emotes_in_message(payload.message):
            for emotes in self.emotes_dict.values():
                if emote in emotes.keys():
                    emote_urls[emote] = emotes[emote]
                    break

        alert_message = {
            "type": "cheer",
            "username": payload.user.display_name
            if payload.user is not None
            else "Anonymous",
            "message": self.treat_message(payload.message),
            "amount": payload.bits,
            "color": color,
            "emotes": emote_urls,
        }

        self.alerts_queue.append((message, alert_message))
        if not self.currently_playing_tts:
            self.play_tts_queue(obswebsockets_manager.is_connected() if channel.name == "thefox580" else False)

    @commands.Component.listener("event_prediction_start")
    async def event_prediction_start(
        self, payload: twitchio.ChannelPredictionBegin
    ) -> None:
        print(translation("event.predictions.begin.print"))
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
            message=translation("event.predictions.begin.message").format(prediction_title, prediction_outcomes_str, mins),
        )

    @commands.Component.listener()
    async def event_prediction_lock(
        self, payload: twitchio.ChannelPredictionLock
    ) -> None:
        print(translation("event.predictions.lock.print"))
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
            message=translation("event.predictions.lock.message").format(prediction_title, prediction_highest.title, round(channel_points / prediction_total * 100, 2), prediction_outcomes_str),
        )

    @commands.Component.listener("event_prediction_end")
    async def event_prediction_end(
        self, payload: twitchio.ChannelPredictionEnd
    ) -> None:
        print(translation("event.predictions.end.print"))
        channel = payload.broadcaster
        prediction_title = payload.title
        if payload.status == "canceled":
            await channel.send_message(
                sender=BOT_ID,
                message=translation("event.predictions.end.message.cancelled").format(prediction_title),
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
                        prediction_winner.channel_points is not None
                        and outcome.channel_points > prediction_winner.channel_points
                    ):
                        prediction_highest = outcome
            channel_points = 0
            if prediction_winner.channel_points is not None:
                channel_points = prediction_winner.channel_points
            await channel.send_message(
                sender=BOT_ID,
                message=translation("event.predictions.end.message.resolved").format(prediction_title, prediction_winner.title, round(channel_points / prediction_total * 100, 2), prediction_total, len(prediction_winner.users), prediction_outcomes_str),
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
    async def event_poll_progress(self, payload: twitchio.ChannelPollBegin) -> None:
        print(translation("event.poll.progress.print"))
        channel = payload.broadcaster
        poll_title = payload.title
        poll_choices = payload.choices

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
        # Event dispatched when a user goes live from the subscription we made above...
        print(translation("event.stream.online.print"))

        # Keep in mind we are assuming this is for ourselves
        # others may not want your bot randomly sending messages...
        self.start_time = datetime.now()
        await payload.broadcaster.send_message(
            sender=BOT_ID,
            message=translation("event.stream.online.message").format(payload.broadcaster.display_name),
        )

    @commands.Component.listener("event_stream_offline")
    async def event_stream_offline(self, payload: twitchio.StreamOffline) -> None:
        # Event dispatched when a user goes live from the subscription we made above...
        print(translation("event.stream.offline.print"))

        # Keep in mind we are assuming this is for ourselves
        # others may not want your bot randomly sending messages...
        stream_time_diff = self.format_time_since(datetime.now(), self.start_time)
        await payload.broadcaster.send_message(
            sender=BOT_ID,
            message=translation("event.stream.offline.message").format(payload.broadcaster.display_name, stream_time_diff),
        )

    @commands.Component.listener("event_hype_train")
    async def event_hype_train(self, payload: twitchio.HypeTrainBegin) -> None:
        print(translation("event.hype_train.begin.print"))
        channel = payload.broadcaster
        train_level = payload.level
        self.hype_train_level = train_level
        shared_text = ""
        is_shared = payload.shared_train
        if is_shared:
            shared_text = translation("event.hype_train.shared")
        special_text = ""
        train_goal = payload.goal
        train_progress = payload.progress
        train_level_complete = round(
            train_progress / train_goal * 100, 2
        )  # A percentage of level completion

        message = translation("event.hype_train.begin.message").format(shared_text, translation(f"event.hype_train.type.{payload.type}"), self.hype_train_level_complete, train_level)

        await channel.send_message(
            sender=BOT_ID,
            message=message,
        )

        alert_message = {
            "type": "hype_train_start",
            "is_shared": is_shared,
            "train_type": payload.type,
        }

        self.alerts_queue.append((message, alert_message))
        if not self.currently_playing_tts:
            self.play_tts_queue(obswebsockets_manager.is_connected() if channel.name == "thefox580" else False)

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

            message = translation("event.hype_train.start.message").format(shared_text, translation(f"event.hype_train.type.{payload.type}"), self.hype_train_level_complete, train_level)

            await channel.send_message(
                sender=BOT_ID,
                message=message,
            )

            alert_message = {
                "type": "hype_train_level_up",
                "is_shared": is_shared,
                "train_type": payload.type,
                "level": train_level,
            }

            self.alerts_queue.append((message, alert_message))
            if not self.currently_playing_tts:
                self.play_tts_queue(obswebsockets_manager.is_connected() if channel.name == "thefox580" else False)

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

    @commands.Component.listener()
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
                    f"{'' if len(participants_str) == 0 else ', '}{participant.display_name}"
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
                    f"{'' if len(participants_str) == 0 else ', '}{participant.display_name}"
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
                    f"{'' if len(participants_str) == 0 else ', '}{participant.display_name}"
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

    @commands.Component.listener()
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
        # await channel.send_message(
        #    sender=BOT_ID,
        #    message=translation("event.goal.begin.message").format(goal_type_str, goal_name, goal_amount, goal_end_amount),
        # )

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
        # await channel.send_message(
        #    sender=BOT_ID,
        #    message=translation("event.goal.progress.message").format(goal_type_str, goal_name, goal_amount, goal_end_amount),
        # )

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
        # await channel.send_message(
        #    sender=BOT_ID,
        #    message=translation("event.goal.end.message").format(goal_name, goal_end_amount, goal_type_str),
        # )

    @commands.Component.listener()
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

        alert_message = {
            "type": "raid",
            "color": self.getChatterColor(raider.id),
            "username": raider.display_name,
            "viewers": payload.viewer_count,
            "time_to_live": 10,
        }

        self.socket.send("new_alert_bot", alert_message)

    @commands.Component.listener("event_channel_update")
    async def event_channel_update(self, payload: twitchio.ChannelUpdate) -> None:
        print(translation("event.channel_update.print"))
        channel = payload.broadcaster
        category = payload.category_name
        title = payload.title
        # await channel.send_message(
        #    sender=BOT_ID,
        #    message=translation("event.channel_update.message").format(title, category),
        # )

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

    @commands.Component.listener("event_automatic_redemption_add")
    async def event_automatic_redemption_add(
        self, payload: twitchio.ChannelPointsAutoRedeemAdd
    ) -> None:
        print(translation("event.auto_channel_points.print"))
        # channel = payload.broadcaster  # The channel it happened on
        # user = payload.user  # The user who redeemed this reward
        reward = payload.reward  # The reward object
        # reward_type = reward.type  # The type of reward
        # reward_cost = (
        #    reward.channel_points
        # )  # The cost of the reward, in channel points (NOT BITS)
        # reward_id = payload.id  # The reward ID of this reward
        # reward_redeemed_at = payload.redeemed_at  # When the reward was redeemed

        # emote_unlocked = reward.emote  # The emote unlocked from reward_type in "reward_type in ['random_sub_emote_unlock', 'chosen_sub_emote_unlock']"
        # user_input = payload.user_input

        # chat_message = payload.text

        # While most attributes won't be used, it's always good to have them down for later.

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
        )  # The input provided by the user, "" if none was given /needed

        # While most attributes won't be used, it's always good to have them down for later.

        if reward_id == "6fb34032-e66f-4e4a-a390-8a0f092323e0":  # Self-Timeout reward
            await channel.timeout_user(
                moderator=BOT_ID, user=user, reason="Self-Timeout reward", duration=600
            )
            await channel.send_message(
                sender=BOT_ID,
                message=f"{user.display_name} timed themselves out for 10 minutes, good luck out there!",
            )

        elif (
            reward_id == "d5f04aa1-7abc-4244-83f3-d141970bb9d3"
        ):  # Timeout Other reward
            targetted_user = await self.bot.fetch_user(login=user_input)

            if type(targetted_user) is twitchio.User:
                await channel.timeout_user(
                    moderator=BOT_ID,
                    user=targetted_user,
                    reason="Timeout Other reward",
                    duration=600,
                )
                await channel.send_message(
                    sender=BOT_ID,
                    message=f"{user.display_name} timed {targetted_user.display_name} out for 10 minutes, good luck out there!",
                )

            else:
                await payload.refund(token_for=channel)
                await channel.send_whisper(
                    to_user=user,
                    message=f'The user "{user_input}" does not exist. Please try again with a correct username only.',
                )
                print(
                    f'{user.display_name} tried to timeout "{user_input}", but this User ID doesn\'t exist. Warned them in whisper with account "TheFox580"'
                )

        elif reward_title == "First":
            color = self.getChatterColor(user.id)

            alert_message = {
                "type": "channel_points",
                "username": user.display_name,
                "amount": reward_cost,
                "message": "They are the 1st (frfr) to join the stream.",
                "title": reward_title,
                "color": color
                if color is not None
                else "#%06x" % random.randint(0, 0xFFFFFF),
                "time_to_live": 5,
            }

            self.socket.send("new_alert_bot", alert_message)

        elif reward_title == "Water":
            color = self.getChatterColor(user.id)

            alert_message = {
                "type": "channel_points",
                "username": user.display_name,
                "amount": reward_cost,
                "message": "It's time to drink some water!",
                "title": reward_title,
                "color": color,
                "time_to_live": 5,
            }

            self.socket.send("new_alert_bot", alert_message)

        elif reward_title == "Change Message Text Color":
            if self.checkHTMLColor(user_input) != "":

                if self.db.has("twitch_api", "chatter_preferences", {"user_id": user.id}):
                    user_preferences = self.db.getData("twitch_api", "chatter_preferences", {"user_id": user.id})[0]

                    user_preferences["message_color"] = user_input

                    self.db.replace("twitch_api", "chatter_preferences", {"user_id": user.id}, user_preferences)

                else:
                    user_preferences = {
                        "user_id": user.id,
                        "user_name": user.name,
                        "message_color": user_input,
                        "background_color": "#000000",
                        "message_font": "",
                    }

                    self.db.insert("twitch_api", "chatter_preferences", user_preferences)

            else:

                if self.db.has("twitch_api", "chatter_preferences", {"user_id": user.id}):
                    user_preferences = self.db.getData("twitch_api", "chatter_preferences", {"user_id": user.id})[0]

                    user_preferences["message_color"] = "#ffffff"

                    self.db.replace("twitch_api", "chatter_preferences", {"user_id": user.id}, user_preferences)

                else:
                    user_preferences = {
                        "user_id": user.id,
                        "user_name": user.name,
                        "message_color": "#ffffff",
                        "background_color": "#000000",
                        "message_font": "",
                    }

                    self.db.insert("twitch_api", "chatter_preferences", user_preferences)

        elif reward_title == "Change Message Background Color":
            if self.checkHTMLColor(user_input) != "":

                if self.db.has("twitch_api", "chatter_preferences", {"user_id": user.id}):
                    user_preferences = self.db.getData("twitch_api", "chatter_preferences", {"user_id": user.id})[0]

                    user_preferences["background_color"] = user_input

                    self.db.replace("twitch_api", "chatter_preferences", {"user_id": user.id}, user_preferences)

                else:
                    user_preferences = {
                        "user_id": user.id,
                        "user_name": user.name,
                        "message_color": "#ffffff",
                        "background_color": user_input,
                        "message_font": "",
                    }

                    self.db.insert("twitch_api", "chatter_preferences", user_preferences)

            else:
                if self.db.has("twitch_api", "chatter_preferences", {"user_id": user.id}):
                    user_preferences = self.db.getData("twitch_api", "chatter_preferences", {"user_id": user.id})[0]

                    user_preferences["background_color"] = "#000000"

                    self.db.replace("twitch_api", "chatter_preferences", {"user_id": user.id}, user_preferences)

                else:
                    user_preferences = {
                        "user_id": user.id,
                        "user_name": user.name,
                        "message_color": "#ffffff",
                        "background_color": "#000000",
                        "message_font": "",
                    }

                    self.db.insert("twitch_api", "chatter_preferences", user_preferences)

        elif reward_title == "Change Message Text Font":

            if user_input != "Reset":

                if self.db.has("twitch_api", "chatter_preferences", {"user_id": user.id}):
                    user_preferences = self.db.getData("twitch_api", "chatter_preferences", {"user_id": user.id})[0]
                    user_preferences["message_font"] = user_input
                    self.db.replace("twitch_api", "chatter_preferences", {"user_id": user.id}, user_preferences)

                else:
                    user_preferences = {
                        "user_id": user.id,
                        "user_name": user.name,
                        "message_color": "#ffffff",
                        "background_color": "#000000",
                        "message_font": user_input
                    }

                    self.db.insert("twitch_api", "chatter_preferences", user_preferences)

            else:

                if self.db.has("twitch_api", "chatter_preferences", {"user_id": user.id}):
                    user_preferences = self.db.getData("twitch_api", "chatter_preferences", {"user_id": user.id})[0]
                    user_preferences["message_font"] = ""
                    self.db.replace("twitch_api", "chatter_preferences", {"user_id": user.id}, user_preferences)

                else:
                    user_preferences = {
                        "user_id": user.id,
                        "user_name": user.name,
                        "message_color": "#ffffff",
                        "background_color": "#000000",
                        "message_font": "",
                    }

                    self.db.insert("twitch_api", "chatter_preferences", user_preferences)

        else:
            color = self.getChatterColor(user.id)

            alert_message = {
                "type": "channel_points",
                "username": user.display_name,
                "amount": reward_cost,
                "title": reward_title,
                "color": color,
                "time_to_live": 3,
            }

            self.socket.send("new_alert_bot", alert_message)

    @commands.Component.listener("event_custom_power_up_redemption_add")
    async def event_custom_power_up_redemption_add(self, payload: twitchio.CustomPowerupRedemptionAdd) -> None:
        print(translation("event.powerups.print"))
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

        if powerup_title == "Also First":
            color = self.getChatterColor(user.id)

            alert_message = {
                "type": "powerup",
                "username": user.display_name,
                "amount": powerup_cost,
                "message": "They are the 1st (frfr) to join the stream.",
                "title": powerup_title,
                "color": color
                if color is not None
                else "#%06x" % random.randint(0, 0xFFFFFF),
            }

            self.alerts_queue.append((f"{user.display_name} is the 1st (frfr) to join the stream.", alert_message))
            if not self.currently_playing_tts:
                self.play_tts_queue(obswebsockets_manager.is_connected() if channel.name == "thefox580" else False)

        elif powerup_title == "One-time Backseat":
            color = self.getChatterColor(user.id)

            alert_message = {
                "type": "powerup",
                "username": user.display_name,
                "amount": powerup_cost,
                "message": user_input,
                "title": powerup_title,
                "color": color
                if color is not None
                else "#%06x" % random.randint(0, 0xFFFFFF),
            }

            self.alerts_queue.append((user_input, alert_message))
            if not self.currently_playing_tts:
                self.play_tts_queue(obswebsockets_manager.is_connected() if channel.name == "thefox580" else False)

        elif powerup_title == "Toggle Backseat":
            color = self.getChatterColor(user.id)

            alert_message = {
                "type": "powerup",
                "username": user.display_name,
                "amount": powerup_cost,
                "message": "All of chat is allowed to backseat!",
                "title": powerup_title,
                "color": color
                if color is not None
                else "#%06x" % random.randint(0, 0xFFFFFF),
            }

            self.alerts_queue.append((f"{user.display_name} enabled backseat for the next 10 minutes.", alert_message))
            if not self.currently_playing_tts:
                self.play_tts_queue(obswebsockets_manager.is_connected() if channel.name == "thefox580" else False)


    @commands.Component.listener("event_ad_break")
    async def event_ad_break(self, payload: twitchio.ChannelAdBreakBegin) -> None:
        print("Received event : Ad Break Starts")
        channel = payload.broadcaster
        started_at = payload.started_at
        duration = self.roundToNNearest(payload.duration, 15)

        if self.message_sent >= 5:
            await channel.send_message(
                sender=BOT_ID,
                message=f"⚠️ A {self.format_time_since(datetime.fromtimestamp(started_at.timestamp() + duration), datetime.now())} ad break has started. ⚠️",
            )
            self.message_sent = 0

    @commands.Component.listener("event_chat_notification")
    async def event_chat_notification(self, payload: twitchio.ChatNotification) -> None:
        print(translation("event.chat_notification.print"))
        channel = payload.broadcaster
        user = payload.chatter
        type = payload.notice_type

        if type == "watch_streak" and payload.watch_streak is not None:
            color = self.getChatterColor(user.id)

            alert_message = {
                "type": "watch_streak",
                "username": user.display_name,
                "amount": payload.watch_streak.streak,
                "color": color,
            }

            self.alerts_queue.append((translation("event.chat_notification.watch_streak.message").format(user.display_name, streak_amount), alert_message))
            if not self.currently_playing_tts:
                self.play_tts_queue(obswebsockets_manager.is_connected() if channel.name == "thefox580" else False)

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
                        eventsub.ChannelPollProgressSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
                        eventsub.ChannelPollEndSubscription(
                            broadcaster_user_id=OWNER_ID
                        ),
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
                        eventsub.ChatNotificationSubscription(broadcaster_user_id=OWNER_ID, user_id=BOT_ID),
                        eventsub.CustomPowerupRedeemAddSubscription(broadcaster_user_id=OWNER_ID)
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
