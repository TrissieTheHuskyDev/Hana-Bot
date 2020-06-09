import re
import typing
import discord
import asyncio
import unicodedata
from discord.ext import commands


def setup(bot: commands.Bot):
    """
    Function necessary for loading Cogs. This will update AntiRaid's data from mongoDB.

    Parameters
    ----------
    bot : commands.Bot
        pass in bot reference to add Cog
    """
    bot.add_cog(Scanner(bot))
    print("Load Cog:\tScanner")


def teardown(bot: commands.Bot):
    """
    Function to be called upon unloading this Cog.

    Parameters
    ----------
    bot : commands.Bot
        pass in bot reference to remove Cog
    """
    bot.remove_cog("Scanner")
    print("Unload Cog:\tScanner")


class Detector:
    """
    Class Detector containing Scanner information and function for a server.

    Attributes
    ----------
    guild: int
        server ID for the scanner
    name: str
        name of the scanner
    words: list
        list of string of unacceptable words
    delete: bool
        whether or not scanner should delete the problematic message
    warn: bool
        whether or not scanner should warn the author of the problematic message
    active: bool
        whether or not the scanner is active and should do any action
    channels: list
        list of IDs for the channels to ignore
    users: list
        list of IDs for the users to ignore
    """

    def __init__(self, package: dict):
        self.guild = package["guild"]
        self.name = package["name"]
        self.words = package["words"]
        self.delete = package["delete"]
        self.warn = package["warn"]
        self.active = package["active"]
        self.channels = package["channels"]
        self.users = package["users"]

    def __contains__(self, target: typing.Union[discord.Member, discord.User, discord.TextChannel, str, int]):
        if isinstance(target, (discord.Member, discord.User)):
            return target.id in self.users
        if isinstance(target, discord.TextChannel):
            return target.id in self.channels
        if isinstance(target, str):
            return target in self.words
        return target in self.users or target in self.channels

    def scan(self, target: str):
        if not self.active:
            return

        ret = []

        # code from (Jack)Tewi#8723 and Commando950#0251
        temp = str(unicodedata.normalize('NFKD', target).encode('ascii', 'ignore')).lower()
        # https://stackoverflow.com/questions/4128332/re-findall-additional-criteria
        # https://stackoverflow.com/questions/14198497/remove-char-at-specific-index-python
        # https://stackoverflow.com/questions/1798465/python-remove-last-3-characters-of-a-string
        analyze = re.findall(r"[\w']+", (temp[:0]) + temp[2:])
        f = len(analyze) - 1
        analyze[f] = analyze[f][:-1]

        for i in analyze:
            if i in self.words:
                ret.append(i)

        return ret if len(ret) != 0 else None


class Scanner(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = {}
        self.s_db = bot.mongo["scanner"]
        self.verify = ["✅", "❌"]
        self.options = ['💡', '🗑', '👮', '💥', '⏸']
        self.update()

    def update(self, guild: int = None):
        if not guild:
            self.data.clear()
            data = self.s_db.find({})
        else:
            try:
                self.data[guild].clear()
            except KeyError:
                self.data.update({guild: {}})
            data = self.s_db.find({"guild": guild})
        for i in data:
            try:
                self.data[i["guild"]].update({i["name"]: Detector(i)})
            except KeyError:
                self.data.update({i["guild"]: {i["name"]: Detector(i)}})

    def find(self, guild: int, name: str):
        """
        Method that attempts to return  the Detector within self.data

        Parameters
        ----------
        guild: int
            server ID for the Detector
        name: str
            name of the Detector

        Returns
        -------
        Detector
            return the specified Detector class if found

        """
        try:
            return self.data[guild][name]
        except KeyError:
            return

    @commands.group(aliases=["s"])
    @commands.has_permissions(manage_channels=True)
    async def scanner(self, ctx: commands.Context):
        """Scanner group commands, invoke this with additional sub-command will bring up scanner help menu."""
        if not ctx.invoked_subcommand:
            pre = ctx.prefix

            embed = discord.Embed(
                title="`Scanner` Commands",
                colour=0xff6b6b
            )
            embed.add_field(inline=False, name=f"{pre}s c <name>",
                            value="Create a new scanner menu.")
            embed.add_field(inline=False, name=f"{pre}s s <scanner name>",
                            value="Open up the setting menu with option to turn on or off the mentioned scanner, "
                                  "delete scanner, toggle auto delete, or toggle auto-warn.")
            embed.add_field(inline=False, name=f"{pre}s + <scanner name> <word/phrase>",
                            value="Add the word/phrase into that specified scanner.")
            embed.add_field(inline=False, name=f"{pre}s - <scanner name> <existing word/phrase>",
                            value="Remove the word/phrase from the specified scanner.")
            embed.add_field(inline=False, name=f"{pre}s ++ <'words to add'>...",
                            value="Add multiple words into the specified scanner separated by space.")
            embed.add_field(inline=False, name=f"{pre}s -- <'words to remove'>...",
                            value="Remove multiple words into the specified scanner separated by space.")
            embed.add_field(inline=False, name=f"{pre}s list (scanner name) (page number)",
                            value="List all the scanners in the server no name mentioned, else will list word "
                                  "list of that scanner.")
            embed.add_field(inline=False, name=f"{pre}s = <scanner name> <word>",
                            value="See if the mentioned word is in the mentioned scanner.")
            embed.add_field(inline=False, name=f"{pre}s import <scanner for import> <scanner to import data from>",
                            value="Import selectable data from one scanner to another")
            embed.add_field(inline=False, name=f"{pre}s deport <scanner for modification> <scanner data reference>",
                            value="Delete selectable data from target scanner based on the specified scanner")
            embed.add_field(inline=False, name=f"{pre}s i <scanner name> <channel mention or user mention or ID>",
                            value="Add the specified item into the ignore list")
            embed.add_field(inline=False, name=f"{pre}s il (page number)",
                            value="Display the ignored users for this scanners")
            embed.add_field(inline=False, name=f"{pre}s ic (page number)",
                            value="Display the ignored channels for this scanner")

            await ctx.send(embed=embed)

    @scanner.command(aliases=["c"])
    async def create(self, ctx: commands.Context, *, name: str):
        """Create a new scanner with the specified name."""
        data = self.find(ctx.guild.id, name)
        if data:
            return await ctx.send("Scanner with the same name already exist")
        else:
            self.s_db.insert_one({"guild": ctx.guild.id, "name": name, "delete": True, "warn": False, "active": False,
                                  "words": [], "channels": [], "users": []})
            self.update(ctx.guild.id)
            await ctx.message.add_reaction(emoji="👍")

    @scanner.command(aliases=["s"])
    async def setting(self, ctx: commands.Context, *, name: str):
        """Open scanner setting menu."""
        data = self.find(ctx.guild.id, name)
        if not data:
            return await ctx.send("Can not find the specified scanner")

        embed = discord.Embed(
            colour=0x55efc4 if data.active else 0xff6b81,
            title=f"Settings for `{name}` - " + ("Active" if data.active else "Inactive"),
            timestamp=ctx.message.created_at
        )
        embed.add_field(name="Auto Delete", value=data.delete)
        embed.add_field(name="Auto Warn", value=data.warn)
        embed.add_field(name="Word Count", value=f"{len(data.words)}", inline=False)
        embed.add_field(name="Ignored User Count", value=f"{len(data.users)}", inline=False)
        embed.add_field(name="Ignored Channel Count", value=f"{len(data.channels)}", inline=False)
        embed.add_field(name="Options", inline=False,
                        value="💡 - Toggle on/off scanner\n🗑 - Toggle on/off auto-delete\n"
                              "👮 - Toggle on/off auto warn\n💥 - Delete the scanner\n⏸ - Freeze the setting menu")
        message = await ctx.send(embed=embed)
        for i in self.options:
            await message.add_reaction(emoji=i)

        def check(reaction1: discord.Reaction, user1: discord.User):
            if (reaction1.message.id == message.id) and (user1.id == ctx.author.id):
                if str(reaction1.emoji) in self.options:
                    return True

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=check)
        except asyncio.TimeoutError:
            await message.edit(embed=None, content="Word Trigger setting menu timed out ⌛")
            return await message.clear_reactions()

        if reaction.emoji == '💡':
            data.active = not data.active
            self.s_db.update_one({"guild": ctx.guild.id, "name": name}, {"$set": {"active": data.active}})
            await message.edit(embed=None,
                               content=f"word list `{name}` is now " + ("active" if data.active else "inactive"))
        elif reaction.emoji == '🗑':
            data.delete = not data.delete
            self.s_db.update_one({"guild": ctx.guild.id, "name": name}, {"$set": {"delete": data.delete}})
            await message.edit(embed=None,
                               content=f"auto deletion for `{name}` is now " + ("on" if data.delete else "off"))
        elif reaction.emoji == '👮':
            data.warn = not data.warn
            self.s_db.update_one({"guild": ctx.guild.id, "name": name}, {"$set": {"warn": data.warn}})
            return await message.edit(embed=None,
                                      content=f"auto warn for `{name}` is now " + ("on" if data.delete else "off"))
        elif reaction.emoji == '⏸':
            embed.remove_field(5)
            embed.set_footer(text="Setting menu paused", icon_url=self.bot.user.avatar_url_as(size=64))
            await message.clear_reactions()
            return await message.edit(embed=embed)
        else:
            def check(reaction1: discord.Reaction, user1: discord.User):
                if (reaction1.message.id == message.id) and (user1.id == ctx.author.id):
                    if reaction1.emoji in self.verify:
                        return True

            await message.clear_reactions()
            await message.edit(embed=None, content=f"You sure you want to delete scanner `{name}`?")
            for i in self.verify:
                await message.add_reaction(emoji=i)

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=check)
            except asyncio.TimeoutError:
                await message.edit(content="scanner deletion confirmation menu timed out ⌛")
            else:
                if reaction.emoji == "❌":
                    await message.clear_reactions()
                    return await message.edit(content="Action cancelled")
                else:
                    self.s_db.delete_one({"guild": ctx.guild.id, "name": name})
                    await message.edit(content=f"Scanner `{name}` deleted")

        self.update(ctx.guild.id)
        await message.clear_reactions()

    @scanner.command(aliases=["+"])
    async def add(self, ctx: commands.Context, name: str, *, word: str):
        """Add the specified phrase or word into the scanner"""
        data = self.find(ctx.guild.id, name)
        if not data:
            return await ctx.send("Can not find the specified role menu")

        word = word.lower()
        if word in data:
            return await ctx.send(f"**{word}** is already inside the Scanner")

        data.words.append(word)
        self.s_db.update_one({"guild": ctx.guild.id, "name": name}, {"$push": {"words": word}})
        await ctx.send(f"**{word}** has been added into scanner `{name}`")

    # TODO finish this
