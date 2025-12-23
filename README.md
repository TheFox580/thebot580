# TheBot580

## **WARNING**! THIS IS THE V2 VERISON OF THE BOT, USING THE LATEST VERSION OF ALL APIs

### If you plan on using this version, make sure all plugins (TwitchIO, Azure, PyGame, OBS Websockets, and requests) are up to date (run `pip install -r requirements.txt` to install and update everything)

This is a fork of [Babagaboosh ↗](https://www.github.com/DougDougGithub/Babagaboosh), changed as a bot for [TheFox580 ↗](https://www.twitch.tv/thefox580), [TheAlt580 ↗](https://www.twitch.tv/thealt580), [TheEvents580 ↗](https://www.twitch.tv/theevents580) and [LeRenard580 ↗](https://www.twitch.tv/lerenard580)

This code uses the TwitchIO **3.1.0** Library, Azure's Text-To-Speech fonctionnality, PyGame's Audio Library and OBS Websockets.

## Here are all of TheBot580's functionnality

### Moderator Bot

**TheBot580 will detect bots based on a banned word list, and if **ANY** of these words are detected in the message, the user will be permanently banned from the channel**

---

### Support for TTS message

**TheBot580 will by default enable Text-To-Speech messages, meaning that any safe messages will be read out loud by the progam!**

> *Note* : This setting can be disabled by putting `TTS = False` at [*this line ↗*](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L296)

> *Tip* : If you're streaming with TTS Enabled, you can use a plugin like [*win-capture-audio ↗*](https://github.com/bozbez/win-capture-audio) and make it output `python.exe` to have TTS on a separate audio channel!

> *Tip* : With this plugin and the [*Move plugin ↗*](https://github.com/exeldro/obs-move-transition), you can make a png move like TheBot580 was actually talking with the use of [*OBS Websockets ↗*](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L26)!

---

### Support for Emote Combos

**TheBot580 will automatically count how many times in a row an emote has been used, and will send a message if the emote has been said at least 5 times!**

> *Note* : Although Better TTV Emotes are being automatically added, I haven't implemented custom support for the other platforms yet, so you may [*enter your own emotes here ↗*](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L149)

> *Tip* : You can modify the message that the bot sends in chat [*to your liking here ↗*](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L346)

---

### Use advanced commands

**Thanks to TwitchIO 3.0.0, we now have more control on how to use bot commands! [*You can check some I have already set up here ↗*](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L416)!**

---

### Support for any streamer

> **Warning** : Any checked interaction requires you to be either an **Affiliated or Partenred streamer**

> *Tip* : *🆙* means this interaction has been updated & *🆕* means this interaction has been added

> *🆙* : The wait time for the bot to start has been removed by `2*<number of subscriptions>`!

**TheBot580 uses EventSub to allow for interactive moments with chat! So far, TheBot580 interacts with :**

* [ ] [**New Follower ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L529)
* [x] [**New Subscriber ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L538)
* [x] [**Resubscriptions ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L549)
* [x] [**Normal / Anonymous Gifted Subscriptions ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L565)
* [x] [**Normal / Anonymous Cheer Message ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L584)
* [x] [**Prediction Begins ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L607)
* [x] [**Prediction Locks ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L625)
* [x] [**Prediction Ends ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L650)
* [x] [**Poll Begins ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L682)
* [x] [**Poll Ends ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L700)
* [ ] Stream [**Starts ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L717) and [**Ends ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L729)
* [x] [**Golden / Treasure (*🆕*) / Normal (Shared *🆕*) Hype Train Begins ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L741)
* [x] [**Golden / Treasure (*🆕*) / Normal (Shared *🆕*) Hype Train Progress ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L764)
* [x] [**Golden / Treasure (*🆕*) / Normal (Shared *🆕*) Hype Train Ends ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L788)
* [ ] [**Shared Chat Collaboration Begins ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L812)
* [ ] [**Shared Chat Collaboration Updates (User join / left) ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L829)
* [ ] [**Shared Chat Collaboration Ends ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L859)
* [x] [**Follower / Subcription / Cheer Goal Begins ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L870) *🆙*
* [x] [**Follower / Subcription / Cheer Goal Progress ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L887) *🆙*
* [x] [**Follower / Subcription / Cheer Goal Reached ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L899) *🆙*
* [ ] [**Raid ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L917) *(Gives an automatic shoutout)*
* [ ] [**Title & Category Update ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L931)
* [ ] [**Shoutout Created (*🆕*) ↗**](https://github.com/TheFox580/thebot580/blob/main/twitch_bot.py#L942)
* More to come...

> *Note* : If you don't know how to start TheBot580 (especially for the 1st time), read the [*TwitchIO tutorial ↗*](https://twitchio.dev/en/latest/getting-started/quickstart.html) on how to start the bot!

## IT IS MORE THAN ADVISED TO KNOW PYTHON (otherwise you can't understand what this code does and this is kinda dumb...)

### BEFORE STARTING THE CODE, PLEASE READ (and modify, if you want) `tts.py`, `websockerts_auth.py` AND `twitch_bot.py`

### CREATE A `keys.py` WITH AT LEAST 7 VARIABLES NAMED

* `AZURE_TTS_KEY`
* `AZURE_TTS_REGION`
* `AZURE_TTS_VOICE` ([*Click here to see all voices available ↗*](https://aka.ms/speech/voices/neural))
* `TWITCH_BOT_CLIENT_ID`
* `TWITCH_BOT_CLIENT_SECRET`
* `OWNER_ID`
* `BOT_ID`

### THESE KEYS MUST EXIST WITHIN `keys.py`

Example of `keys.py`:

![10 lines, most of them having a key with an example of what is meant to be in it.](keys.png)

## ALSO YOU NEED OBS TO BE OPEN FOR THE BOT TO WORK BECAUSE IT CONNECTS TO OBS THROUGH WEBSOCKETS
