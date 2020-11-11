# -*- coding: utf-8 -*-
'''
The MIT License (MIT)

Copyright (c) 2020 RocketRace

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
'''

import asyncio
from typing import *
import discord
from discord.ext import commands, tasks
from collections import namedtuple
from datetime import datetime, timedelta

__version__ = "0.1.0a" # for setup.py

_VersionInfo = namedtuple("_VersionInfo", "major minor micro releaselevel serial")
version_info = _VersionInfo(major=0, minor=1, micro=0, releaselevel="alpha", serial=0)

__all__ = ("DefaultBouncer",)

class DefaultBouncer(commands.Cog):
    '''A "bouncer" used to leave guilds automatically under certain criteria.

    This class is a subclass of :class:`commands.Cog`, meaning it can be loaded
    into a :class:`discord.ext.commands.Bot` using `bot.load_cog`. In addition, 
    it can be customized to implement anything a :class:`commands.Cog` could 
    implement, such as commands to manage its behavior.

    Note:
        If your bot is disconnected from the Discord gateway due to a network
        disconnection or otherwise, this cog will not be able to leave any guilds
        during that time. It is recommended to manually set your bot private from
        the developer dashboard instead, if this risk is too significant.

    Attributes
    ------------
    bot: :class:`discord.ext.commands.Bot`
        The bot instance this cog is associated with.

    max_guilds: :class:`int`
        The maximum number of guilds the bot is allowed to join. By default, this is 
        set to 95 guilds.
        
        Whenever a new guild is joined above this limit, that guild is immediately left,
        and :meth:`self.on_guild_limit_reach` is called.

        Note:
            Under very rare circumstances it is possible that two or more guilds are joined 
            in quick succession before the bot can leave them, which may lead the guild count
            to be exceeded temporarily. As a result, it is recommended to leave a "safety net"
            in your bot's maximum guild count to account for this behavior. The default limit
            of 95 ensures that multiple guilds joined simultaneously will not cause the bot to 
            exceed 99 guilds, but this value may be adjusted as necessary.
    
    min_member_count: Optional[:class:`int`]
        The minimum member count enforced on guilds. If a guild does not have this many
        members, the bot will leave that guild. See :meth:`self.leave_criteria` for more 
        information on which criteria are used to determine whether a guild should be left.
        Defaults to `None`.

        Note:
            This requires the :meth:`discord.Intents.members` intent to function properly
            with periodic guild checks. Without this intent, the :prop:`member_count` field
            of guilds will not be up to date. However, newly joined guilds will always have 
            this field up to date.

    max_member_count: Optional[:class:`int`]
        The maximum member count enforced on guilds. If a guild has more members than this, 
        the bot will leave that guild. See :meth:`self.leave_criteria` for more 
        information on which criteria are used to determine whether a guild should be left.
        Defaults to `None`.

        Note:
            This requires the :meth:`discord.Intents.members` intent to function properly
            with periodic guild checks. Without this intent, the :prop:`member_count` field
            of guilds will not be up to date. However, newly joined guilds will always have 
            this field up to date.

    max_bot_ratio: Optional[:class:`float`]
        The maximum proportion of guild members that are allowed to be bots. If a guild has
        more bots than specified here, this bot will leave that guild. See 
        :meth:`self.leave_criteria` for more information on which criteria are used to
        determine whether a guild should be left. Defaults to `None`.

        Note:
            This requires the :meth:`discord.Intents.members` intent to function.
            If it is not provided in the bot constructor and the developer dashboard, the
            bot will not have access to the member lists of guilds, and therefore cannot
            count the number of bots in a guild.

    min_guild_age: Optional[:class:`datetime.timedelta`]
        The minimum age enforced on guilds. If a guild was created more recently than this,
        the bot will leave that guild. See :meth:`self.leave_criteria` for more 
        information on which criteria are used to determine whether a guild should be left.
        Defaults to `None`.

    frequency: Optional[Union[:class:`datetime.timedelta`, :class:`float`]]
        How often the bot should check already joined guilds for eligibility.
        If this is set to `None`, the bot will not periodically check existing guilds for this leave criteria. 
        If this is a :class:`datetime.timedelta`, it is interpreted as the duration between waves of checks.
        If this is a :class:`float`, it is interpreted as the number of seconds between waves of checks.
    '''
    
    def __init__(
        self,
        bot: commands.Bot,
        *,
        max_guilds: int=58,
        min_members: Optional[int]=None,
        max_members: Optional[int]=None,
        max_bot_ratio: Optional[float]=None,
        min_guild_age: Optional[timedelta]=None,
        frequency: Optional[Union[timedelta, int]]=None,
    ):
        self.bot = bot
        self.max_guilds = max_guilds
        self.min_members = min_members
        self.max_members = max_members
        self.max_bot_ratio = max_bot_ratio
        self.min_guild_age = min_guild_age
        self.frequency = frequency

        self._task = None
        if self.frequency is not None:
            if isinstance(self.frequency, timedelta):
                wrapper = tasks.loop(seconds=self.frequency.total_seconds())
            elif isinstance(self.frequency, int):
                wrapper = tasks.loop(seconds=self.frequency)
            else:
                raise TypeError("frequency must be a timedelta or float")
            self._task = wrapper(self._check_guilds())
            self._task.start()

    async def _check_guilds(self):
        for guild in self.bot.guilds:
            if await self.leave_criteria(guild):
                await self.before_leave(guild, new=False)
                await guild.leave()
                await self.after_leave(guild, new=False)

    async def leave_criteria(self, guild: discord.Guild) -> bool:
        '''Performs the logic determining whether a guild should be left. 
        
        This typically shouldn't be overridden.
        
        Returns `True` if :param:`guild` fits any of the criteria for rejection 
        and is not whitelisted. Returns `False` otherwise.

        The criteria, if specified, are:
        * The member count (both mimimum and maximum)
        * The proportion of bots to members in the guild (maximum)
        * The guild age (mimimum)
        * Custom criteria defined in :meth:`self.extra_criteria`

        If any of these limits are broken, and :meth:`self.whitelisted` returns 
        `False`, this function will return `True`.

        Parameters
        -----------
        guild: :class:`discord.Guild`
            The guild being checked.
        '''
        if self.whitelisted(guild):
            return False
        return any([
            # guild members
            self.min_members is not None and 
                guild.member_count < self.min_members,
            self.max_members is not None and 
                guild.member_count > self.max_members,
            self.max_bot_ratio is not None and 
                len([None for m in guild.members if m.bot]) / guild.member_count > self.max_bot_ratio,
            # guild itself
            self.min_guild_age is not None and 
                datetime.utcnow() - guild.created_at > self.min_guild_age,
            # Custom checks
            await self.extra_criteria(guild),
        ])

    async def whitelisted(self, guild: discord.Guild) -> bool:
        '''A method to determine whether a guild should not be left,
        even if it fits leaving criteria.
        
        This should be overridden to whitelist certain guilds.

        Returns `True` if the guild is whitelisted, and `False` otherwise.

        By default, this returns `False`.

        Parameters
        ----------
        guild: :class:`discord.Guild`
            The guild being checked.
        '''
        return False

    async def extra_criteria(self, guild: discord.Guild) -> bool:
        '''Contains custom logic used to determine whether a guild should be left.

        This should be overridden to add any additional criteria to check guilds on.
        
        Returns `True` if the guild should be left, and `False` otherwise.

        By default, this returns `False`.

        Parameters
        -----------
        guild: :class:`discord.Guild`
            The guild being checked.
        '''
        return False

    async def before_leave(self, guild: discord.Guild, *, new: bool):
        '''This coroutine is executed when a guild is determined to be ineligible and is about to be left.
        
        This will not be called if the bot meets or exceeds its :attribute:`max_guilds` count as a result of this guild.
        Instead, :meth:`self.on_guild_limit_reached` will be called.

        Parameters
        ----------
        guild: :class:`discord.Guild`
            The guild that is about to be left.
        new: :class:`bool`
            Whether or not the guild was just joined. If `False`, this means that an existing guild met the leave criteria.
        '''

    async def after_leave(self, guild: discord.Guild, *, new: bool):
        '''This coroutine is executed after a guild has successfully been left.

        This will always be called after either :meth:`self.before_leave` or :meth:`on_guild_limit_reached`.

        Parameters
        -----------
        guild: :class:`discord.Guild`
            The guild that was just left.
        new: :class:`bool`
            Whether or not the guild was just joined. If `False`, this means that an existing guild met the leave criteria.
        '''

    async def on_guild_limit_reached(self, guild: discord.Guild):
        '''This coroutine is executed when the bot's guild count is greater than or equal to :attribute:`self.max_guilds`
        as a result of joining :param:`guild`.
        
        This event is called regardless of whether a guild is eligible.

        Parameters
        -----------
        guild: :class:`discord.Guild`
            The guild that was just joined.

            Note:
                The bot may or may not be in the guild when this is executed. To determine whether
                or the bot has already left this guild, check whether the value of :attr:`guild.me` is `None`.
        '''

    @commands.Cog.listener("on_guild_join")
    async def _on_guild_join(self, guild: discord.Guild):
        if len(self.bot.guilds) >= self.max_guilds:
            await self.on_guild_limit_reached(guild)
            await guild.leave()
            await self.after_leave(guild, new=True)
        elif await self.leave_criteria(guild):
            await self.before_leave(guild, new=True)
            await guild.leave()
            await self.after_leave(guild, new=True)

# This function is called whenever this module is loaded using `bot.load_extension("dbouncer")`
def setup(bot: commands.Bot):
    bot.add_cog(DefaultBouncer(bot))
