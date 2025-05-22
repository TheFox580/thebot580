# TheBot580

## This page is version 1.0 of TheBot580, and has been deprecated, for an updated version of the code, [visit this page ↗](https://github.com/TheFox580/thebot580/tree/2.0)

This is a fork of [Babagaboosh](https://www.github.com/DougDougGithub/Babagaboosh), changed as a bot for [TheFox580](https://www.twitch.tv/thefox580), [TheAlt580](https://www.twitch.tv/thealt580), [TheEvents580](https://www.twitch.tv/theevents580) and [LeRenard580](https://www.twitch.tv/lerenard580)

This code uses the TwitchIO **3.0.0 (beta 4)** Library, ElevenLabs' Text-To-Speech fonctionnality and PyGame's Audio Library.
It also acts as a moderator bot, as it contains a list of banned word in the chat, that will ban bots automatically.

## IT IS MORE THAN ADVISED TO KNOW PYTHON (otherwise you can't understand what this code does and this is kinda dumb...)

### BEFORE STARTING THE CODE, PLEASE READ (and modify, if you want) eleven_labs.py, websockerts_auth.py AND twitch_bot.py

### CREATE A keys.py WITH AT LEAST 5 VARIABLES NAMED

- ELEVEN_LABS_KEY
- TWITCH_BOT_CLIENT_ID
- TWITCH_BOT_CLIENT_SECRET
- OWNER_ID
- BOT_ID

### THESE KEYS MUST EXIST WITHIN keys.py

Example of keys.py:

![5 lines, each of them having a key with an example of what is meant to be in it.](keys.png)

## ALSO YOU NEED OBS TO BE OPEN FOR THE BOT TO WORK BECAUSE IT CONNECTS TO OBS THROUGH WEBSOCKETS
