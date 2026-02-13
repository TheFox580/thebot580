import requests

from keys import OWNER_ID, TWITCH_BOT_CLIENT_ID, TWITCH_BOT_CLIENT_SECRET


    
def getTwitchEmotes(broadcaster_id:str) -> tuple[list[str], list[str]]:
    emotes : tuple[list[str], list[str]] = ([], [])
    params = {"client_id": TWITCH_BOT_CLIENT_ID, "client_secret": TWITCH_BOT_CLIENT_SECRET, "grant_type":"client_credentials"}
    req = requests.post("https://id.twitch.tv/oauth2/token", params=params)
    if not req.ok:
        raise requests.HTTPError
    res = req.json()
    access_token = res["access_token"]
    headers = {"Authorization": f"Bearer {access_token}", "Client-Id": TWITCH_BOT_CLIENT_ID}
    req = requests.get(f'https://api.twitch.tv/helix/chat/emotes?broadcaster_id={broadcaster_id}', headers=headers)
    if not req.ok :
        raise requests.HTTPError
    
    res = req.json()
    emote1 = []
    for emote in res["data"]:
        emote1.append(emote["name"])
    req = requests.get(f'https://api.twitch.tv/helix/chat/emotes/global', headers=headers)
    if not req.ok :
        raise requests.HTTPError
    
    res = req.json()
    emote2 = []
    for emote in res["data"]:
        emote2.append(emote["name"])
    emotes : tuple[list[str], list[str]] = (emote1, emote2)
    return emotes

print(getTwitchEmotes(OWNER_ID))