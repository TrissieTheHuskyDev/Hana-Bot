import discord
from discord.ext import commands, tasks
import datetime
import CustomTools


def setup(bot: commands.Bot):
    """
    Necessary function for a cog that initialize the Mute class.

    Args:
        bot (commands.Bot): passing in bot for class initialization

    Returns:
        None
    """
    bot.add_cog(Mute(bot))
    print("Loaded Cog: Mute")


def teardown(bot: commands.Bot):
    """
    Function to be called upon Cog unload, in this case, it will print message in CMD.

    Args:
        bot (commands.Bot): passing in bot reference for unload.

    Returns:
        None
    """
    bot.remove_cog("Mute")
    print("Unloaded Cog: Mute")


async def remove_mute(bot: commands.Bot, guild: int, target: int, reason: str = "Mute time expired."):
    """
    Function that passes in required parameters to remove mute role from target.

    Args:
        bot(commands.Bot): pass in bot reference
        guild(int): the guild which the target wants to be unmuted
        target(int): target ID
        reason(str): unmute reasoning

    Returns:
        None
    """
    mute = bot.get_cog('Mute')
    try:
        role = bot.get_guild(guild).get_role(mute.roles[guild])
        if not role:
            bot.mongodb["mute_time"].delete_many({"guild_id": guild})
            bot.mongodb["mute_role"].delete_many({"guild_id": guild})
            mute.roles.pop(guild)
            mute.timers.pop(guild)
            return
    except KeyError:
        mute.timers.pop(guild)
        bot.mongodb["mute_time"].delete_many({"guild_id": guild})
        return
    else:
        member = bot.get_guild(guild).get_member(target)
        if member:
            await member.remove_roles(role, reason=reason)
            bot.mongodb["mute_time"].delete_one({"guild_id": guild, "user_id": target})
        mute.timers[guild].pop(target)


class MuteTimer:
    """
    Class responsible for storing mute information.

    Attributes:
        start(datetime.datetime): time the mute started in bot's memory
        guild(int): guild ID where the mute took place
        member(int): user ID of the mute
        ends(float): after what time will the mute end
        destination(datetime.datetime): estimated time when the mute ends
    """
    def __init__(self, bot: commands.Bot, guild: int = None, uid: int = None, diff: float = None, pack=None,
                 initial: datetime.datetime = None):
        """
        Constructor for MuteTimer class.

        Args:
            bot(commands.Bot): bot reference
            guild(int): guild ID
            uid(int): user ID
            diff(float): mute duration
            pack: mongoDB input if any
            initial(datetime.datetime): the initial mute time if any
        """
        if not initial:
            self.start = datetime.datetime.now()
        else:
            self.start = initial
        self.bot = bot
        if not pack:
            self.guild = guild
            self.member = uid
            self.ends = diff
        else:
            self.guild = pack['guild_id']
            self.member = pack['user_id']
            if pack['destination'] > self.start:
                self.ends = float((pack['destination'] - self.start).total_seconds())
            else:
                raise ValueError("Time input from package is already passed.")
        self.destination = (self.start + datetime.timedelta(seconds=self.ends))
        self.the_timer.change_interval(seconds=self.ends)
        self.the_timer.start()

    def terminate(self):
        """
        Method of MuteTimer class that terminate the loop task.

        Returns:
            None
        """
        self.the_timer.cancel()

    @tasks.loop(count=2)
    async def the_timer(self):
        """
        The task loop responsible for removing mute role automatically.

        Returns:
            None
        """
        if self.the_timer.current_loop == 1:
            try:
                await remove_mute(self.bot, self.guild, self.member)
            except discord.HTTPException:
                pass
            self.terminate()


class Mute(commands.Cog):
    """
    A class of Mute cmmands for Hana bot.

    Attributes:
        bot(commands.Bot): bot reference
        roles(dict): the mute roles assigned by servers
        timers(dict): in process mutes with MuteTimer
        units(dict): dictionary containing units to seconds
        converter(dict): dictionary containing alphabet to unit conversion
    """
    def __init__(self, bot: commands.Bot):
        """
        Constructor for Mute class.

        Args:
            bot(commands.Bot): pass in bot reference
        """
        self.bot = bot
        self.roles = {}
        self.timers = {}
        self.units = {"second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 604800}
        self.converter = {'s': 'second', 'm': 'minute', 'h': 'hour', 'd': 'day', 'w': 'week'}

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Bot event method for Mute class that updates the roles and timers dictionary. Required method for Hana bot.

        Returns:
            None
        """
        await self.update()

    async def update(self):
        """
        Async method for Mute class that will update roles and timers data from database.

        Returns:
            None
        """
        self.roles = {}
        data = self.bot.mongodb["mute_role"].find({})
        for i in data:
            self.roles.update({i['guild_id']: i['role_id']})
        data = self.bot.mongodb['mute_time'].find({})
        self.timers = {}
        for i in data:
            try:
                role = self.bot.get_guild(i['guild_id']).get_role(self.roles[i['guild_id']])
                if not role:
                    self.bot.mongodb["mute_role"].delete_many({"guild_id": i['guild_id']})
                    self.bot.mongodb["mute_time"].delete_many({"guild_id": i['guild_id']})
                    self.roles.pop(i['guild_id'])
                    self.timers.pop(i['guild_id'])
                    continue
            except KeyError:
                continue
            else:
                if i['destination'] > datetime.datetime.now():
                    try:
                        self.timers[i['guild_id']].update({i['user_id']: MuteTimer(pack=i, bot=self.bot)})
                    except KeyError:
                        self.timers.update({i['guild_id']: {i['user_id']: MuteTimer(pack=i, bot=self.bot)}})
                else:
                    self.bot.mongodb["mute_time"].delete_one({"guild_id": i['guild_id'], "user_id": i['user_id']})
                    target = self.bot.get_guild(i['guild_id']).get_member(i['user_id'])
                    if target:
                        await target.remove_roles(role, reason="Mute timer expired (Might a late removal due to Cog "
                                                               "downtime).")

    # some time input code from: https://github.com/Twentysix26/26-Cogs/blob/master/remindme/remindme.py

    @commands.group(aliases=['mr'])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def mute_role(self, ctx: commands.Context):
        """
        Command for Mute class that displays the current setup mute role for the server if any.

        Args:
            ctx(commands.Context): pass in context for analysis and reply

        Returns:
            None
        """
        if not ctx.invoked_subcommand:
            nope = False
            try:
                data = self.roles[ctx.guild.id]
            except KeyError:
                nope = True
            else:
                role = ctx.guild.get_role(data)
                if not role:
                    self.bot.mongodb["mute_role"].delete_many({"guild_id": ctx.guild.id})
                    self.roles.pop(ctx.guild.id)
                    nope = True

            if nope:
                await ctx.send("This server have not set up a mute role.")
            else:
                await ctx.send(embed=discord.Embed(
                    title="Server Mute Role",
                    colour=0x22a6b3,
                    description=f"{role.mention}",
                    timestamp=ctx.message.created_at
                ))

    @mute_role.command()
    async def set(self, ctx: commands.Context, want: discord.Role):
        """
        Command for Mute class that sets the mute role for the server.

        Args:
            ctx(commands.Context): pass in context for process and reply
            want(discord.Role): the new mute role for the system

        Returns:
            None
        """
        try:
            self.roles[ctx.guild.id]
        except KeyError:
            self.bot.mongodb["mute_role"].insert_one({"guild_id": ctx.guild.id, "role_id": want.id})
            self.roles.update({ctx.guild.id: want.id})
        else:
            self.bot.mongodb["mute_role"].update_one({"guild_id": ctx.guild.id}, {"$set": {"role_id": want.id}})
            self.roles[ctx.guild.id] = want.id

        await ctx.send(embed=discord.Embed(
            title="Server Mute Role Updated",
            timestamp=ctx.message.created_at,
            colour=0xeccc68,
            description=f"`Updated to` {want.mention}"
        ))

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx: commands.Context, target: discord.Member, amount: int, de_time: str, *,
                   reason: str = "Not Specified"):
        """
        Command for mute class that applies the mute role to the target for a specified amount of time. Require
        manage roles permission to use.

        Args:
            ctx(commands.Context): pass in context for reply and analysis
            target(discord.Member): member to apply mute
            amount(int): duration to mute
            de_time(str): mute time description
            reason(str): reason for muting, default to "Not Specified" if no input.

        Returns:
            None
        """
        if target.bot:
            await ctx.send("Muting a bot?")
            return
        if target.id == ctx.author.id:
            await ctx.send("😅")
            return

        wrong = False
        try:
            if len(de_time) > 1:
                if de_time.endswith('s'):
                    de_time = de_time[:-1]
            else:
                de_time = self.converter[de_time]
        except KeyError:
            wrong = True

        if (de_time not in self.units) or wrong:
            await ctx.send("Unknown time unit input.")
            return

        try:
            role = ctx.guild.get_role(self.roles[ctx.guild.id])
            if not role:
                wrong = True
                self.bot.mongodb["mute_role"].delete_many({"guild_id": ctx.guild.id})
                self.roles.pop(ctx.guild.id)
        except KeyError:
            wrong = True

        if wrong:
            await ctx.send("Mute role have not been setup for this server.")
            return

        secs = amount * (self.units[de_time])
        dur = f"{amount} {de_time}"

        try:
            data = self.timers[ctx.guild.id][target.id]
        except KeyError:
            try:
                self.timers[ctx.guild.id]
            except KeyError:
                self.timers.update({ctx.guild.id: {}})
            await target.add_roles(role, reason=f"Mute applied for {amount} {de_time} by {ctx.author} for: \n{reason}.")
            self.timers[ctx.guild.id].update({target.id: MuteTimer(self.bot, ctx.guild.id, target.id, secs)})
            self.bot.mongodb["mute_time"].insert_one(
                {"guild_id": ctx.guild.id, "user_id": target.id,
                 "destination": self.timers[ctx.guild.id][target.id].destination}
            )
            await ctx.send(embed=discord.Embed(
                title="🔇 Muted",
                timestamp=ctx.message.created_at,
                colour=0x95afc0
            ).add_field(name="Member", value=target.mention).add_field(name="Duration", value=dur)
                           .add_field(name="Reason", value=reason).set_thumbnail(url=target.avatar_url))
            await self.tell(ctx, target, reason, dur)
        else:
            original = data.start
            o_time = data.ends + secs
            self.timers[ctx.guild.id][target.id].terminate()
            self.timers[ctx.guild.id].pop(target.id)
            self.timers[ctx.guild.id].update({target.id: MuteTimer(self.bot, ctx.guild.id, target.id, o_time,
                                                                   initial=original)})
            data = self.timers[ctx.guild.id][target.id]
            self.bot.mongodb["mute_time"].update_one(
                {"guild_id": ctx.guild.id, "user_id": target.id}, {"$set": {"destination": data.destination}}
            )
            await ctx.send(embed=discord.Embed(
                title="🔇 Mute Time Increased",
                timestamp=ctx.message.created_at,
                colour=0x95afc0
            ).add_field(name="Member", value=target.mention).add_field(name="Duration Increased By", value=dur)
                           .add_field(name="Reason", value=reason).set_thumbnail(url=target.avatar_url))
            await self.tell(ctx, target, reason, dur, True)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx: commands.Context, target: discord.Member, *, reason: str = "Not Specified"):
        """
        Command for Mute class that removes mute role from target if any and remove the mute timer associated with it.

        Args:
            ctx(commands.Context): pass in context for process
            target(discord.Member): unmute target
            reason(str): reason for the unmute, default to "Not Specified" if no reason given

        Returns:
            None
        """
        try:
            role_id = self.roles[ctx.guild.id]
        except KeyError:
            self.bot.mongodb["mute_time"].delete_many({"guild_id": ctx.guild.id})

            try:
                self.timers.pop(ctx.guild.id)
            except KeyError:
                pass
            await ctx.send("Something went wrong. Is the mute role setup?")
            return

        try:
            self.timers[ctx.guild.id][target.id]
        except KeyError:
            await ctx.send("That user is not muted or has a manual mute not applied by this bot.")
        else:
            self.timers[ctx.guild.id][target.id].terminate()
            role = ctx.guild.get_role(role_id)
            if not role:
                self.bot.mongodb["mute_role"].delete_many({"guild_id": ctx.guild.id})
                self.bot.mongodb["mute_time"].delete_many({"guild_id": ctx.guild.id})
                self.timers.pop(ctx.guild.id)
                self.roles.pop(ctx.guild.id)
                await ctx.send("Something went wrong. Is the mute role deleted?")
            else:
                if len(reason) <= 0:
                    reason = "No specified."
                await remove_mute(self.bot, ctx.guild.id, target.id, reason)
                await ctx.message.add_reaction(emoji='🔇')

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """
        Event listener for Mute class that checks whether or not the mute role have been removed manually and
        performs the appropriate action if so.

        Args:
            before(discord.Member): before member update
            after(discord.Member): after member update

        Returns:
            None
        """
        if before.roles != after.roles:
            try:
                scan = self.roles[after.guild.id]
            except KeyError:
                return

            removed = None
            for i in before.roles:
                if i not in after.roles:
                    removed = i
                    break

            if scan:
                if scan == removed.id:
                    try:
                        self.timers[after.guild.id][after.id].terminate()
                        self.timers[after.guild.id].pop(after.id)
                    except KeyError:
                        return
                    self.bot.mongodb["mute_time"].delete_one({"guild_id": after.guild.id, "user_id": after.id})

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """
        Event listener for Mute class that checks whether or not an assigned mute role were deleted

        Args:
            role(discord.Role): the deleted role

        Returns:
            None
        """
        try:
            result = self.roles[role.guild.id] == role.id
        except KeyError:
            return

        if result:
            self.roles.pop(role.guild.id)
            self.bot.mongodb["mute_role"].delete_many({"guild_id": role.guild.id})
            self.bot.mongodb["mute_time"].delete_manay({"guild_id": role.guild.id})
            try:
                for i in self.timers[role.guild.id]:
                    i.terminate()
                self.timers.pop(role.guild.id)
            except KeyError:
                return

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """
        Listener for Mute class that checks whether not server banned a muted member and update database if so.

        Args:
            guild(discord.Guild): discord server with the ban
            user(discord.User): user being banned from the server

        Returns:
            None
        """
        try:
            result = self.timers[guild.id][user.id]
        except KeyError:
            return

        result.terminate()
        self.timers[guild.id].pop(user.id)
        self.bot.mongodb["mute_time"].delete_one({"guild_id": guild.id, "user_id": user.id})

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Event listener for Mute class that checks whether or not the newly joined member is in mute system, if so
        then re-apply mute role.

        Args:
            member(discord.Member): the newly joined Member

        Returns:
            None
        """
        try:
            result = self.timers[member.guild.id][member.id]
        except KeyError:
            return

        try:
            role = self.roles[member.guild.id]
        except KeyError:
            return

        role = member.guild.get_role(role)
        if not role:
            return

        if result.destination > datetime.datetime.utcnow():
            await member.add_roles(role, reason="Left during a mute, time have not expired yet.")
        else:
            self.timers[member.guild.id].pop(member.id)

    async def tell(self, ctx: commands.Context, target: discord.Member, reason: str, duration: str, inc: bool = False):
        """
        Async method for Mute class that DMs the target regarding their mute.

        Args:
            ctx(commands.Context): pass in context for analysis
            target(discord.Member): pass in member to DM
            reason(str): reasoning
            duration(str): mute duration or increment in string form
            inc(bool): whether or not mute time is increased and not new mute

        Returns:
            None
        """
        if target.bot:
            return
        if len(reason) <= 0:
            return
        if ctx.author.id == target.id:
            return

        data = CustomTools.add_warn(self.bot, ctx.message.created_at, ctx.guild.id, target.id, None, 2, reason,
                                    duration)

        try:
            await target.send("🔇 You have been muted 🔇" if not inc else "➕  Mute Time Increased",
                              embed=discord.Embed(timestamp=ctx.message.created_at,
                                                  description=f"[{duration}] - **{reason}**", colour=0x636e72)
                              .set_footer(icon_url=target.avatar_url_as(size=64), text=f"{data} offenses")
                              .set_author(icon_url=ctx.guild.icon_url_as(size=128), name=f"{ctx.guild.name}"))
        except discord.HTTPException:
            pass
