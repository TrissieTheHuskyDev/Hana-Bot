import discord
from discord.ext import commands


class Ignores(commands.Cog):
    """
    A class of ignore channel commands.

    Attributes:
        bot(commands.Bot) : passing in bot reference
        data(dict) : dictionary holding in channels to ignore
    """

    def __init__(self, bot: commands.Bot):
        """
        Constructor for Ignores class.

        Args:
            bot(commands.Bot) : passing in the bot reference to append
        """
        self.bot = bot
        self.db = bot.mongodb["ignore_channel"]
        self.data = {}

    async def update(self):
        """
        Async function that updates the entire ignore channel data.

        Returns:
            None
        """
        self.data = {}
        data = self.db.find({})
        for i in data:
            try:
                self.data[i['guild_id']].append(i['channel_id'])
            except KeyError:
                self.data.update({i['guild_id']: [i['channel_id']]})

    async def local_update(self, guild: int):
        """
        Async function that updates the ignore channel data of the specified guild ID.

        Args:
            guild(int): ID of the guild to update

        Returns:
            None
        """
        data = self.db.find({"guild_id": guild})
        try:
            self.data[guild] = []
        except KeyError:
            self.data.update({guild: []})
        for i in data:
            try:
                self.data[guild].append(i['channel_id'])
            except KeyError:
                self.data({guild: [i['channel_id']]})

    def find(self, guild: int, channel: int = None):
        """
        A function that searches the ignore channels data for specified target.

        Args:
            guild(int): The Guild ID of the target
            channel(int): Target's channel ID

        Returns:
            int : ID of the channel if found
            list : if only the guild ID was specified
            None : if what specified is not found
        """
        try:
            data = self.data[guild]
        except KeyError:
            return
        if not channel:
            return data
        else:
            if channel in data:
                return channel

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Async function that will be called once when the bot is ready.

        Returns:
            None
        """
        await self.update()

    @commands.command(aliases=['ic'])
    @commands.has_permissions(manage_channels=True)
    async def ignore_channels(self, ctx: commands.Context):
        """
        Bot command for those that have managed channels permission that will
        list channels ignored for certain commands in the server.

        Args:
            ctx(commands.Context): pass in context for reply

        Returns:
            None
        """
        data = self.find(ctx.guild.id)
        display = "I take commands from all channels"

        if len(data) > 0:
            display = ""
            for i in data:
                channel = ctx.guild.get_channel(i)
                if channel is None:
                    self.db.delete_one({"guild_id": ctx.guild.id, "channel_id": i})
                else:
                    display += f"* {channel.mention}\n"
            embed = discord.Embed(
                title=f"I Ignore Normal Commands From These Channels",
                colour=0x1289A7,
                description=display,
                timestamp=ctx.message.created_at
            ).set_image(url=ctx.guild.icon_url)
            if len(display) <= 0:
                await ctx.send("I take commands from all channels")
            else:
                await ctx.send(embed=embed)
        else:
            await ctx.send(display)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def ignore(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Bot command for those that have managed channels permission that will
        ignore or un-ignored the specified channel depend on stored ignore channels.

        Args:
            ctx(commands.Context): pass in context for reply
            channel(discord.TextChannel): discord channel to ignore or un-ignore

        Returns:
            None
        """
        channel = ctx.channel if not channel else channel
        data = self.find(ctx.guild.id, channel.id)

        if not data:
            self.db.insert_one({"guild_id": ctx.guild.id, "channel_id": channel.id})
            await ctx.send(f"{channel} has been added to ignore commands list.", delete_after=5)
        else:
            self.db.delete_one({"guild_id": ctx.guild.id, "channel_id": channel.id})
            await ctx.send(f"{channel} has been removed from ignore commands list.", delete_after=5)
        await self.local_update(ctx.guild.id)


def setup(bot: commands.Bot):
    """
    Necessary function for a cog that initialize the Ignores class.

    Args:
        bot (commands.Bot): passing in bot for class initialization

    Returns:
        None
    """
    bot.add_cog(Ignores(bot))
    print("Loaded Cog: Ignores")


def teardown(bot: commands.Bot):
    """
    Function to be called upon Cog unload, in this case, it will print message in CMD.

    Args:
        bot (commands.Bot): passing in bot reference for unload.

    Returns:
        None
    """
    bot.remove_cog("Ignores")
    print("Unloaded Cog: Ignores")
