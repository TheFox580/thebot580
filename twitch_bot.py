import asyncio
import json
import logging
import math
import random
import sqlite3
from threading import Timer
from datetime import datetime, timezone

import asqlite
import requests
import twitchio
from twitchio import eventsub, user
from twitchio.ext import commands

import mcci
import mongo
import socket_client
from audio_player import AudioManager
from keys import (
    AZURE_TTS_VOICE,
    BOT_ID,
    HAS_ONBOARDED,
    MONGODB_URL,
    OWNER_ID,
    TWITCH_BOT_CLIENT_ID,
    TWITCH_BOT_CLIENT_SECRET,
    BANNED_WORD_LIST,
)
from obs_websockets import OBSWebsocketsManager
from tts import TTSManager

tts_manager = TTSManager(AZURE_TTS_VOICE)
audio_manager = AudioManager()
obswebsockets_manager = OBSWebsocketsManager()

LOGGER: logging.Logger = logging.getLogger("TheBot580")


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
            eventsub.SharedChatSessionBeginSubscription(broadcaster_user_id=OWNER_ID)
        )
        subscriptions.append(
            eventsub.SharedChatSessionUpdateSubscription(broadcaster_user_id=OWNER_ID)
        )
        subscriptions.append(
            eventsub.SharedChatSessionEndSubscription(broadcaster_user_id=OWNER_ID)
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

            # Subscribe and listen to when poll starts or ends..
            subscriptions.append(
                eventsub.ChannelPollBeginSubscription(
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

        resp: twitchio.MultiSubscribePayload = await self.multi_subscribe(subscriptions)
        if resp.errors:
            LOGGER.warning(
                "Failed to subscribe to: %r, for user: %s", resp.errors, payload.user_id
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

        LOGGER.info("Added token to the database for user: %s", resp.user_id)
        return resp

    async def event_ready(self) -> None:
        LOGGER.info("Successfully logged in as: %s", self.bot_id)


class MyComponent(commands.Component):
    def __init__(self, bot: Bot):
        # Passing args is not required...
        # We pass bot here as an example...
        self.banned_words = BANNED_WORD_LIST
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

        self.chat_emotes_combo: list = [  # type: ignore
            "",
            0,
        ]  # Holds a list like : [str("Emote Name"), int(number of instance of this emote in a row)]

        self.shared_chat_users: list = []
        self.hype_train_level: int = -1
        self.hype_train_level_complete: float = 0
        self.start_time: datetime = datetime.now()
        self.lurkers = []
        self.activate_tts: bool = True
        self.tts_queue: list[str] = []
        self.currently_playing_tts: bool = False
        self.message_sent = 0
        self.db = mongo.Database(MONGODB_URL)
        # self.db.update(
        #    "twitch_api",
        #    "messages",
        #    {"user_id": OWNER_ID},
        #    {"$set": {"user_id": OWNER_ID, "messages": []}},
        # )

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
            print("WARNING!! COULDN'T GET THE TOKEN")
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
                badge_comp[version["id"]] = version["image_url_1x"].split("/1")[0]
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
                badge_comp[version["id"]] = version["image_url_1x"].split("/1")[0]
            badges[badge["set_id"]] = badge_comp

        return badges

    def getChatterColor(self, user_id: str) -> str | None:
        color: str | None = None

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Client-Id": TWITCH_BOT_CLIENT_ID,
        }

        params = {"user_id": user_id}

        req = requests.get(
            "https://api.twitch.tv/helix/chat/color", headers=headers, params=params
        )

        if not req.ok:
            return color

        res = req.json()

        for user in res["data"]:
            color = user["color"] if user["color"] != "" else None
            break

        return color

    def getEmoteList(self) -> list[str]:
        emotes_list: list[str] = []
        for value in self.emotes_dict.values():
            for key in value.keys():
                emotes_list.append(key)

        return emotes_list

    def treat_message(self, message: str, cheer: bool = False) -> str:
        final_message = ""
        if not cheer:
            if (
                "Cheer" in message
            ):  # If the message is being treated as a non cheer message and has "Cheer" in it, just don't read it
                return ""
        messageList = message.split()
        for word in messageList:
            word = word.replace("_", " ")
            if ("🫡" == word) or ("o7" == word):
                final_message += "eau 7 "
            elif "D:" == word:
                final_message += "D face "
            elif "<3" == word:
                final_message += "love "
            elif "</3" == word:
                final_message += "don't love "
            elif "https" in word:
                pass
            elif "Cheer" in word:  # We don't want it to say the bits amount!
                pass
            elif self.message_has_an_emote(word):
                pass
            else:
                final_message += word + " "

        return final_message[:-1]

    def format_tier(self, tier: str, is_gift: bool = False) -> str:
        if not is_gift:
            if tier == "1000":
                return "1 / Prime"
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

        seconds_text = "seconde"
        minutes_text = "minute"
        if secs != 1:
            seconds_text += "s"
        if mins != 1:
            minutes_text += "s"

        time_text = f"{mins} {minutes_text} and {secs} {seconds_text}"  # I'm always including the minutes just so that I don't have to handle the "and". Big Brain

        if leap_year_warning:
            time_text += (
                " (Le temps peut être imparfait à cause des années bisextiles.)"
            )

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

    def play_tts_queue(self) -> None:
        if len(self.tts_queue) > 0 and self.activate_tts: # If there's TTS in the queue
            if not self.currently_playing_tts:
                self.currently_playing_tts = True

            tts_message: str = self.tts_queue.pop(0)
            print(f"Taille de la file: {len(self.tts_queue)}")

            # Send Twitch message to Azure to turn into cool audio
            tts_file = tts_manager.text_to_speech(tts_message)
            print(tts_file)

            tts_length = audio_manager.get_audio_length(tts_file)

            print(f"Message joué: {tts_message}")
            audio_manager.play_audio(tts_file, sleep_during_playback=False, play_using_music=True)

            delete_tts_at_end = Timer(tts_length, audio_manager.delete_file, [tts_file], {}) #Delete TTS at the end
            delete_tts_at_end.start()

            wait_end_tts = Timer(tts_length, self.play_tts_queue, [], {}) #Waiting until end of TTS to give it some time to breath
            wait_end_tts.start()

        else:
            self.currently_playing_tts = False

    # We use a listener in our Component to display the messages received.
    @commands.Component.listener("event_message")
    async def event_message_overlay(self, payload: twitchio.ChatMessage) -> None:
        banned_message = False
        command_message = False

        print(
            f"[{payload.broadcaster.display_name}] - {payload.chatter.display_name}: {payload.text} {f'(De {payload.source_broadcaster.display_name})' if payload.source_broadcaster is not None else ''}"
        )

        # Setup what will be translated as a variable
        twitchChatMessage = payload.text
        if payload.type == "user_intro":
            command_message = True
            twitchChatMessage = f"FIRST TIME CHATTER --> {payload.chatter.name} a dit : {twitchChatMessage}"

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
                    print(f"{word} a été ajouté en tant que terme bloqué sur la chaine.")
                    await payload.delete(moderator=BOT_ID)

        if payload.chatter.name in [
            "fossabot",
            "streamelements",
            "thebot580",
            "nightbot",
        ]:  # Bots + broadcaster
            command_message = True
        elif payload.text[0] == "!" or payload.text[0] == "-":
            command_message = True
        elif payload.source_broadcaster is not None and self.activate_tts is True:
            command_message = True

        if not (banned_message or command_message):
            # Send new message to server

            twitchChatMessage = ""
            emote_urls = {}

            for messageFragment in payload.fragments:
                if messageFragment.type == "emote":
                    emote_urls[messageFragment.text] = (
                        f"https://static-cdn.jtvnw.net/emoticons/v2/{messageFragment.emote.id}/default/dark/2.0"
                    )
                    twitchChatMessage += messageFragment.text + " "
                elif messageFragment.type == "text":
                    twitchChatMessage += messageFragment.text + " "

            emotes = self.get_emotes_in_message(twitchChatMessage)

            for emote in emotes:
                for emotes_platform in self.emotes_dict.values():
                    if emote in emotes_platform.keys():
                        emote_urls[emote] = emotes_platform[emote]

            source_broadcaster_pfp_url: str | None = None

            if payload.source_broadcaster is not None:
                source_broadcaster = await payload.source_broadcaster.user()
                source_broadcaster_pfp_url = source_broadcaster.profile_image.url

            color = (
                payload.chatter.color.html
                if payload.chatter.color is not None
                else "#%06x" % random.randint(0, 0xFFFFFF)
            )

            self.message_sent += 1
            if self.chat_emotes_combo != ["", 0]:  # If we currently have a combo
                if self.message_has_emote(
                    twitchChatMessage, self.chat_emotes_combo[0]
                ):  # If it is the right emote
                    self.chat_emotes_combo[1] += 1
                    print(
                        f"+1 au combo {self.chat_emotes_combo[0]} de {payload.chatter.display_name} (Maintenant {self.chat_emotes_combo[1]}) "
                    )
                else:
                    print(
                        f"Le combo de {self.chat_emotes_combo[1]}x {self.chat_emotes_combo[0]} a été arrêté par {payload.chatter.display_name}"
                    )
                    if self.chat_emotes_combo[1] >= 5:
                        await payload.broadcaster.send_message(
                            sender=BOT_ID,
                            message=f"Combo {self.chat_emotes_combo[1]}x de {self.chat_emotes_combo[0]} ! POGGIES",
                        )
                    self.chat_emotes_combo: list = [  # type: ignore
                        "",
                        0,
                    ]  # Resetting Emotes Combo, because the emote we were looking for wasn't sent
            else:
                if self.message_has_an_emote(
                    twitchChatMessage
                ):  # If the message has at least an emote
                    emote: str = self.get_first_emote_in_message(twitchChatMessage)
                    self.chat_emotes_combo: list = [emote, 1]
                    print(
                        f"Nouveau combo : {self.chat_emotes_combo[0]}. Commencé par {payload.chatter.display_name}"
                    )

            message = {
                "badges": [
                    self.badges_dict[badge.set_id][badge.id] for badge in payload.badges
                ],
                "reply": {
                    "id": payload.reply.parent_message_id,
                    "username": payload.reply.parent_user.display_name,
                    "color": self.getChatterColor(payload.reply.parent_user.id)
                } if payload.reply is not None else None,
                "chatter": payload.chatter.display_name,
                "color": color,
                "emotes": emote_urls,
                "message": {
                    "text": twitchChatMessage,
                    "id": payload.id
                },
                "username": payload.chatter.name,
                "shared_chat_pfp": source_broadcaster_pfp_url,
            }

            self.socket.send("new_message_bot", message)

        if banned_message:
            # IF A WORD IN SOMEONE'S MESSAGE IS IN self.banned_words, THEY WILL BE BANNED FOREVER, THE MESSAGE WILL NOT BE SAID OUT LOUD, INSTEAD SAYING THAT SOMEONE IS BANNED. MODS / STREAMER CAN UNBAN THEM IF YOU WANT.
            await payload.chatter.ban(moderator=BOT_ID, reason="MESSAGE INVALIDE")
            banMessage = "MESSAGE BANNI DETECTE : LE MESSAGE NE SERA PAS TRAITE"
            print(banMessage)

    @commands.Component.listener("event_message")
    async def event_message_tts(self, payload: twitchio.ChatMessage) -> None:
        tts_event = False
        play_audio = self.activate_tts

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

        if len(twitchChatMessage) > 250:
            play_audio = False

        if play_audio:

            self.tts_queue.append(twitchChatMessage) #Adding the TTS to the queue
            print(f"Nouveau TTS! Taille de la file : {len(self.tts_queue)}")

            if not self.currently_playing_tts:
                self.play_tts_queue()

    # CHANNEL COMMANDS

    @commands.command(aliases=["hello", "howdy", "hey"])
    async def hi(self, ctx: commands.Context) -> None:
        """Simple command that says hello!

        !hi, !hello, !howdy, !hey
        """
        await ctx.reply(f"Salut {ctx.chatter.mention}!")

    @commands.command()
    async def emotes(self, ctx: commands.Context) -> None:
        await ctx.reply(
            "Pour avoir accès a plus d'emotes, installez l'extension 7TV (https://7tv.app/) sur votre navigateur."
        )

    @commands.group(invoke_fallback=True)
    async def socials(self, ctx: commands.Context) -> None:
        """Group command for our social links.

        !socials
        """
        await ctx.reply(
            "https://www.discord.gg/9tmdgHWaMU, https://www.youtube.com/@lerenard580"
        )

    @socials.command(name="discord")
    async def socials_discord(self, ctx: commands.Context) -> None:
        """Sub command of socials that sends only our discord invite.

        !socials discord
        """
        await ctx.reply("Le discord : https://www.discord.gg/9tmdgHWaMU")

    @socials.command(name="youtube")
    async def socials_youtube(self, ctx: commands.Context) -> None:
        """Sub command of socials that sends only our discord invite.

        !socials discord
        """
        await ctx.reply("La chaine Youtube : https://www.youtube.com/@lerenard580")

    @commands.command(aliases=["follow", "followsince"])
    async def followage(self, ctx: commands.Context):
        print(ctx.chatter)
        if type(ctx.chatter) is twitchio.Chatter:
            follow_info = await ctx.chatter.follow_info()
            print(follow_info)
            if follow_info is None:
                await ctx.reply(
                    f"Désolé {ctx.chatter.display_name}, mais tu ne follow pas la chaîne..."
                )
            else:
                follow_time = follow_info.followed_at
                await ctx.reply(
                    f"{ctx.chatter.display_name}, tu a follow la chaîne depuis {self.format_time_since(datetime.now(timezone.utc), follow_time, True)}. (Follow le {follow_time.strftime('%d/%m/%Y at %H:%M:%S %Z')})"
                )

    @commands.command()
    async def uptime(self, ctx: commands.Context):
        await ctx.reply(
            f"Fox est en live depuis {self.format_time_since(datetime.now(timezone.utc), self.start_time)} (Stream commencé le {self.start_time.strftime('%d/%m/%Y at %H:%M:%S %Z')})."
        )

    @commands.command()
    async def lurk(self, ctx: commands.Context):
        if ctx.chatter.name not in self.lurkers:
            self.lurkers.append(ctx.chatter.name)
            await ctx.reply(f"Tu viens de lurk {ctx.chatter.display_name}, à plus !")
        else:
            await ctx.reply(
                f"Tu étais déjà en train de lurk! Mais à plus {ctx.chatter.display_name}."
            )

    @commands.command()
    async def unlurk(self, ctx: commands.Context):
        if ctx.chatter.name in self.lurkers:
            self.lurkers.remove(ctx.chatter.name)
            await ctx.reply(f"Re-bienvenue {ctx.chatter.display_name}!")
        else:
            await ctx.reply(
                f"Tu n'étais pas en train de lurk! Mais re-bienvenue {ctx.chatter.display_name}."
            )

    @commands.command()
    async def time(self, ctx: commands.Context):
        await ctx.reply(
            f"Il est actuellement {datetime.now().strftime('%B %d %Y, %H:%M:%S')} pour Fox."
        )

    @commands.command()
    async def today(self, ctx: commands.Context):
        await ctx.send(
            "Le titre du stream explique surement extremement bien le stream du jour"
        )

    @commands.command()
    async def ai(self, ctx: commands.Context):
        await ctx.reply(
            "Je n'utilise l'IA pour rien (ni le code, ni l'art, ...) Je pense que n'importe qui peut faire n'importe quoi avec un peu d'effort. Fait ce qu'il te fait par tot même et surtout, amuse toi !"
        )

    @commands.command()
    async def tts(self, ctx: commands.Context):
        if ctx.chatter.moderator or ctx.chatter.broadcaster:  # type: ignore # type: ignore
            self.activate_tts = not self.activate_tts
            if self.activate_tts:
                await ctx.reply("TTS à été activé.")
                self.play_tts_queue()
                return
            await ctx.reply("TTS à été désactivé.")
            return

        if self.activate_tts:
            await ctx.reply("TTS est actuellement activé.")
            return
        await ctx.reply("TTS est actuellement désactivé.")

    # @commands.command()
    # async def subtember(self, ctx: commands.Context):
    #    await ctx.send(f"For the next {self.format_time_since(datetime.fromtimestamp(1759338000), datetime.now())}, you can get up to 30% off your subscription thanks to this year's SUBtember! If you want to support me, you can do so by going to https://www.twitch.tv/subs/thefox580 !")

    # @commands.command(aliases=["donate"])
    # async def charity(self, ctx: commands.Context):
    #    await ctx.send_announcement(
    #        "We're raising money for the Sarcoma Foundation of America initiative! Donate here: https://thewebsite580.vercel.app/donate",
    #        color="green",
    #    )

    @commands.command(aliases=["bot"])
    async def version(self, ctx: commands.Context):
        await ctx.reply(
            'Je suis un bot custom en Python, basé sur l\'application "Babagaboosh" de DougDoug. Je tourne actuellement sur la version 580.FR (En utilisant TwitchIO 3.2.0 & Python 3.13.12). Vous pouvez aller voir par vous même à https://github.com/TheFox580/thebot580',
            me=True,
        )

    @commands.command()
    async def age(self, ctx: commands.Context):
        await ctx.send(
            f"Fox à {self.format_time_since(datetime.now(), datetime.fromtimestamp(1139072400), True)} ans."
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
                f"{username} | Elo: {data['eloRate']} (High/Low: {data['seasonResult']['highest']}/{data['seasonResult']['lowest']}) | #{data['eloRank']} === {totalGamesPlayed} parties jouées | W/D/L {gamesWon}/{gamesTied}/{gamesLost} === PB: {pb[0]}:{pb[1]}.{pb[2]} === {ffRate}% Taux d'Abandon",
                me=True,
            )
            return
        await ctx.reply(f'Aucun utilisateur avec le pseudo "{username}" à été trouvé')

    @commands.command()
    async def mccilook(self, ctx: commands.Context, *, content: str):
        username = content.split()[0]

        mcci_data = mcci.MCCI_STATS(username)

        if not mcci_data.isFound():
            await ctx.reply(
                f'Aucun utilisateur avec le pseudo "{username}" à été trouvé'
            )
            return

        await ctx.reply(mcci_data.getSimpleInfos())

    # @commands.command()
    # async def coding(self, ctx: commands.Context):
    #    await ctx.reply(f"Fox is coding for WubDub_'s upcoming Minecraft Event, \"Goofy Games\". I wrote this command in advance so idk what I'm working on right now, but maybe it's written on screen.")

    # @commands.command()
    # async def team(self, ctx: commands.Context):
    #    await ctx.reply(
    #        "In this event, Fox is in a team with KaNukei, Ceeps & DaHouse_Panda!"
    #    )

    @commands.command()
    @commands.is_broadcaster()
    async def trigger(self, ctx: commands.Context, *, content: str):
        # !trigger alert {"type": "follow", "username": "thefox580"}
        # self.socket.send("alert", {"type": "follow", "username": "thefox580"})

        channel = content.split()[0]
        message = content.split(channel + " ")[1]

        self.socket.send(channel, json.loads(message))

        await ctx.reply("Trigger custom envoté")

    @commands.command()
    @commands.is_lead_moderator()
    @commands.is_broadcaster()
    async def color(self, ctx: commands.Context):
        if ctx.chatter is user.Chatter:
            await ctx.reply(
                f"Votre couleur est: {ctx.chatter.color.html if ctx.chatter.color is not None else None}"
            )
            await ctx.reply(
                f"Votre couleur est probablement: {self.getChatterColor(ctx.chatter.id)}"
            )

    # @commands.command()
    # async def backseat(self, ctx: commands.Context):
    #    await ctx.send_announcement(f"No backseat will be allowed unless Fox asks. You will get timed out 10 minutes for backseating.", color="green")

    # @commands.command()
    # async def pb(self, ctx: commands.Context):
    #    pb = ""
    #    with open("./custom_shit_that_uses_this/pb.txt", "r") as file:
    #        for lines in file:
    #            pb = lines
    #        file.close()
    #    await ctx.reply(f"Fox's current PB is {pb} (In private rooms)")

    # @commands.command()
    # async def games(self, ctx: commands.Context):
    #     await ctx.reply("Fox is playing Balatro, Portal 2, Trackmania and a Bingo")

    # @commands.command()
    # async def archipelago(self, ctx: commands.Context):
    #     link = "https://archipelago.gg/tracker/ANatV6flTqei79kJ7RpPig"
    #     await ctx.reply(
    #         f"Archipelago is a multi-game randomizer, this means objects in a game can be found in another one. You can check Fox's progress at {link}"
    #     )

    # @commands.command(aliases=["sludgineers"])
    # @commands.cooldown(
    #    rate=1, per=60 * 10, key=commands.BucketType.chatter
    # )  # Cooldown for 1 / 10mins
    # async def sludge(self, ctx: commands.Context):
    #    await ctx.send_announcement(
    #        "Thanks to Funk Games for the key! The game comes out on June 1st, and you can buy it there: https://lurk.ly/pJVjlz"
    #    )

    @commands.command()
    @commands.is_moderator()
    async def setgame(self, ctx: commands.Context, *, content: str) -> None:
        game: twitchio.Game | None = await ctx.bot.fetch_game(name=content)
        print(game)
        if game is None:
            await ctx.reply(
                "La catégorie n'a pas pu être mise a jour, veuillez rentrer un nom de jeu correct."
            )
        else:
            await ctx.broadcaster.modify_channel(game_id=game.id)

    @commands.command()
    @commands.is_moderator()
    async def settitle(self, ctx: commands.Context, *, content: str) -> None:
        await ctx.broadcaster.modify_channel(title=content)

    # CHANNEL INTERACTIONS

    @commands.Component.listener()
    async def event_follow(self, payload: twitchio.ChannelFollow) -> None:
        print("Received event : User Follow")
        channel = payload.broadcaster
        await channel.send_message(
            sender=BOT_ID,
            message=f"Merci {payload.user.display_name} pour le follow!",
        )

        color = self.getChatterColor(payload.user.id)

        alert_message = {
            "type": "follow",
            "username": payload.user.display_name,
            "color": color
            if color is not None
            else "#%06x" % random.randint(0, 0xFFFFFF),
        }

        self.socket.send("new_alert_bot", alert_message)

    @commands.Component.listener()
    async def event_subscription(self, payload: twitchio.ChannelSubscribe) -> None:
        print("Received event : 'New User Subscription'")
        channel = payload.broadcaster
        sub_tier = self.format_tier(payload.tier)

        color = self.getChatterColor(payload.user.id)

        alert_message = {
            "type": "first_year",
            "username": payload.user.display_name,
            "color": color
            if color is not None
            else "#%06x" % random.randint(0, 0xFFFFFF),
            "sub_type": sub_tier,
        }

        self.socket.send("new_alert_bot", alert_message)

        if not payload.gift:
            await channel.send_message(
                sender=BOT_ID,
                message=f"{payload.user.display_name} s'est abonné en Tier {sub_tier} !",
            )

    @commands.Component.listener()
    async def event_subscription_message(
        self, payload: twitchio.ChannelSubscriptionMessage
    ) -> None:
        print("Received event : 'User Resubscription'")
        channel = payload.broadcaster
        sub_tier = self.format_tier(payload.tier)
        streak = ""
        if payload.streak_months is not None and payload.streak_months > 0:
            streak = (
                f" Iel est abonné depuis {payload.streak_months} months à la suite !"
            )

        await channel.send_message(
            sender=BOT_ID,
            message=f"{payload.user.display_name} s'est réabonné en Tier {sub_tier} depuis {payload.months} mois !{streak}",
        )

        message = f'{payload.user.display_name} s\'est réabonné en Tier {sub_tier} depuis {payload.months} mois !{streak} Iel a dit: "{self.treat_message(payload.text)}"'
        output = tts_manager.text_to_speech(message)

        color = self.getChatterColor(payload.user.id)

        emote_urls = {}

        for emote in payload.emotes:
            emote_urls[payload.text[emote.begin : emote.end]] = (
                f"https://static-cdn.jtvnw.net/emoticons/v2/{emote.id}/default/dark/2.0"
            )

        alert_message = {
            "type": "resub_year" if payload.months % 12 == 0 else "resub_not_year",
            "username": payload.user.display_name,
            "message": payload.text,
            "amount": payload.months // 12
            if payload.months % 12 == 0
            else payload.months,
            "color": color
            if color is not None
            else "#%06x" % random.randint(0, 0xFFFFFF),
            "emotes": emote_urls,
            "sub_type": sub_tier,
            "tts_loc": output,
        }

        self.socket.send("new_alert_bot", alert_message)
        # audio_manager.play_audio(output, True, True, True) # Disabled to play in the webpage

    @commands.Component.listener()
    async def event_subscription_gift(
        self, payload: twitchio.ChannelSubscriptionGift
    ) -> None:
        print("Received event : 'User Sub Gifting'")
        channel = payload.broadcaster
        sub_tier = self.format_tier(payload.tier, True)
        message = ""
        display_name = "Un utilisateur anonyme"
        if type(payload.user.display_name) is str:  # type: ignore
            display_name = payload.user.display_name  # type: ignore

        if payload.anonymous:
            await channel.send_message(
                sender=BOT_ID,
                message=f"{display_name} à donné {payload.total} subs de Tier {sub_tier} à la communauté ! Au total, il y a eu {payload.cumulative_total} sub gifts d'utilisateurs anonymes dans la communauté !",
            )
            message = f"{display_name} à donné {payload.total} subs de Tier {sub_tier} à la communauté ! Au total, il y a eu {payload.cumulative_total} sub gifts d'utilisateurs anonymes dans la communauté !"
        else:
            await channel.send_message(
                sender=BOT_ID,
                message=f"{display_name} à donné {payload.total} subs de Tier {sub_tier} à la communauté ! Au total, {display_name} à donné {payload.cumulative_total} subs à la communauté !",
            )
            message = f"{display_name} à donné {payload.total} subs de Tier {sub_tier} à la communauté ! Au total, {display_name} à donné {payload.cumulative_total} subs à la communauté !"
        output = tts_manager.text_to_speech(message)

        color = (
            self.getChatterColor(payload.user.id) if payload.user is not None else None
        )

        alert_message = {
            "type": "gift_sub",
            "username": payload.user.display_name
            if payload.user is not None
            else "Un utilisateur anonyme",
            "amount": payload.total,
            "color": color
            if color is not None
            else "#%06x" % random.randint(0, 0xFFFFFF),
            "sub_type": sub_tier,
            "total_amount": payload.cumulative_total,
            "tts_loc": output,
        }

        self.socket.send("new_alert_bot", alert_message)
        # audio_manager.play_audio(output, True, True, True) # Disabled to play in the webpage

    @commands.Component.listener()
    async def event_cheer(self, payload: twitchio.ChannelCheer) -> None:
        print("Received event : 'User Cheer'")
        channel = payload.broadcaster
        message = ""
        display_name = "Un utilisateur anonyme"
        if type(payload.user.display_name) is str:  # type: ignore
            display_name = payload.user.display_name  # type: ignore
        if payload.anonymous:
            await channel.send_message(
                sender=BOT_ID,
                message=f"Un utilisateur anonyme à donné {payload.bits} bits!",
            )
            message = f"Un utilisateur anonyme à donné {payload.bits} bits! Iel a dit: {self.treat_message(payload.message, True)}"
        else:
            await channel.send_message(
                sender=BOT_ID,
                message=f"{display_name} à donné {payload.bits} bits!",
            )
            message = f"{display_name} à donné {payload.bits} bits! Iel a dit: {self.treat_message(payload.message, True)}"
        output = tts_manager.text_to_speech(message)

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
            else "Un utilisateur anonyme",
            "message": self.treat_message(payload.message),
            "amount": payload.bits,
            "color": color
            if color is not None
            else "#%06x" % random.randint(0, 0xFFFFFF),
            "emotes": emote_urls,
            "tts_loc": output,
        }

        self.socket.send("new_alert_bot", alert_message)

        # audio_manager.play_audio(output, True, True, True) # Disabled to play in the webpage

    @commands.Component.listener()
    async def event_prediction_start(
        self, payload: twitchio.ChannelPredictionBegin
    ) -> None:
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
            message=f'Une nouvelle prédiction a commencé ! "{prediction_title}" | Les choix sont : {prediction_outcomes_str}. Cette prédiction se ferme dans {mins} minute(s).',
        )

    @commands.Component.listener()
    async def event_prediction_lock(
        self, payload: twitchio.ChannelPredictionLock
    ) -> None:
        print("Received event : Prediction locked")
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
        await channel.send_message(
            sender=BOT_ID,
            message=f'La prédiction "{prediction_title}" est maintenant fermée ! "{prediction_highest.title}" est le choix le plus choisi avec {round(channel_points / prediction_total * 100, 2)}% | Les choix sont : {prediction_outcomes_str}.',
        )

    @commands.Component.listener()
    async def event_prediction_end(
        self, payload: twitchio.ChannelPredictionEnd
    ) -> None:
        print("Received event : Prediction ended")
        channel = payload.broadcaster
        prediction_title = payload.title
        if payload.status == "canceled":
            await channel.send_message(
                sender=BOT_ID,
                message=f'La prédiction "{prediction_title}" a été annulé! Tout les points de chaînes seront rendus.',
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
                message=f'La prédiction "{prediction_title}" est terminée! "{prediction_winner.title}" est le choix gagnant avec {round(channel_points / prediction_total * 100, 2)}% (C\'est {prediction_total} Chockbars pour {len(prediction_winner.users)} chatteurs) | Les choix étaient : {prediction_outcomes_str}.',  # type: ignore
            )

    @commands.Component.listener()
    async def event_poll_begin(self, payload: twitchio.ChannelPollBegin) -> None:
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
            message=f'Un nouveau sondage a démarré ! "{poll_title}" | Les choix sont : {poll_choices_str}. Ce sondage se termine dans {mins} minute(s).',
        )

    @commands.Component.listener()
    async def event_poll_end(self, payload: twitchio.ChannelPollEnd) -> None:
        print("Received event : Poll ended")
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
            message=f'Nous avons les résultats! {poll_winner.title} à gagné "{poll_title}" avec {poll_winner.votes} votes | Les choix étaient : {poll_choices_str}.',
        )

    @commands.Component.listener()
    async def event_stream_online(self, payload: twitchio.StreamOnline) -> None:
        # Event dispatched when a user goes live from the subscription we made above...

        # Keep in mind we are assuming this is for ourselves
        # others may not want your bot randomly sending messages...
        self.start_time = datetime.now()
        await payload.broadcaster.send_message(
            sender=BOT_ID,
            message=f"{payload.broadcaster.display_name} est maintenant en live.",
        )

    @commands.Component.listener()
    async def event_stream_offline(self, payload: twitchio.StreamOffline) -> None:
        # Event dispatched when a user goes live from the subscription we made above...

        # Keep in mind we are assuming this is for ourselves
        # others may not want your bot randomly sending messages...
        stream_time_diff = self.format_time_since(datetime.now(), self.start_time)
        await payload.broadcaster.send_message(
            sender=BOT_ID,
            message=f"Le stream est maintenant terminé. {payload.broadcaster.display_name} était en live pendant {stream_time_diff}.",
        )

    @commands.Component.listener()
    async def event_hype_train(self, payload: twitchio.HypeTrainBegin) -> None:
        print("Received event : Hype Train started")
        channel = payload.broadcaster
        train_level = payload.level
        self.hype_train_level = train_level
        shared_text = ""
        is_shared = payload.shared_train
        if is_shared:
            shared_text = "Pargagé "
        special_text = ""
        if payload.type == "golden_kappa":
            special_text = "Kappa Doré "
        elif payload.type == "treasure":
            special_text = "Trésor "
        elif payload.type == "mythic":
            special_text = "Mythique "
        train_goal = payload.goal
        train_progress = payload.progress
        train_level_complete = round(
            train_progress / train_goal * 100, 2
        )  # A percentage of level completion
        await channel.send_message(
            sender=BOT_ID,
            message=f"Un Train de la Hype {special_text}{shared_text}viens de commencer! Nous sommes à {train_level_complete}% dans le niveau {train_level}!",
        )

        alert_message = {
            "type": "hype_train_start",
            "is_shared": is_shared,
            "train_type": payload.type,
        }

        self.socket.send("new_alert_bot", alert_message)

    @commands.Component.listener()
    async def event_hype_train_progress(
        self, payload: twitchio.HypeTrainProgress
    ) -> None:
        print("Received event : Hype Train progressed")
        channel = payload.broadcaster
        train_level = payload.level
        if train_level > self.hype_train_level:  # type: ignore
            self.hype_train_level = train_level
            shared_text = ""
            is_shared = payload.shared_train
            if is_shared:
                shared_text = "Pargagé "
            special_text = ""
            if payload.type == "golden_kappa":
                special_text = "Kappa Doré "
            elif payload.type == "treasure":
                special_text = "Trésor "
            elif payload.type == "mythic":
                special_text = "Mythique "
            train_goal = payload.goal
            train_progress = payload.progress
            self.hype_train_level_complete = round(
                train_progress / train_goal * 100, 2
            )  # A percentage of level completion
            await channel.send_message(
                sender=BOT_ID,
                message=f"Le Train de la Hype {special_text}{shared_text}à évolué! Nous sommes à {self.hype_train_level_complete}% dans le niveau {train_level}!",
            )

            alert_message = {
                "type": "hype_train_start",
                "is_shared": is_shared,
                "train_type": payload.type,
                "level": train_level,
            }

            self.socket.send("new_alert_bot", alert_message)

    @commands.Component.listener()
    async def event_hype_train_end(self, payload: twitchio.HypeTrainEnd) -> None:
        print("Received event : Hype Train ended")
        channel = payload.broadcaster
        train_level = payload.level
        self.hype_train_level = -1
        shared_text = ""
        is_shared = payload.shared_train
        if is_shared:
            shared_text = "Partagé "
        special_text = ""
        if payload.type == "golden_kappa":
            special_text = "Kappa Doré "
        elif payload.type == "treasure":
            special_text = "Trésor "
        elif payload.type == "mythic":
            special_text = "Mythique "
        train_countdown_until = payload.cooldown_until
        diff = (
            datetime.fromtimestamp(train_countdown_until.timestamp()) - datetime.now()
        )
        secs = int(diff.total_seconds())
        mins = int(secs // 60)
        await channel.send_message(
            sender=BOT_ID,
            message=f"Le Train de la Hype {special_text}{shared_text}à quitté le chat... Nous avons atteint {self.hype_train_level_complete}% du niveau {train_level}! Le prochain Train de la Hype peut revenir dans {mins} minutes.",
        )

    @commands.Component.listener()
    async def event_shared_chat_begin(
        self, payload: twitchio.SharedChatSessionBegin
    ) -> None:
        print("Received event : Shared Chat session started")
        channel = payload.broadcaster
        host = payload.host
        participants = payload.participants
        participants_str = ""
        for participant in participants:
            if participant.id != host.id:
                if participant not in self.shared_chat_users:
                    self.shared_chat_users.append(participant)
                participants_str += (
                    f"{'' if len(participants_str) == 0 else ', '}{participant.name}"  # type: ignore
                )
        await channel.send_message(
            sender=BOT_ID,
            message=f"{host.display_name} à commencé une session de Chat Partagé avec {participants_str}.",
        )

    @commands.Component.listener()
    async def event_shared_chat_update(
        self, payload: twitchio.SharedChatSessionUpdate
    ) -> None:
        print("Received event : Shared Chat session updated")
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
                    f"{'' if len(participants_str) == 0 else ', '}{participant.name}"  # type: ignore
                )
            await channel.send_message(
                sender=BOT_ID,
                message=f"{host.name} à ajouté {abs(diff)} utilisateur dans le Chat Partagé. Les participants sont maintenant {participants_str}.",
            )
        else:  # If a user was removed
            self.shared_chat_users = []
            for participant in participants:
                if participant.id != host.id:
                    self.shared_chat_users.append(participant)
                participants_str += (
                    f"{'' if len(participants_str) == 0 else ', '}{participant.name}"  # type: ignore
                )
            await channel.send_message(
                sender=BOT_ID,
                message=f"{host.name} à retiré {diff} utilisateurs du Chat Partagé. Les participants sont maintenant {participants_str}.",
            )

    @commands.Component.listener()
    async def event_shared_chat_end(
        self, payload: twitchio.SharedChatSessionEnd
    ) -> None:
        print("Received event : Shared Chat session ended")
        channel = payload.broadcaster
        host = payload.host
        self.shared_chat_users = []
        await channel.send_message(
            sender=BOT_ID,
            message=f"{host.name} à terminé la session de Chat Partagé.",
        )

    @commands.Component.listener()
    async def event_goal_begin(self, payload: twitchio.GoalBegin) -> None:
        print("Received event : Goal Begin")
        channel = payload.broadcaster
        goal_name = payload.description
        goal_amount = payload.current_amount
        goal_end_amount = payload.target_amount
        goal_type = payload.type
        if goal_type in [
            "subscription_count",
            "new_subscription",
            "new_subscription_count",
        ]:
            goal_type = "subscription"
        elif goal_type in ["new_bit", "new_cheer"]:
            goal_type = "cheer"
        # await channel.send_message(
        #    sender=BOT_ID,
        #    message=f"A new {goal_type} goal has begun! {goal_name} ({goal_amount}/{goal_end_amount})",
        # )

    @commands.Component.listener()
    async def event_goal_progress(self, payload: twitchio.GoalProgress) -> None:
        print("Received event : Goal Begin")
        channel = payload.broadcaster
        goal_name = payload.description
        goal_amount = payload.current_amount
        goal_end_amount = payload.target_amount
        # await channel.send_message(
        #    sender=BOT_ID,
        #    message=f"{goal_name} updated! ({goal_amount}/{goal_end_amount})",
        # )

    @commands.Component.listener()
    async def event_goal_end(self, payload: twitchio.GoalEnd) -> None:
        print("Received event : Goal Begin")
        channel = payload.broadcaster
        goal_name = payload.description
        goal_end_amount = payload.target_amount
        goal_type = payload.type
        if goal_type in [
            "subscription_count",
            "new_subscription",
            "new_subscription_count",
        ]:
            goal_type = "subscribers"
        elif goal_type in ["new_bit", "new_cheer"]:
            goal_type = "bits"
        else:
            goal_type = "followers"
        # await channel.send_message(
        #    sender=BOT_ID,
        #    message=f"{goal_name} has been completed! ({goal_end_amount} {goal_type})",
        # )

    @commands.Component.listener()
    async def event_raid(self, payload: twitchio.ChannelRaid) -> None:
        print("Received event : New Raid")
        channel = payload.to_broadcaster
        raider = payload.from_broadcaster
        await channel.send_message(
            sender=BOT_ID,
            message=f"Merci beaucoup {raider.display_name} pour le raid de {payload.viewer_count} viewers !",
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
        }

        self.socket.send("new_alert_bot", alert_message)

    @commands.Component.listener()
    async def event_channel_update(self, payload: twitchio.ChannelUpdate) -> None:
        print("Received event : Channel Update")
        channel = payload.broadcaster
        category = payload.category_name
        title = payload.title
        # await channel.send_message(
        #    sender=BOT_ID,
        #    message=f"Updated title to \"{title}\" and category to \"{category}\"."
        # )

    @commands.Component.listener()
    async def event_shoutout_create(self, payload: twitchio.ShoutoutCreate) -> None:
        print("Received event : Created Shoutout")
        channel = payload.broadcaster
        shoutout_receiver = payload.to_broadcaster
        channel_info = await shoutout_receiver.fetch_channel_info()
        game = await channel_info.fetch_game()
        if game is not None:
            await channel.send_message(
                sender=BOT_ID,
                message=f'{shoutout_receiver.display_name} était en train de stream "{game.name}"! Si vous appréciez, vou devriez aller voir !',
            )
            return
        await channel.send_message(
            sender=BOT_ID,
            message=f"{shoutout_receiver.display_name} streamait pour {payload.viewer_count} viewers ! Bienvenue !",
        )

    @commands.Component.listener()
    async def event_automatic_redemption_add(
        self, payload: twitchio.ChannelPointsAutoRedeemAdd
    ) -> None:
        print("Received event : Auto Channel Point Redeemed")
        # channel = payload.broadcaster  # The channel it happened on
        # user = payload.user  # The user who redeemed this reward
        # reward = payload.reward  # The reward object
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

    @commands.Component.listener()
    async def event_custom_redemption_add(
        self, payload: twitchio.ChannelPointsRedemptionAdd
    ) -> None:
        print("Received event : Channel Point Redeemed")
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

    @commands.Component.listener()
    async def event_ad_break(self, payload: twitchio.ChannelAdBreakBegin) -> None:
        print("Received event : Ad Break Starts")
        channel = payload.broadcaster
        started_at = payload.started_at
        duration = payload.duration

        if self.message_sent >= 5:
            await channel.send_message(
                sender=BOT_ID,
                message=f"⚠️ Une pub de {self.format_time_since(datetime.fromtimestamp(started_at.timestamp() + duration), datetime.now())} à commencé. ⚠️",
            )
            self.message_sent = 0


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
        LOGGER.warning("Shutting down due to KeyboardInterrupt")


if __name__ == "__main__":
    main()
