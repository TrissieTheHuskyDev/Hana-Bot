import discord
import CustomTools
import typing
from discord.ext import commands

import datetime
import asyncio


class Notify:
    """
    Class used to store log channel data.

    Attributes:
        guild(int): guild ID of that channel
        channel(int): the channel ID
        data(dict): contains dictionary with values with booleans
    """
    def __init__(self, package):
        """
        Constructor of Notify class.

        Args:
            package: pass in database package
        """
        self.guild = package['guild_id']
        self.channel = package['channel_id']
        self.data = {}
        temp = ['enter', 'leave', 'kick', 'ban', 'unban', 'trigger', 'raid', 'member_update', 'server_update',
                'vc_update']
        for i in temp:
            self.data.update({i: package[i]})


class Notification(commands.Cog):
    """
    Class of Notification commands for hana bot.

    Attributes:
        bot(commands.Bot): bot reference
        memory(dict): dictionary storing the Notify classes
        reactions(list): list of emote reactions for each different log type
        label(dict): dictionary of translating emotes into string
        second(list): reaction of "yes" and "no"
        db: mongodb reference to "system_message"
    """

    def __init__(self, bot: commands.Bot):
        """
        Constructor for Notification class.

        Args:
            bot(commands.Bot): pass in bot reference
        """
        self.bot = bot
        self.memory = {}
        self.reactions = ["➡", "🚪", "👢", "🔨", "👼", "⚠", "🚶", "🔃", "🏗", "💬", "⏸", "❌"]
        self.label = {"➡": "enter", "🚪": "leave", "👢": "kick", "🔨": "ban", "👼": "unban", "⚠": "trigger",
                      "🚶": "raid", "🔃": "member_update", "🏗": "server_update", "💬": "vc_update"}
        self.second = ['✔', '🇽']
        self.db = bot.mongodb["system_message"]

    def find(self, guild: int, channel: int):
        """
        Method for Notification class that searches the memory dictionary for the appropriate stored Notify class.

        Args:
            guild(int): guild ID of that Notify class
            channel(int): channel ID of that Notify class

        Returns:
            Notify: if found within memory
            None: if nothing was found
        """
        try:
            for i in self.memory[guild]:
                if i.channel == channel:
                    return i
        except KeyError:
            pass
        return None

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Event listener that calls the update method when the bot is ready.

        Returns:
            None
        """
        await self.update()

    async def local_update(self, guild: int):
        """
        Async method for the Notification class that updates the memory of the specified guild from database.

        Args:
            guild(int): guild ID of the guild to update

        Returns:
            None
        """
        try:
            self.memory.pop(guild)
        except KeyError:
            pass
        data = self.db.find({"guild_id": guild})
        if data:
            self.memory.update({guild: []})
            for i in data:
                self.memory[guild].append(Notify(i))

    async def update(self):
        """
        Async method for the Notification class that updates the entire memory from database.

        Returns:
            None
        """
        self.memory = {}
        data = self.db.find({})
        for i in data:
            try:
                fail = False
                server = self.bot.get_guild(i['guild_id'])
                if server:
                    chan = server.get_channel(i['channel_id'])
                    if not chan:
                        fail = True
                else:
                    fail = True

                if not fail:
                    self.memory[i['guild_id']].append(Notify(i))
                else:
                    self.db.delete_one({"guild_id": i['guild_id'], "channel_id": i['channel_id']})
            except KeyError:
                self.memory.update({i['guild_id']: [Notify(i)]})

    @commands.group(aliases=["lc"])
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True, view_audit_log=True)
    async def log_channels(self, ctx: commands.Context):
        """
        Command for Notification class and a command group that will return command group usage if no additional
        sub group were provided.

        Args:
            ctx(commands.Context): pass in context for reply

        Returns:
            None
        """
        if not ctx.invoked_subcommand:
            embed = discord.Embed(
                title="Sub-commands for log channels",
                colour=0xf39c12
            )
            embed.add_field(name="list", value="List channels that is set as a log channel")
            embed.add_field(name="+ [Optional: channel mention]",
                            value="Sets the current channel (if no channel is given) or the mentioned channel as a"
                                  "log channel")
            embed.add_field(name="s [optional: channel mention]",
                            value="Opens up the setting menu for the mentioned or current channel.")
            embed.set_footer(icon_url=self.bot.user.avatar_url_as(size=64),
                             text="Now do the lc command followed by one of the above")

            await ctx.send(embed=embed)

    @log_channels.command(aliases=["l"])
    async def list(self, ctx: commands.Context):
        """
        Sub-command of log_channels that list number of log channels within the server.

        Args:
            ctx(commands.Context): pass in context for analysis and reply

        Returns:
            None
        """
        try:
            data = self.memory[ctx.guild.id]
        except KeyError:
            await ctx.send("This server don't have any log channel.")
            return

        message = "=========================\nList of log channels:\n-------------------------\n"
        for i in data:
            channel = ctx.guild.get_channel(i.channel)
            message += f"> {channel.mention}\n" if channel else f"> {i.channel} 🗑️\n"
        message += "========================="
        new = CustomTools.split_string(message, 2000)
        for i in new:
            await ctx.send(i)

    @log_channels.command(aliases=["+", "a"])
    async def add(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Sub-command of log_channels that sets a channel as a log channel if it's not.

        Args:
            ctx(commands.Context): pass in context for analysis and reply
            channel(discord.TextChannel): the channel to set as a log channel

        Returns:
            None
        """
        channel = ctx.channel if not channel else channel
        data = self.find(ctx.guild.id, channel.id)

        if data:
            await ctx.send(f"**#{channel}** is already a log channel.")
        else:
            f = False
            self.db.insert_one(
                {"guild_id": ctx.guild.id, "channel_id": channel.id, "leave": f, "enter": f, "kick": f, "ban": f,
                 "unban": f, "trigger": f, "raid": f, "member_update": f, "server_update": f, "vc_update": f}
            )
            await self.local_update(ctx.guild.id)
            await ctx.send(f"**#{channel}** has been set as a log channel")

    @log_channels.command(aliases=['s'])
    async def setting(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Sub-command of log_channels that pull up setting menu for existing log channel.

        Args:
            ctx(commands.Context): pass in context for analysis and reply
            channel(discord.TextChannel): channel to try pull up log channel setting

        Returns:
            None
        """
        channel = ctx.channel if not channel else channel

        data = self.find(ctx.guild.id, channel.id)

        if not data:
            await ctx.send(f"**#{channel}** is not a log channel")
        else:
            message = await ctx.send("Processing . . .")
            ret = await self.setting_menu(channel, message, data, False)
            if ret:
                temp = ret.data
                self.db.update_one(
                    {"guild_id": ctx.guild.id, "channel_id": channel.id},
                    {"$set": {"enter": temp['enter'], "leave": temp['leave'], "kick": temp['kick'], "ban": temp['ban'],
                              "unban": temp['unban'], "trigger": temp['trigger'], "raid": temp['raid'],
                              "member_update": temp['member_update'], "server_update": temp['server_update'],
                              "vc_update": temp['vc_update']}}
                )

    async def setting_menu(self, channel: discord.TextChannel, message: discord.Message, data: Notify,
                           emoted: bool = True):
        """
        Async method for Notification class that changes the Notify class according to user input.

        Args:
            channel(discord.TextChannel): the target log channel
            message(discord.Message): the message of the summoned setting menu
            data(Notify): Notify class from before
            emoted(bool): whether or not the message already contain the necessary emotes

        Returns:
            Notify: updated Notify class after user input
        """
        y = "✅"
        n = "🛑"
        temp = f"=============================================\n" \
               f"➡|=> {y if data.data['enter'] else n} |=>User joining the server\n" \
               f"🚪|=> {y if data.data['leave'] else n} |=>User leaving the server\n" \
               f"👢|=> {y if data.data['kick'] else n} |=>User kicked from the server\n" \
               f"🔨|=> {y if data.data['ban'] else n} |=>User banned from the server\n" \
               f"👼|=> {y if data.data['unban'] else n} |=>User un-banned from the server\n" \
               f"⚠|=> {y if data.data['trigger'] else n} |=>Word triggers within the server\n" \
               f"🚶|=> {y if data.data['raid'] else n} |=>Possible raid warning alert\n" \
               f"🔃|=> {y if data.data['member_update'] else n} |=>Display server member updates [name, nickname]\n" \
               f"🏗|=> {y if data.data['server_update'] else n} |=>Display server changes\n" \
               f"💬|=> {y if data.data['vc_update'] else n} |=>Display member joining, moving, leaving voice chat"
        embed = discord.Embed(
            colour=0xfdcb6e,
            title=f"Reaction to change what log will the bot send in this channel",
            description=temp
        )
        embed.set_author(name=f"{channel} log settings")
        embed.add_field(name="Freezing", value="reacting with '⏸' will freeze this menu, "
                                               "command redo will be needed.")
        embed.set_footer(text=f"react with '❌' to no longer make [{channel}] a log channel")

        await message.edit(embed=embed, content="")

        if not emoted:
            for i in self.reactions:
                await message.add_reaction(emoji=i)

        def check(reaction1, user1):
            if (reaction1.message.id == message.id) and (user1.id == message.author.id):
                if str(reaction1.emoji) in self.reactions:
                    return True

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30, check=check)
        except asyncio.TimeoutError:
            await message.edit(embed=None, content=f"**{channel}** setting menu timed out ⏱")
            await message.clear_reactions()
            return data
        else:
            if reaction.emoji == "⏸":
                await message.clear_reactions()
                embed.remove_field(0)
                embed.set_footer(text="Frozen")
                embed.title = None
                embed.timestamp = message.created_at
                await message.edit(embed=embed)
                return data
            elif reaction.emoji == "❌":

                def sure(reaction1, user1):
                    if (reaction1.message.id == message.id) and (user1.id == message.author.id):
                        if str(reaction1.emoji) in self.second:
                            return True

                await message.clear_reactions()
                await message.edit(content=f"You sure you want to turn off log messages for **{channel}**?",
                                   embed=None)
                await message.add_reaction(emoji="✔")
                await message.add_reaction(emoji="🇽")

                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=sure)
                except asyncio.TimeoutError:
                    await message.edit(embed=None, content=f"un-log **{channel}** confirm menu timed out ⏱")
                    await message.clear_reactions()
                else:
                    if reaction.emoji == "🇽":
                        await message.delete()
                    if reaction.emoji == "✔":
                        self.db.delete_one({"guild_id": message.guild.id, "channel_id": channel.id})
                        await message.clear_reactions()
                        await self.local_update(message.guild.id)
                        await message.edit(content=f"**{channel}** will no longer receive any log messages.")
            else:
                await message.remove_reaction(emoji=reaction.emoji, member=user)
                req = self.label[reaction.emoji]
                res = data.data[req]
                data.data[req] = False if res else True
                ret = await self.setting_menu(channel, message, data)
                return ret

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        """
        Event listener for Notification class that detects server update and sends update to the appropriate log
        channel.

        Args:
            before(discord.Guild): the discord guild before
            after(discord.Guild): the discord guild after

        Returns:
            None
        """
        try:
            data = self.memory[after.id]
        except KeyError:
            return

        for i in data:
            if i.data['server_update']:
                passing = False
                channel = self.bot.get_channel(i.channel)
                if not channel:
                    self.db.delete_one({"guild_id": i.guild, "channel_id": i.channel})
                    return

                embed = discord.Embed(
                    colour=0x3498db,
                    timestamp=datetime.datetime.utcnow(),
                    title="🔼 Server Updated 🔼"
                )

                def change(title, be, af):
                    embed.add_field(name=f"{title}",
                                    value=f"**from** {be} **to** {af}", inline=False)

                if before.name != after.name:
                    passing = True
                    change("Server Name Change", f"`{before.name}`", f"`{after.name}`")
                if before.owner != after.owner:
                    passing = True
                    change("Owner Change", before.owner.mention, after.owner.mention)
                if before.region != after.region:
                    passing = True
                    change("Region Change", f"`{before.region}`", f"`{after.region}`")
                if before.premium_tier != after.premium_tier:
                    passing = True
                    change("Server Boost Level Change", f"Level `{before.premium_tier}`",
                           f"`Level {after.premium_tier}`")
                if before.afk_channel != after.afk_channel:
                    passing = True
                    change("AFK Voice Channel Change", f"`{before.afk_channel}`", f"`{after.afk_channel}`")
                if before.afk_timeout != after.afk_timeout:
                    passing = True
                    change("AFK Time Out Change", f"`{before.afk_timeout / 60} minutes`",
                           f"`{after.afk_timeout / 60} minutes`")
                if before.default_notifications != after.default_notifications:
                    passing = True
                    change("Notification Level Change", f"`{before.default_notifications}`",
                           f"`{after.default_notifications}`")
                if before.verification_level != after.verification_level:
                    passing = True
                    change("Verification Level Change", f"`{before.verification_level}`",
                           f"`{after.verification_level}`")
                if before.explicit_content_filter != after.explicit_content_filter:
                    passing = True
                    change("Content Filter Change", f"`{before.explicit_content_filter}`",
                           f"`{after.explicit_content_filter}`")

                if passing:
                    await channel.send(embed=embed)

                async def image(title, b, a):
                    await channel.send(f"{title}\n======================")
                    await channel.send(embed=discord.Embed(
                        colour=0x3498db,
                        title=f"Before {title}"
                    ).set_image(url=b))
                    await channel.send(embed=discord.Embed(
                        colour=0x3498db,
                        title=f"After {title}"
                    ).set_image(url=a))

                if before.icon_url != after.icon_url:
                    await image("Server Icon Update", before.icon_url, after.icon_url)
                if before.banner_url != after.banner_url:
                    await image("Server Banner Update", before.banner_url, after.banner_url)
                if before.splash_url != after.splash_url:
                    await image("Server Splash Screen Update", before.splash_url, after.splash_url)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        """
        Event listener for Notification class that detects voice state update and sends it for the appropriate
        log channel.

        Args:
            member(discord.Member): member of the voice state change
            before(discord.VoiceState): voice state before
            after(discord.VoiceState): voice state after

        Returns:
            None
        """
        try:
            data = self.memory[member.guild.id]
        except KeyError:
            return

        for i in data:
            if i.data['vc_update']:
                channel = self.bot.get_channel(i.channel)
                if not channel:
                    self.db.delete_one({"guild_id": i.guild, "channel_id": i.channel})
                    return
                now = datetime.datetime.utcnow()

                embed = None
                label = ""

                if before.channel is None:
                    embed = discord.Embed(
                        colour=0x7bed9f,
                        description=f"{member.mention} **joined** `{after.channel}`"
                    )
                    label = "🎤"
                elif after.channel is None:
                    embed = discord.Embed(
                        colour=0xff6b81,
                        description=f"{member.mention} **left** `{before.channel}`"
                    )
                    label = "🚪"
                elif before.channel != after.channel:
                    embed = discord.Embed(
                        colour=0xeccc68,
                        description=f"{member.mention} **switched** from `{before.channel}` to `{after.channel}`",
                    )
                    label = "🔄"
                elif after.self_stream and not before.self_stream:
                    embed = discord.Embed(
                        colour=0x6c5ce7,
                        description=f"{member.mention} is **Live** in `{after.channel}`!"
                    )
                    label = "📺"
                if embed:
                    embed.set_author(name="Voice Channel Update")
                    embed.set_footer(icon_url=member.avatar_url_as(size=64), text=label)
                    embed.timestamp = now
                    await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Event listener for Notification class for when a new member joins.

        Args:
            member(discord.Member): the new member that joined the server

        Returns:
            None
        """
        try:
            data = self.memory[member.guild.id]
        except KeyError:
            return

        for i in data:
            if i.data['enter']:
                channel = self.bot.get_channel(i.channel)
                if not channel:
                    self.db.delete_one({"guild_id": i.guild, "channel_id": i.channel})
                    return
                embed = discord.Embed(
                    colour=0x55efc4,
                    timestamp=member.joined_at,
                    description=f"{member.mention} ➡ **{member.guild}**"
                )
                embed.set_thumbnail(url=member.avatar_url)
                embed.set_author(name="New member!", icon_url=member.guild.icon_url)
                embed.add_field(name="User ID", value=member.id)
                embed.add_field(name="Account Birthday", value=member.created_at.strftime("%#d %B %Y, %I:%M %p UTC"))
                temp = member.joined_at - member.created_at
                # code reference: https://stackoverflow.com/questions/28775345/python-strftime-clock
                seconds = temp.days*86400 + temp.seconds
                minutes, seconds = divmod(seconds, 60)
                hours, minutes = divmod(minutes, 60)
                days, hours = divmod(hours, 24)
                years, days = divmod(days, 365)
                temp = "{years:02d} years {days:02d} days {hours:02d} hours {minutes:02d} " \
                       "minutes {seconds:02d} seconds".format(**vars())
                embed.add_field(name="Account Age", value=temp, inline=False)
                url = self.bot.user.avatar_url_as(size=64)
                if seconds <= 1:
                    embed.set_footer(icon_url=url, text="This user is 99.99% a bot account!!")
                elif hours <= 1:
                    embed.set_footer(icon_url=url, text="This account is rather new...")
                elif days <= 7:
                    embed.set_footer(icon_url=url, text="New to discord yo!")

                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """
        Event listener for Notification class when a member "leaves" the server.

        Args:
            member(discord.Member): member who left the server

        Returns:
            None
        """
        # reference: https://youtu.be/eirjjyP2qcQ
        # https://discordpy.readthedocs.io/en/latest/api.html#discord.Guild.audit_logs
        try:
            data = self.memory[member.guild.id]
        except KeyError:
            return
        time = datetime.datetime.utcnow()

        for i in data:
            target = self.bot.get_channel(i.channel)
            if not target:
                self.db.delete_one({"guild_id": i.guild, "channel_id": i.channel})
                return

            if i.data['leave']:
                embed = discord.Embed(
                    colour=0xe74c3c,
                    timestamp=time,
                    description=f"{member.mention} ⬅ **{member.guild}**"
                )
                embed.set_thumbnail(url=member.avatar_url)
                embed.set_author(name="Someone left...", icon_url=member.guild.icon_url)
                embed.add_field(name="User ID", value=member.id)
                embed.add_field(name="Leave Time",
                                value=time.strftime("%#d %B %Y, %I:%M %p UTC"))

                await target.send(embed=embed)

            if i.data['kick']:
                async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
                    temp = (time - entry.created_at).seconds
                    if entry.target.id == member.id and temp < 300:
                        embed = discord.Embed(
                            colour=0xe74c3c,
                            timestamp=entry.created_at,
                            description=f"**{entry.target.name}** got drop kicked out of **{member.guild}**!"
                        )
                        embed.set_thumbnail(url=member.avatar_url)
                        embed.set_author(name="👢 Booted!", icon_url=member.guild.icon_url)
                        embed.set_footer(text="Kicked")
                        embed.add_field(inline=False, name="Kicked by:", value=entry.user.mention)
                        embed.add_field(inline=False, name="Reason:", value=entry.reason)
                        embed.add_field(name="User ID", value=member.id)
                        embed.add_field(name="Kick Time",
                                        value=entry.created_at.strftime(
                                            "%#d %B %Y, %I:%M %p UTC"))

                        await target.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: typing.Union[discord.Member, discord.User]):
        """
        Event listener for Notification class when a ban has occurred and sends update to the appropriate log channel.

        Args:
            guild(discord.Guild): the guild where the ban event has occurred
            user(typing.Union[discord.Member, discord.User]): user being banned from server

        Returns:
            None
        """
        try:
            data = self.memory[guild.id]
        except KeyError:
            return

        for i in data:
            if i.data['ban']:
                async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=2):
                    if entry.target.id == user.id:
                        channel = self.bot.get_channel(i.channel)
                        if not channel:
                            self.db.delete_one({"guild_id": i.guild, "channel_id": i.channel})
                            return

                        embed = discord.Embed(
                            timestamp=entry.created_at,
                            colour=0xED4C67,
                            description=f"**{user.name}** got hit by a massive hammer and vanished into the "
                                        f"shadow realm!"
                        )
                        embed.set_footer(text="Banned")
                        embed.set_thumbnail(url=user.avatar_url)
                        embed.set_author(name="🔨 Banned!", icon_url=guild.icon_url)
                        embed.add_field(inline=False, name="Banned by:", value=entry.user.mention)
                        embed.add_field(inline=False, name="Reason:", value=entry.reason)
                        embed.add_field(name="User ID", value=user.id)
                        embed.add_field(name="Ban Time", value=entry.created_at.strftime("%#d %B %Y, %I:%M %p UTC"))
                        channel = self.bot.get_channel(i.channel)

                        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        """
        Event listener for Notification class that detects when a user have been unbanned and sends update to the
        appropriate log channel.

        Args:
            guild(discord.Guild): guild of the unban event
            user(discord.User): user being unbanned

        Returns:
            None
        """
        try:
            data = self.memory[guild.id]
        except KeyError:
            return

        for i in data:
            if i.data['unban']:
                async for entry in guild.audit_logs(action=discord.AuditLogAction.unban, limit=2):
                    channel = self.bot.get_channel(i.channel)
                    if not channel:
                        self.db.delete_one({"guild_id": i.guild, "channel_id": i.channel})
                        return
                    if entry.target.id == user.id:
                        embed = discord.Embed(
                            colour=0x1abc9c,
                            timestamp=entry.created_at,
                            description=f"Don't lose hope just yet **{user.name}**! Stay determined!"
                        )
                        embed.set_footer(text="Unbanned")
                        embed.set_thumbnail(url=user.avatar_url)
                        embed.set_author(name="✝ Unbanned!", icon_url=guild.icon_url)
                        embed.add_field(inline=False, name="Unbanned by:", value=entry.user.mention)
                        embed.add_field(inline=False, name="Reason:", value=entry.reason)
                        embed.add_field(name="User ID", value=user.id)
                        embed.add_field(name="Unban Time", value=entry.created_at.strftime("%#d %B %Y, %I:%M %p UTC"))

                        await channel.send(embed=embed)


def setup(bot: commands.Bot):
    """
    Necessary function for a cog that initialize the Notification class.

    Args:
        bot (commands.Bot): passing in bot for class initialization

    Returns:
        None
    """
    bot.add_cog(Notification(bot))
    print("Loaded Cog: Notification")


def teardown(bot: commands.Bot):
    """
    Function to be called upon Cog unload, in this case, it will print message in CMD.

    Args:
        bot (commands.Bot): passing in bot reference for unload.

    Returns:
        None
    """
    bot.remove_cog("Notification")
    print("Unloaded Cog: Notification")
