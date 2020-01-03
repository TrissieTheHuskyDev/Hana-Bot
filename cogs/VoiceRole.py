import discord
from discord.ext import commands


class VoiceRole(commands.Cog):
    """
    Class of VoiceRole commands.

    Attributes:
        bot(commands.Bot): bot reference
        data(dict): dictionary containing voice chat role data
        db: "vc_text" mongoDB reference
    """
    def __init__(self, bot: commands.Bot):
        """
        Constructor for VoiceRole class.

        Args:
            bot(commands.Bot): pass in bot reference
        """
        self.bot = bot
        self.data = {}
        self.db = bot.mongodb["vc_text"]

    def find(self, guild: int):
        """
        Method of VoiceRole class that will attempt to search data dictionary for the voice chat role.

        Args:
            guild(int): the guild ID of the voice chat role

        Returns:
            int: if vc role ID is found
            None: if nothing is found
        """
        try:
            return self.data[guild]
        except KeyError:
            return None

    async def update(self):
        """
        Async method for VoiceRole class that will update data from database.

        Returns:
            None
        """
        self.data = {}
        data = self.db.find({})
        for i in data:
            self.data.update({i['guild_id']: i['role_id']})

    async def local_update(self, guild: int):
        """
        Async method for VoiceRole class that will update data from specified guild database.

        Returns:
            None
        """
        try:
            self.data.pop(guild)
        except KeyError:
            pass
        data = self.db.find_one({"guild_id": guild})
        if data:
            self.data.update({guild: data['role_id']})

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Event listener for voice role class that will call update method when bot is ready.

        Returns:
            None
        """
        await self.update()

    # VC only text channel
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        """
        Event listener for VoiceRole class that gives member the voice chat role if any.

        Args:
            member(discord.Member): the member with the voice state update
            before(discord.VoiceState): voice state before
            after(discord.VoiceState): voice state after

        Returns:
            None
        """
        server = member.guild
        data = self.find(member.guild.id)

        if not data:
            return

        role = server.get_role(data)

        if not role:
            return

        if not before.channel and after.channel:
            await member.add_roles(role, reason="Joined VC")

        if before.channel and not after.channel:
            await member.remove_roles(role, reason="Left VC")

    @commands.group(aliases=['vcr'])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def vc_role(self, ctx: commands.Context):
        """
        Commands for VoiceRole and also command group named vc_role, this will return the sub-command list
        if no sub-command or the wrong one were given.

        Args:
            ctx(commands.Context): pass in context for reply

        Returns:
            None
        """
        if not ctx.invoked_subcommand:
            embed = discord.Embed(
                colour=0x2bcbba,
                title="Please specify the operation"
            )
            embed.add_field(name="set <Role mention or ID>", value="Sets the auto role upon joining vc", inline=False)
            embed.add_field(name="reset", value="Disable auto voice chat role.", inline=False)
            embed.set_footer(text="Now do the command again but with one of the above after the command",
                             icon_url=self.bot.user.avatar_url_as(size=64))
            await ctx.send(embed=embed)

    @vc_role.command()
    async def set(self, ctx: commands.Context, role: discord.Role):
        """
        Sub-command of vc_role that sets the server's voice chat role.

        Args:
            ctx(commands.Context): pass in context for reply
            role(discord.Role): the voice chat role

        Returns:
            None
        """
        if not role:
            await ctx.send("Role not found.")
            return

        data = self.find(ctx.guild.id)

        if not data:
            self.db.insert_one({"guild_id": ctx.guild.id, "role_id": role.id})
            self.data.update({ctx.guild.id: role.id})
            await ctx.send(f"Successfully set {role.mention} as VC role.")
        else:
            self.db.update_one({"guild_id": ctx.guild.id}, {"$set": {"role_id": role.id}})
            self.data[ctx.guild.id] = role.id
            await ctx.send(f"Updated server's auto vc role to {role}.")

    @vc_role.command()
    async def reset(self, ctx: commands.Context):
        """
        Sub-command of vc_role that removes vc role from the server.

        Args:
            ctx(commands.Context): pass in context for reply

        Returns:
            None
        """
        data = self.find(ctx.guild.id)

        if not data:
            await ctx.send("This server have no set VC role.")
        else:
            self.db.delete_one({"guild_id": ctx.guild.id})
            self.data.pop(ctx.guild.id)
            await ctx.send("Successfully removed VC role.")


def setup(bot: commands.Bot):
    """
    Necessary function for a cog that initialize the VoiceRole class.

    Args:
        bot (commands.Bot): passing in bot for class initialization

    Returns:
        None
    """
    bot.add_cog(VoiceRole(bot))
    print("Loaded Cog: VoiceRole")


def teardown(bot: commands.Bot):
    """
    Function to be called upon Cog unload, in this case, it will print message in CMD.

    Args:
        bot (commands.Bot): passing in bot reference for unload.

    Returns:
        None
    """
    bot.remove_cog("VoiceRole")
    print("Unloaded Cog: VoiceRole")
