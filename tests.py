import requests

from keys import OWNER_ID

def getBTTVEmotes(broadcaster_id:str):
    emotes : list[str] = []
    req = requests.get(f'https://api.betterttv.net/3/cached/users/twitch/{broadcaster_id}')
    res = req.json()
    for emote in res["sharedEmotes"]:
        emotes.append(emote["code"])
    return emotes

print(getBTTVEmotes(OWNER_ID))