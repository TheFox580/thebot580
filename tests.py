import requests

from keys import TWITCH_BOT_CLIENT_ID, TWITCH_BOT_CLIENT_SECRET

emotes: dict[str, dict[str, str]] = {"7TV": {}, "FFZ": {}, "BTTV": {}, "Twitch": {}}


def getEmotes(platform, url):
    if platform != "Twitch":
        req = requests.get(url)
        res = req.json()
        current_set = {}
        if platform == "7TV":
            for emote in res["emotes"]:
                # interesting = emote["data"]
                # for key, value in interesting.items():
                #    print(key + ":", value)
                current_set[emote["data"]["name"]] = (
                    "https:"
                    + emote["data"]["host"]["url"]
                    + "/"
                    + emote["data"]["host"]["files"][0]["name"]
                )

        if platform == "FFZ":
            emoteSet = res["room"]["set"]
            currentSet = res["sets"][str(emoteSet)]
            for emote in currentSet["emoticons"]:
                current_set[emote["name"]] = emote["urls"]["2"]

        if platform == "BTTV":
            emotes_list = res["sharedEmotes"]
            for emote in emotes_list:
                current_set[emote["code"]] = (
                    "https://cdn.betterttv.net/emote/" + emote["id"] + "/2x"
                )

        emotes[platform].update(current_set)

    elif platform == "Twitch":
        current_set = {}

        params = {
            "client_id": TWITCH_BOT_CLIENT_ID,
            "client_secret": TWITCH_BOT_CLIENT_SECRET,
            "grant_type": "client_credentials",
        }

        req = requests.post("https://id.twitch.tv/oauth2/token", params=params)

        res = req.json()
        access_token = res["access_token"]

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Client-Id": TWITCH_BOT_CLIENT_ID,
        }

        req = requests.get(
            url,
            headers=headers,
        )

        res = req.json()
        for emote in res["data"]:
            link = emote["images"]["url_2x"]
            if "animated" in emote["format"]:
                link = link.replace("/static/", "/animated/")
            current_set[emote["name"]] = link

        emotes[platform].update(current_set)


getEmotes("7TV", "https://api.7tv.app/v3/emote-sets/global")
getEmotes("7TV", "https://api.7tv.app/v3/emote-sets/01G0WKR3RR000C616F94Z7P2EQ")
getEmotes("FFZ", "https://api.frankerfacez.com/v1/room/id/126869447")
getEmotes("BTTV", "https://api.betterttv.net/3/cached/users/twitch/126869447")
getEmotes("Twitch", "https://api.twitch.tv/helix/chat/emotes/global")
getEmotes("Twitch", "https://api.twitch.tv/helix/chat/emotes?broadcaster_id=126869447")

print(emotes)
