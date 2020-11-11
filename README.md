# dbouncer

Since 7th October 2020, unverified bots must maintain a guild count of 99 or fewer 
to access privileged intents, which are necessary for member & presence data. 
This module provides a robust API to automatically manage your bot's guild count by 
leaving guilds matching certain customizable criteria.

## Installation

From [https://pypi.org/project/dbouncer/](PyPi):

```bash
pip install dbouncer
```

Development version:

```bash
pip install -U git+https://github.com/RocketRace/dbouncer
```

## Usage

The module can be enabled out-of-the-box using

```py
bot.load_extension("dbouncer")
```

In this mode, the bot will unconditionally leave any new guilds joined after the guild count hits 98.

You can customize the behavior of dbouncer and hook into the events by inheriting from the `dbouncer.DefaultBouncer` cog:

```py
import discord
from discord.ext import commands
import dbouncer

class MyBouncer(dbouncer.DefaultBouncer):
    async def whitelisted(self, guild):
        return guild.id == 360268483197665282
    
    async def before_leave(self, guild):
        await guild.owner.send("This guild does not have enough users, or has too many bots!")
    
    async def after_leave(self, guild):
        print("Left guild {0} (ID: {0.id})".format(guild))

# The members intent is required to check how many bots are in a guild
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="$", intents=intents)

# Other parameters are detailed in the documentation
bot.add_cog(MyBouncer(bot,
    min_member_count=10,
    max_bot_ratio=0.5,
))
```