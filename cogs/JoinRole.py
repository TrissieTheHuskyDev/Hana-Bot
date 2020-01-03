import discord
import typing
from discord.ext import commands


class AutoRole:
    """
    A class for roles to add to new members.

    Attributes:
        data(list): list with the ID of roles to add on new members
        power(bool): whether the join role system is active
        guild(int): the guild ID
    """
    def __init__(self, pack):
        """
        Constructor for the class JoinRole.

        Args:
            pack: passes in PostgreSQL data for initialization
        """
        self.guild = pack['guild_id']
        self.data = pack['role_array']
        self.power = pack['switch']

    def to_string(self):
        """
        Function that returns string with the stored role in the class.

        Returns:
            str: String of roles inside the system
        """
        ret = ""
        for i in self.data:
            ret += f"<@&{i}>\n"
        return ret

    async def join(self, member: discord.Member):
        """
        Async function that adds the roles stored inside the class onto the passed in member.

        Args:
            member(discord.Member): member to add stored roles to

        Returns:
            None
        """
        if not self.data:
            return
        elif not self.power:
            return
        elif len(self.data) < 1:
            return
        else:
            temp = []
            for i in self.data:
                add = member.guild.get_role(i)
                if add:
                    temp.append(add)
            await member.add_roles(*temp, reason="Auto-Join role")


class JoinRole(commands.Cog):
    """
    A class of JoinRole commands.

    Attributes:
        bot(commands.Bot): bot reference for the class
        data(dict): dictionary for storing JoinRole classes for server
    """
    def __init__(self, bot: commands.Bot):
        """
        Constructor for the JoinRole class.

        Args:
            bot(commands.Bot): bot reference for the class
        """
        self.bot = bot
        self.data = {}
        self.db = bot.mongodb["join_auto"]

    def search(self, guild: int):
        """
        A function that scans the data given the guild ID and returns the AutoRole.

        Args:
            guild(int): the guild ID to scan the data

        Returns:
            AutoRole: the AutoRole class associated with that guild
            None: if the guild don't have JoinRole system
        """
        try:
            return self.data[guild]
        except KeyError:
            return

    async def update(self, guild: int = None):
        """
        Async function that grabs information from the SQL data and paste adds the information into data.

        Args:
            guild(int): the guild ID to update. If none, then update the entire data

        Returns:
            None
        """
        if guild:
            try:
                self.data.pop(guild)
            except KeyError:
                pass
            data = self.db.find_one({"guild_id": guild})
        else:
            self.data = {}
            data = self.db.find({})
        if not data:
            return
        for i in data:
            self.data.update({i['guild_id']: AutoRole(i)})

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Event function to be called when the bot is ready, update data.

        Returns:
            None
        """
        await self.update()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Async function called when someone joins the server and determine whether or not to auto role.

        Args:
            member(discord.Member): the newly joined member

        Returns:
            None
        """
        if member.bot:
            return

        data = self.search(member.guild.id)

        if data:
            await data.join(member)

    @commands.group(aliases=['jr'])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def join_role(self, ctx: commands.Context):
        """
        Command group of join_role, if no sub-command or wrong sub command, the correct usage will be displayed.

        Args:
            ctx(commands.Context): pass in context for reply

        Returns:
            None
        """
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="Please specify the operation",
                colour=0x12CBC4
            )
            embed.add_field(name="+ <Role mention or ID>...", value="Adds in one or multiple roles into the system.")
            embed.add_field(name="- <Role mention or ID>...",
                            value="Remove one or multiple roles from the system.")
            embed.add_field(name="t", value="toggle auto role menu on or off")
            embed.add_field(name="list", value="Shows the number of roles in the join role system.")
            embed.add_field(name="reset", value="Turns join role system off and wipes the existing setting.")
            embed.set_footer(text="Now do the command again but with one of the above after the command",
                             icon_url=self.bot.user.avatar_url_as(size=64))
            await ctx.send(embed=embed)

    @join_role.command(aliases=['l'])
    async def list(self, ctx: commands.Context):
        """
        Sub-command of join_role that lists the number of roles inside the join role system for that server.

        Args:
            ctx(commands.Context): pass in context for reply and search

        Returns:
            None
        """
        data = self.search(ctx.guild.id)

        if not data:
            await ctx.send("Join role system no set.")
        else:
            temp = data.to_string()
            status = "Join role list " + ("[On]" if data.switch else "[Off]")
            await ctx.send(embed=discord.Embed(
                title=status,
                colour=0x2ecc71 if data.switch else 0xe74c3c,
                description=temp
            ))

    @join_role.command()
    async def reset(self, ctx: commands.Context):
        """
        Sub-command of join_role that deletes the join role system from that server.

        Args:
            ctx(commands.Context): pass in context for reply and analysis

        Returns:
            None
        """
        data = self.search(ctx.guild.id)

        if not data:
            await ctx.send("Nothing to purge")
        else:
            self.db.delete_one({"guild_id": ctx.guild.id})
            await self.update(ctx.guild.id)
            await ctx.send("Join role system purged.")

    @join_role.command(aliases=['t'])
    async def toggle(self, ctx: commands.Context):
        """
        Sub-command of join_role that toggles on and off switch of the join role system for that server.

        Args:
            ctx(commands.Context): pass in context for reply and analysis

        Returns:
            None
        """
        data = self.search(ctx.guild.id)

        if not data:
            await ctx.send("No join role system for this server")
        else:
            data.switch = not data.switch
            status = "On" if data.switch else "Off"
            self.db.update_one({"guild_id": ctx.guild.id}, {"$set": {"switch": data.switch}})
            await ctx.send(f"Join role system is now {status}")

    @join_role.command(aliases=['-'])
    async def remove(self, ctx: commands.Context, *roles: typing.Union[discord.Role, int]):
        """
        Sub-command of join_role that removes the specified roles from the join role system.

        Args:
            ctx(commands.Context): pass in context for reply and analysis
            *roles(typing.Union[discord.Role, int]): list of either discord role or integer for removal from join role.

        Returns:
            None
        """
        data = self.search(ctx.guild.id)

        if not data:
            await ctx.send("Join role system is not setup")
            return

        removes = ""
        fails = ""
        for i in roles:
            num = i.id if isinstance(i, discord.Role) else i
            try:
                data.data.remove(num)
            except ValueError:
                fails += f"<@&{num}>\n"
            else:
                removes += f"<@&{num}>\n"

        self.db.update_one({"guild_id": ctx.guild.id}, {"$set": {"role_array", data.data}})

        embed = discord.Embed(
            title="Updated roles in the join role system",
            colour=0xe74c3c
        )
        embed.add_field(name="Removed roles", value="None" if removes == "" else removes, inline=False)
        embed.add_field(name="Failed to remove", value="None" if fails == "" else fails, inline=False)
        await ctx.send(embed=embed)

    @join_role.command(aliases=['+'])
    async def add(self, ctx: commands.Context, *roles: discord.Role):
        """
        Sub-command of join_role that adds specified role into the join role system.

        Args:
            ctx(commands.Context): pass in context for reply and analysis
            *roles([discord.Role]): list of discord roles to add into the join role system

        Returns:
            None
        """
        data = self.search(ctx.guild.id)
        if not data:
            ids = []
            for i in roles:
                ids.append(i.id)
            self.db.insert_one({"guild_id": ctx.guild.id, "role_array": ids, "switch": True})
            temp = ""
            for i in roles:
                temp += f"<@&{i.id}>\n"
            await ctx.send(embed=discord.Embed(
                title="Added these role(s) into the join role system",
                colour=0x74b9ff,
                description=temp
            ))
        else:
            adds = ""
            fails = ""
            for i in roles:
                if i not in data.data:
                    adds += f"<@&{i.id}>\n"
                    data.data.append(i.id)
                else:
                    fails += f"<@&{i.id}>\n"
            self.db.update_one({"guild_id": ctx.guild.id}, {"$set": {"role_array": data.data}})
            embed = discord.Embed(title="Updated role(s) in the join role system", colour=0x55efc4)
            embed.add_field(name="Added Role(s)", value="None" if adds == "" else adds, inline=False)
            embed.add_field(name="Failed to add", value="None" if fails == "" else fails, inline=False)
            await ctx.send(embed=embed)

        await self.update(ctx.guild.id)


def setup(bot: commands.Bot):
    """
    Necessary function for a cog that initialize the JoinRole class.

    Args:
        bot (commands.Bot): passing in bot for class initialization

    Returns:
        None
    """
    bot.add_cog(JoinRole(bot))
    print("Loaded Cog: JoinRole")


def teardown(bot: commands.Bot):
    """
    Function to be called upon Cog unload, in this case, it will print message in CMD.

    Args:
        bot (commands.Bot): passing in bot reference for unload.

    Returns:
        None
    """
    bot.remove_cog("JoinRole")
    print("Unloaded Cog: JoinRole")
