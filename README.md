# TheBot580

## **WARNING**! THIS IS THE V2 VERISON OF THE BOT, USING THE LATEST VERSION OF ALL APIs!

### If you plan on using this version, make sure all plugins (TwitchIO, ElevenLabs, PyGame, OBS Websockets, and requests) are up to date (run `pip install -r requirements.txt` to install and update everything)

This is a fork of [Babagaboosh ↗](https://www.github.com/DougDougGithub/Babagaboosh), changed as a bot for [TheFox580 ↗](https://www.twitch.tv/thefox580), [TheAlt580 ↗](https://www.twitch.tv/thealt580), [TheEvents580 ↗](https://www.twitch.tv/theevents580) and [LeRenard580 ↗](https://www.twitch.tv/lerenard580)

This code uses the TwitchIO **3.0.0 (beta 4)** Library, ElevenLabs **2.0.0**' Text-To-Speech fonctionnality, PyGame's Audio Library and OBS Websockets.

## Here are all of TheBot580's functionnality:

### Moderator Bot

**TheBot580 will detect bots based on a banned word list, and if **ANY** of these words are detected in the message, the user will be permanently banned from the channel**

---

### Support for TTS message

**TheBot580 will by default enable Text-To-Speech messages, meaning that any safe messages will be read out loud by the progam!**

> *Note* : This setting can be disabled by putting `TTS = False` at [*this line ↗*](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L296)

> *Tip* : If you're streaming with TTS Enabled, you can use a plugin like [*win-capture-audio ↗*](https://github.com/bozbez/win-capture-audio) and make it output `python.exe` to have TTS on a separate audio channel!

> *Tip* : With this plugin and the [*Move plugin ↗*](https://github.com/exeldro/obs-move-transition), you can make a png move like TheBot580 was actually talking with the use of [*OBS Websockets ↗*](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L26)!

---

### Support for Emote Combos

**TheBot580 will automatically count how many times in a row an emote has been used, and will send a message if the emote has been said at least 5 times!**

> *Note* : Although Better TTV Emotes are being automatically added, I haven't implemented custom support for the other platforms yet, so you may enter your own emotes [*here ↗*](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L149)

> *Tip* : You can modify the message that the bot sends in chat to your liking [*here ↗*](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L346)

---

### Use advanced commands

**Thanks to TwitchIO 3.0.0, we now have more control on how to use bot commands! You can check some I have already set up [here ↗](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L416)!**

---

### Support for any streamers!

> **Warning**: Any checked interaction requires you to be either an **Affiliated or Partenred streamer**

**TheBot580 uses EventSub to allow for interactive moments with chat! So far, TheBot580 interacts with :**

* [ ] [**New Follower ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L520)
* [x] [**New Subscriber ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L529)
* [x] [**Resubscriptions ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L540)
* [x] [**Normal / Anonymous Gifted Subscriptions ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L556)
* [x] [**Normal / Anonymous Cheer Message ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L569)
* [x] [**Prediction Begins ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L589)
* [x] [**Prediction Locks ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L606)
* [x] [**Prediction Ends ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L628)
* [x] [**Poll Begins ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L656)
* [x] [**Poll Ends ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L674)
* [ ] Stream [**Starts ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L691) and [**Ends ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L703)
* [x] [**Golden / Normal Hype Train Begins ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L715) (Treasure Hype Trains are not supported by the Twitch API yet)
* [x] [**Golden / Normal Hype Train Progress ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L733) (Treasure Hype Trains are not supported by the Twitch API yet)
* [x] [**Golden / Normal Hype Train Ends ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L752) (Treasure Hype Trains are not supported by the Twitch API yet)
* [ ] [**Shared Chat Collaboration Begins ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L774)
* [ ] [**Shared Chat Collaboration Updates (User join / left) ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L790)
* [ ] [**Shared Chat Collaboration Ends ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L817)
* [x] [**Follower / Subcription / Cheer Goal Begins ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L828)
* [x] [**Follower / Subcription / Cheer Goal Progress ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L845)
* [x] [**Follower / Subcription / Cheer Goal Reached ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L857)
* [ ] [**Raid ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L875) (Gives an automatic shoutout)
* [ ] [**Title & Category Update ↗**](https://github.com/TheFox580/thebot580/blob/2.0/twitch_bot.py#L889)
* More to come...

> *Note* : If you don't know how to start TheBot580 (especially for the 1st time), read the [*TwitchIO tutorial ↗*](https://twitchio.dev/en/latest/getting-started/quickstart.html) on how to start the bot!

## IT IS MORE THAN ADVISED TO KNOW PYTHON (otherwise you can't understand what this code does and this is kinda dumb...)

### BEFORE STARTING THE CODE, PLEASE READ (and modify, if you want) eleven_labs.py, websockerts_auth.py AND twitch_bot.py

### CREATE A keys.py WITH AT LEAST 5 VARIABLES NAMED

* `ELEVEN_LABS_KEY`
* `TWITCH_BOT_CLIENT_ID`
* `TWITCH_BOT_CLIENT_SECRET`
* `OWNER_ID`
* `BOT_ID`

### THESE KEYS MUST EXIST WITHIN keys.py

Example of keys.py:

![5 lines, each of them having a key with an example of what is meant to be in it.](keys.png)

## ALSO YOU NEED OBS TO BE OPEN FOR THE BOT TO WORK BECAUSE IT CONNECTS TO OBS THROUGH WEBSOCKETS
