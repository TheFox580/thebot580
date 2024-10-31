# TheBot580
This is a fork of [Babagaboosh](https://www.github.com/DougDougGithub/Babagaboosh), changed as a bot for [TheFox580](https://www.twitch.tv/thefox580), [TheAlt580](https://www.twitch.tv/thealt580), [TheEvents580](https://www.twitch.tv/theevents580) and [LeRenard580](https://www.twitch.tv/lerenard580)

This code uses the TwitchIO Libraty, ElevenLabs' Text-To-Speech fonctionnality and PyGame's Audio Library.
It also acts as a moderator bot, as it contains a list of banned word in the chat, that will ban bots automatically.

## IT IS MORE THAN ADVISED TO KNOW PYTHON (otherwise you can't understand what this code does and this is kinda dumb...)

### BEFORE STARTING THE CODE, PLEASE READ (and modify, if you want) eleven_labs.py, websockerts_auth.py AND twitch_bot.py
---
### CREATE A keys.py WITH 4 VARIABLES NAMED:
- ELEVEN_LABS_KEY_1
- ELEVEN_LABS_KEY_2
- ELEVEN_LABS_KEY_3
- TWITCH_BOT_TOKEN
### THESE 4 KEYS MUST EXIST WITHIN keys.py. IF THE 3 'ELEVEN_LABS_KEY' HAVE THE SAME VALUE, IT'S FINE, BUT THE MORE KEYS YOU HAVE, THE BETTER IT WILL BE

Example of keys.py:

![4 lines, each of them having a key masked by white drawing.](keys.png)

## ALSO YOU NEED OBS TO BE OPEN FOR THE BOT TO WORK BECAUSE IT CONNECTS TO OBS THROUGH WEBSOCKETS!