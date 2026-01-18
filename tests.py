import requests

from keys import OWNER_ID

def get7TVEmotes(broadcaster_id:str):
    emotes : list[str] = []

    req = requests.get(f'https://api.7tv.app/v3/users/twitch/{broadcaster_id}')
    res = req.json()
    emote_set = res["emote_set_id"]

    req = requests.get(f'https://api.7tv.app/v3/emote-sets/{emote_set}')
    res = req.json()
    for emote in res["emotes"]:
        emotes.append(emote["name"])
    return emotes

print(get7TVEmotes(OWNER_ID))