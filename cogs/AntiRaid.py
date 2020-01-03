import discord
from discord.ext import commands
import asyncio
import typing
from CustomTools import prefix


class Jail:
    """
    A class of jail cells for potential raiders.

    Attributes:
        data (list): list of jail cells for holding member data of potential raiders
        IDs (list): list of the ID of people in the jail cell
        guild (int): the guild ID the jail cells represents
        role (int): the role to give to people in the jail cells and future members when anti-raid mode is on
        timer (int): the timer that automatically removes the new member from cell if anti-raid mode is off
        count (int): the max amount of people in the holding cell
        switch (bool): whether or not the anti-raid system is on
        trigger (bool): whether or not anti-raid mode is on
    """
    def __init__(self, package):
        """
        Constructor for Jail class.

        Args:
            package: passing in the data from SQL data base to initialize the class.
        """
        self.data = []
        self.IDs = []
        self.guild = package['guild_id']
        self.role = package['role_id']
        self.timer = package['interval']
        self.count = package['amount']
        self.switch = package['power']
        self.trigger = False

    async def triggered(self, guild: discord.Guild):
        """
        Async function that turns the anti-raid on and puts everyone in holding cell into jail cell along with giving
        them the assigned raider role.

        Args:
            guild (discord.Guild): passing in the discord server

        Returns:
            None

        Raises:
            ValueError: if the passed in guild don't matches the class' assigned guild id
        """
        if self.guild != guild.id:
            raise ValueError("guild ID don't match")
        role = guild.get_role(self.role)
        self.trigger = True
        for i in self.data:
            if role not in i.roles:
                try:
                    await i.add_roles(role, reason="Potential Raider")
                except discord.NotFound:
                    pass

    async def add(self, member: discord.Member):
        """
        Async function that adds a new member to the holding cell.

        Args:
            member (discord.Member): the new member to add into the holding

        Returns:
            None

        Raises:
            ValueError: if the input member's guild id don't match the one stored
        """
        if self.guild != member.guild.id:
            raise ValueError("guild ID don't match")
        if self.switch:
            if member.id not in self.IDs:
                self.data.append(member)
                self.IDs.append(member.id)
            if not self.trigger:
                if len(self.data) >= self.count:
                    self.trigger = True
                    await self.triggered(member.guild)
                else:
                    await asyncio.sleep(self.timer)
                    if not self.trigger:
                        try:
                            self.data.remove(member)
                            self.IDs.remove(member.id)
                        except ValueError:
                            pass
                        return
            else:
                await member.add_roles(member.guild.get_role(self.role), reason="Potential Raider")

    async def kill_all(self, ctx: commands.Context, conti: bool = False):
        """
        Async function that bans all users in the jail cell from the server and wipe their message.

        Args:
            ctx (commands.Context): passing in the context of the command call
            conti (bool): Whether or not to keep the anti-raid mode on, defaults to no

        Returns:
            None

        Raises:
            ValueError: if the context guild ID don't match the stored one
        """
        if self.guild != ctx.guild.id:
            raise ValueError("guild ID don't match")
        role = ctx.guild.get_role(self.role)
        for i in role.members:
            try:
                await i.ban(reason="Raider Ban", delete_message_days=1)
            except discord.HTTPException:
                pass
        self.data = []
        self.IDs = []
        self.trigger = conti

    async def kick_all(self, ctx: commands.Context, conti: bool = True):
        """
        Async function that kicks all users in the jail cell from the server.

        Args:
            ctx (commands.Context): passes in command call context
            conti (bool): whether or not to let anti-raid mode continue, default true

        Returns:
            None

        Raises:
            ValueError: if the passed in guild ID don't match the one stored
        """
        if self.guild != ctx.guild.id:
            raise ValueError("guild ID don't match")
        role = ctx.guild.get_role(self.role)
        for i in self.data:
            if role in i.roles:
                try:
                    await i.kick(reason="Raider Kick")
                except discord.HTTPException:
                    pass
        self.data = []
        self.IDs = []
        self.trigger = conti

    async def false_alarm(self, ctx: commands.Context):
        """
        Async function that turns off the anti-raid mode and release all users in the jail cell.

        Args:
            ctx(commands.Context): pass in command call context

        Returns:
            None
        """
        self.trigger = False
        role = ctx.guild.get_role(self.role)
        for i in self.data:
            if role in i.roles:
                try:
                    await i.remove_roles(role, reason="All clear, not a raid.")
                except discord.NotFound:
                    pass
        self.data = []
        self.IDs = []

    def toggle(self, ctx: commands.Context):
        """
        A function that toggles the anti-raid.

        Args:
            ctx (commands.Context): passing in context

        Returns:
            none

        Raises:
            ValueError: the passed in guild ID don't match one stored
        """
        if self.guild != ctx.guild.id:
            raise ValueError("guild ID don't match")
        self.switch = not self.switch
        return self.switch

    def is_in(self, target: typing.Union[discord.Member, discord.User, int]):
        """
        A function that checks whether or not the passed in target is in any cells.

        Args:
            target (typing.Union[discord.Member, discord.User, int]):
                The target to check for

        Returns:
            none
        """
        if isinstance(target, int):
            sight = target
        else:
            sight = target.id
        return sight in self.IDs

    def to_string(self, ctx: commands.Context):
        """
        A function that returns people in the cells as string.

        Args:
            ctx (commands.Context): passing in context to check

        Returns:
            str: people in the cell of this Jail class

        Raises:
            ValueError: if the passed in guild ID don't match the one stored
        """
        if ctx.guild.id != self.guild:
            raise ValueError("guild ID don't match")
        ret = ""
        role = ctx.guild.get_role(self.role)
        for i in range(len(self.data)):
            if role in self.data[i].roles:
                ret += f"{i + 1}.\t{self.data[i].mention}\n"
        return ret


class AntiRaid(commands.Cog):
    """
    A class of anti-raid commands for server members with mod privilege.

    Attributes:
        bot(commands.Bot): bot reference
        logging(dict): dictionary with key of guild ID and Jail class reference as object
    """
    def __init__(self, bot: commands.Bot):
        """
        Constructor for Anti-Raid class.

        Args:
            bot(commands.Bot): passing in bot reference
        """
        self.bot = bot
        self.db = bot.mongodb["anti_raid"]
        self.logging = {}

    async def update(self):
        """
        Async method that updates the logging dictionary base on SQL data. This will lose jail cell data.

        Returns:
            None
        """
        self.logging = {}
        data = self.db.find({})
        for i in data:
            fail = False
            guild = self.bot.get_guild(i['guild_id'])
            if guild:
                role = guild.get_role(i['role_id'])
                if guild and role:
                    self.logging.update({i['guild_id']: Jail(i)})
                    for m in role.members:
                        self.logging[i['guild_id']].data.append(m)
                        self.logging[i['guild_id']].IDs.append(m.id)
                else:
                    fail = True
            else:
                fail = True
            if fail:
                self.db.delete_one({"guild_id": i["guild_id"]})

    async def local_update(self, guild: int):
        """
        Async function that updates the setting of a specific server's an anti-raid system.

        Args:
            guild(int): pass in guild ID to update their anti-raid

        Returns:
            None
        """
        try:
            self.logging.pop(guild)
        except KeyError:
            pass
        data = self.db.find_one({"guild_id": guild})
        if data:
            self.logging.update({guild: Jail(package=data)})

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Calls the update function when the Cog's ready.

        Returns:
            None
        """
        await self.update()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Function to be called when a new user joins the server and puts them into anti-raid system if any, if
        anti-raid mode is on, bot will send message to channels in the server that has notified setting set to
        anti-raid.

        Args:
            member(discord.Member): the newly joined member

        Returns:
            None
        """
        try:
            check = self.logging[member.guild.id].switch
        except KeyError:
            return
        if check:
            await self.logging[member.guild.id].add(member)
            if self.logging[member.guild.id].trigger:
                try:
                    data = self.bot.get_cog("Notification").memory[member.guild.id]
                except KeyError:
                    return
                except ValueError:
                    return
                embed = discord.Embed(
                    colour=0xe056fd,
                    title="Potential Raider",
                    timestamp=member.joined_at
                ).set_footer(text="Joined", icon_url=member.guild.icon_url_as(size=64))
                embed.set_thumbnail(url=member.avatar_url)
                embed.add_field(name="Mention", value=member.mention)
                embed.add_field(name="ID", value=member.id)
                for i in data:
                    if i.data['raid']:
                        await self.bot.get_channel(i.channel).send(embed=embed)

    @commands.group(aliases=['ar'])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True, kick_members=True)
    async def antiraid(self, ctx: commands.Context):
        """
        Main command of the anti-raid, will be used to call other sub commands.

        Args:
            ctx (commands.Context): passing in context for reply

        Returns:
            None
        """
        if ctx.invoked_subcommand is None:
            pass
            # TODO additional

    async def verify(self, ctx: commands.Context):
        """
        Async function that checks whether or not a server have anti-raid system.

        Args:
            ctx(commands.Context): passing in context for reply

        Returns:
            None
        """
        try:
            data = self.logging[ctx.guild.id]
        except KeyError:
            pre = prefix(self, ctx)
            await ctx.send(f"This server have not setup an anti-raid yet. Do `{pre}antiraid create <raider role>`"
                           f"to set it up.")
            return
        return data

    @antiraid.command()
    async def no(self, ctx: commands.Context):
        """
        Sub command of antiraid, this will disable the anti-raid mode if it's on.

        Args:
            ctx (commands.Context): passing in context for analyze and reply

        Returns:
            None
        """
        data = await self.verify(ctx)
        if not data:
            return
        await data.false_alarm(ctx)
        await ctx.send("False alarm, all prisoner released.")

    @antiraid.command()
    async def raid(self, ctx: commands.Context):
        """
        Sub command of antiraid, this will turn the raid alarm on.

        Args:
            ctx(commands.Context): passing in Context for reply

        Returns:
            None
        """
        data = await self.verify(ctx)
        if not data:
            return
        await data.triggered(ctx.guild)
        await ctx.message.add_reaction(emoji="🏃")

    @antiraid.command()
    async def kick(self, ctx: commands.Context, alarm: bool = False):
        """
        Sub command of antiraid, this will kick all members inside the jail cell from the server.

        Args:
            ctx (commands.Context): passing in context for verification and reply
            alarm (bool): whether or not to disable the anti-raid mode, default is no

        Returns:
            None
        """
        data = await self.verify(ctx)
        if not data:
            return
        await self.logging[ctx.guild.id].kick_all(ctx, not alarm)
        await ctx.message.add_reaction(emoji='✅')

    @antiraid.command()
    async def ban(self, ctx: commands.Context, alarm: bool = True):
        """
        Sub command of antiraid, this will ban all members inside the jail cell from the server.

        Args:
            ctx(commands.Context): passing in context for verification and reply
            alarm(bool): whether or not to turn off anti-raid mode, default yes

        Returns:
            None
        """
        data = await self.verify(ctx)
        if not data:
            return
        await self.logging[ctx.guild.id].kill_all(ctx, not alarm)
        await ctx.message.add_reaction(emoji='✅')

    @antiraid.command()
    async def create(self, ctx: commands.Context, role: discord.Role):
        """
        Sub command of antiraid, this will create initialize the anti-raid system for that server unless it is already
        initialized.

        Args:
            ctx(commands.Context): pass in context for analyze and reply
            role(discord.Role): the anti-raid mode

        Returns:
            None.
        """
        data = self.db.find_one({"guild_id": ctx.guild.id})
        if data:
            await ctx.send("This server already have an anti-raid system, no need to create another.")
            return
        self.db.insert_one({"guild_id": ctx.guild.id, "interval": 5, "amount": 3, "power": True, "role_id": role.id})
        data = self.db.find_one({"guild_id": ctx.guild.id})
        self.logging.update({ctx.guild.id: Jail(data)})
        await ctx.message.add_reaction(emoji='👍')

    @antiraid.command()
    async def cell(self, ctx: commands.Context):
        """
        Sub command of antiraid that shows the cell of anti-raid.

        Args:
            ctx(commands.Context): pass in context for analyze and reply

        Returns:
            None
        """
        data = await self.verify(ctx)
        if not data:
            return
        await ctx.send(embed=discord.Embed(
            colour=0xe056fd,
            title="Raid Cell " + ("[RAID ALERT!]" if data.trigger else "[All Clear]"),
            description=data.to_string(ctx),
            timestamp=ctx.message.created_at
        ))

    @antiraid.command(aliases=['+'])
    async def mark(self, ctx: commands.Context, *target: discord.Member):
        """
        Sub command of antiraid that puts a selected member into the jail cell.

        Args:
            ctx(commands.Context): pass in context for analyze and reply
            target(*discord.Member): the members to put into cell

        Returns:
            None
        """
        data = await self.verify(ctx)
        if not data:
            return
        guild = ctx.guild.id
        for i in target:
            if not data.is_in(i):
                self.logging[guild].data.append(i)
                self.logging[guild].IDs.append(i.id)
            role = ctx.guild.get_role(data.role)
            if role not in i.roles:
                await i.add_roles(role, reason="Marked as a raider.")
        await ctx.message.add_reaction(emoji='👍')

    @antiraid.command(aliases=['-'])
    async def unmark(self, ctx: commands.Context, *target: discord.Member):
        """
        Sub command of antiraid that puts a selected member out of the jail cell if they are in it.

        Args:
            ctx(commands.Context): passing in context to check and reply
            target(*discord.Member): the members to remove from jail cell

        Returns:
            None
        """
        data = await self.verify(ctx)
        if not data:
            return
        guild = ctx.guild.id
        for i in target:
            if data.is_in(i):
                self.logging[guild].data.remove(i)
                self.logging[guild].IDs.remove(i.id)
                role = ctx.guild.get_role(data.role)
                if role in i.roles:
                    try:
                        await i.remove_roles(role, reason="Unmarked, not a raider.")
                    except discord.NotFound:
                        pass
        await ctx.message.add_reaction(emoji='👍')

    @antiraid.command(aliases=['s'])
    async def setting(self, ctx: commands.Context):
        """
        Sub command of antiraid that pulls up the anti-raid setting menu for user to modify.

        Args:
            ctx(commands.Context): pass in context to check and fetch anti-raid info

        Returns:
            None
        """
        emotes = []

        def check(reaction1, user1):
            return reaction1.emoji in emotes and user1.id == ctx.author.id

        data = await self.verify(ctx)
        if not data:
            return
        emotes = ['💡', '👪', '⏱', '📛', '🔁', '⏸']
        de_role = ctx.guild.get_role(data.role)
        embed = discord.Embed(
            title="Anti-Raid Setting Menu " + ("[Active]" if data.switch else "[Inactive]"),
            colour=0x2ecc71 if data.switch else 0xc0392b,
            timestamp=ctx.message.created_at,
            description=f"💡 - Toggle Anti-Raid \n👪 - Amount of People Required to Trigger [{data.count}]\n"
                        f"⏱ - Timer [{data.timer} seconds]\n"
                        f"📛 - Raider Role: " + (f"{de_role.mention}" if de_role else "**Error!!**") + "\n"
                        f"🔁 - Reload Anti-Raid Module\n⏸ - Setting Menu Pause"
        ).set_footer(text="React to Modify", icon_url=self.bot.user.avatar_url_as(size=128))
        msg = await ctx.send(embed=embed)
        for i in emotes:
            await msg.add_reaction(emoji=i)
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=check)
        except asyncio.TimeoutError:
            await msg.edit(embed=embed.set_footer(text="Menu Timed Out",
                                                  icon_url=self.bot.user.avatar_url_as(size=64)))
            await msg.clear_reactions()
            return
        await msg.clear_reactions()

        def check_m(m):
            return m.author.id == ctx.author.id

        if reaction.emoji == '⏸':
            await msg.edit(embed=embed.set_footer(text="Menu Paused", icon_url=self.bot.user.avatar_url_as(size=64)))
        elif reaction.emoji == "💡":
            result = self.logging[ctx.guild.id].toggle(ctx)
            await msg.edit(embed=None, content="Anti-Raid now enabled" if result else "Anti-Raid now disabled")
        elif reaction.emoji == '🔁':
            self.logging[ctx.guild.id] = Jail(self.db.find_one({"guild_id": ctx.guild.id})["guild_id"])
            await msg.edit(embed=None, content="Anti-Raid reloaded 🔁")
            return
        elif reaction.emoji == '📛':
            await msg.edit(embed=None, content="Enter the role ID of the new raider role.")
            try:
                m = await self.bot.wait_for('message', timeout=20, check=check_m)
            except asyncio.TimeoutError:
                await msg.edit(content="Anti-Raid Menu Timed Out.")
                return
            try:
                rol = ctx.guild.get_role(int(m.content))
            except ValueError:
                await msg.edit(content="Input not a number, action cancelled.")
                return
            if not rol:
                await msg.edit(content="Role not found, action cancelled")
                return
            await msg.edit(content=f"Changed raid role to {rol.mention}")
            self.logging[ctx.guild.id].role = rol.id
        else:
            try:
                if reaction.emoji == '👪':
                    await msg.edit(embed=None, content="Enter the amount(integer) of user join needed to trigger")
                else:
                    await msg.edit(embed=None, content="Enter the amount(integer) in seconds of the interval")
                m = await self.bot.wait_for('message', timeout=10, check=check_m)
                try:
                    m = int(m.content)
                except ValueError:
                    await msg.edit(content="Value entered is not an integer. Action cancelled")
                    return
                if m < 1:
                    await msg.edit(content="Value must be 1 or bigger")
                    return
                if reaction.emoji == '👪':
                    self.logging[ctx.guild.id].count = m
                    await msg.edit(content=f"member join flow holder is now set to `{m}` people")
                else:
                    self.logging[ctx.guild.id].timer = m
                    await msg.edit(content=f"member join timer is now set `{m}` seconds")
            except asyncio.TimeoutError:
                await msg.edit(content="Anti-Raid Menu Timed Out.")
                return
        await self.database_update(self.logging[ctx.guild.id])

    async def database_update(self, data: Jail):
        """
        Async function that updates the data inside the SQL database base on given Jail class.

        Args:
            data(Jail): passing in the jail pass for updating SQL

        Returns:
            None
        """
        self.db.update_one({"guild_id": data.guild}, {"$set": {"power": data.switch, "interval": data.timer,
                                                               "amount": data.count, "role_id": data.role}})


def setup(bot: commands.Bot):
    """
    Necessary function for a cog that initialize the AntiRaid class.

    Args:
        bot (commands.Bot): passing in bot for class initialization

    Returns:
        None
    """
    bot.add_cog(AntiRaid(bot))
    print("Loaded Cog: AntiRaid")


def teardown(bot: commands.Bot):
    """
    Function to be called upon Cog unload, in this case, it will print message in CMD.

    Args:
        bot (commands.Bot): passing in bot reference for unload.

    Returns:
        None
    """
    bot.remove_cog("AntiRaid")
    print("Unloaded Cog: AntiRaid")
