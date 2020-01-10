from discord.ext import commands


class Prefix(commands.Cog):
    """
    class of Prefix commands.

    Attributes:
        bot(commands.Bot): bot reference
        prefix(dict): dictionary contains the custom prefix setting for servers
        db: database connection "custom_prefix"
    """
    def __init__(self, bot: commands.Bot):
        """
        Constructor for Prefix class.

        Args:
            bot(commands.Bot): pass in bot reference
        """
        self.bot = bot
        self.prefix = {}
        self.db = bot.mongodb["custom_prefix"]

    async def update(self):
        """
        Async method that updates the prefix dictionary from database.

        Returns:
            None
        """
        self.prefix = {}
        data = self.db.find({})
        for i in data:
            self.prefix.update({i['guild_id']: i['prefix']})

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Event listener for Prefix class that class update method when the bot is ready.

        Returns:
            None
        """
        await self.update()

    # change prefix for the guild
    @commands.group()
    @commands.guild_only()
    async def prefix(self, ctx: commands.Context):
        """
        Command of Prefix class and command group named prefix, this will return the custom prefix of the bot if any
        on the server.

        Args:
            ctx(commands.Context): pass in context for analysis and reply

        Returns:
            None
        """
        if not ctx.invoked_subcommand:
            try:
                data = self.prefix[ctx.guild.id]
            except KeyError:
                data = None

            if data is None:
                await ctx.send("The default: **[]**")
            else:
                await ctx.send(f"Prefix for this server is: **{data}**")

    @prefix.command()
    @commands.has_permissions(manage_guild=True)
    async def set(self, ctx: commands.Context, pre: str):
        """
        Sub-command of prefix group, this command will attempt to modify the custom prefix on the server or remove it.

        Args:
            ctx(commands.Context): pass in context for reply
            pre(str): the new custom prefix or default [] to disable custom prefix

        Returns:
            None
        """
        try:
            data = self.prefix[ctx.guild.id]
        except KeyError:
            data = None

        if pre == "[]":
            if not data:
                await ctx.send("🤷 Nothing has changed.")
            else:
                self.db.delete_one({"guild_id": ctx.guild.id})
                self.prefix.pop(ctx.guild.id)
                await ctx.send("Server prefix have been reset to: **[]**.")
            return

        if data is None:
            self.db.insert_one({"guild_id": ctx.guild.id, "prefix": pre})
            self.prefix.update({ctx.guild.id: pre})
            await ctx.send(f"Server prefix have been set to: **{pre}**.")
        else:
            self.db.update_one({"guild_id": ctx.guild.id}, {"$set": {"prefix": pre}})
            self.prefix[ctx.guild.id] = pre
            await ctx.send(f"Server prefix have been updated to: **{pre}**.")


def setup(bot: commands.Bot):
    """
    Necessary function for a cog that initialize the Prefix class.

    Args:
        bot (commands.Bot): passing in bot for class initialization

    Returns:
        None
    """
    bot.add_cog(Prefix(bot))
    print("Loaded Cog: Prefix")


def teardown(bot: commands.Bot):
    """
    Function to be called upon Cog unload, in this case, it will print message in CMD.

    Args:
        bot (commands.Bot): passing in bot reference for unload.

    Returns:
        None
    """
    bot.remove_cog("Prefix")
    print("Unloaded Cog: Prefix")
