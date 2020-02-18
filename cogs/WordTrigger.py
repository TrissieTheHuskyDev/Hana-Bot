import discord
from discord.ext import commands

import asyncio
import re
import unicodedata
import typing
import CustomTools


class Detector:
    """
    Detector class storing information for word scanner.

    Attributes:
        guild(int): guild ID for that scanner
        label(str): name of that word trigger
        words(list): list of banned words
        delete(bool): whether or not to auto delete message
        active(bool): whether or not the word trigger is active
    """
    def __init__(self, package):
        """
        Constructor for Detector class.

        Args:
            package: pass in mongoDB data
        """
        self.guild = package['guild_id']
        self.label = package['name']
        self.words = package['words']
        self.delete = package['auto_del']
        self.active = package['active']


class WordTrigger(commands.Cog):
    """
    Class of word trigger commands.

    Attributes:
        bot(commands.Bot): bot reference
        labels(list): emotes of word trigger setting menu
        checks(list): reaction of yes or no
        memory(dict): dictionary containing Detectors
        ignores(dict): dictionary containing people to be ignored for word trigger
    """
    def __init__(self, bot: commands.Bot):
        """
        Constructor for WordTrigger class.

        Args:
            bot(commands.Bot): pass in bot reference
        """
        self.bot = bot
        self.labels = ['💡', '🗑', '💥', '⏸']
        self.checks = ['✅', '❎']
        self.memory = {}
        self.ignores = {}
        self.wt_db = bot.mongodb["word_trigger"]
        self.ignore_db = bot.mongodb["server_wt_ignore"]
        self.wt_data_db = bot.mongodb["wt_data"]

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Event listener for WordTrigger class, this will call update method when the bot is ready.

        Returns:
            None
        """
        await self.update()

    async def update(self):
        """
        Async method for WordTrigger class that updates memory and ignores from database.

        Returns:
            None
        """
        data = self.wt_db.find({})
        self.memory = {}
        for i in data:
            try:
                self.memory[i['guild_id']].append(Detector(i))
            except KeyError:
                self.memory.update({i['guild_id']: [Detector(i)]})
        self.ignores = {}
        data = self.ignore_db.find({})
        for i in data:
            try:
                self.ignores[i['guild_id']].append((i['user_id']))
            except KeyError:
                self.ignores.update({i['guild_id']: [i['user_id']]})

    async def local_update(self, guild: int):
        """
        Async method for WordTrigger class that updates ignore and memory for the specified server.

        Args:
            guild(int): guild ID of the server to update

        Returns:
            None
        """
        data = self.wt_db.find({"guild_id": guild})
        if data:
            try:
                self.memory[guild] = []
            except KeyError:
                self.memory.update({guild: []})
            for i in data:
                self.memory[guild].append(Detector(i))

        data = self.ignore_db.find({"guild_id": guild})
        if data:
            try:
                self.ignores[guild] = []
            except KeyError:
                self.ignores.update({guild: []})
            for i in data:
                self.ignores[guild].append(i['user_id'])

    def find_ignore(self, guild: int, who: int):
        """
        Method of WordTrigger that checks whether or not the specified user has been ignored by word trigger.

        Args:
            guild(int): guild ID of the server
            who(int): user ID of the person to check

        Returns:
            bool: whether or not the specified user is ignored by word trigger
        """
        try:
            data = self.ignores[guild]
        except KeyError:
            return False
        if who in data:
            return True
        return False

    @commands.group(aliases=['wt'])
    @commands.has_permissions(manage_channels=True)
    async def word_trigger(self, ctx: commands.Context):
        """
        Command for WordTrigger class, and group of word_trigger commands. This command will send back the correct
        usage of sub-commands when wrong sub-command or none are given.

        Args:
            ctx(commands.Context): pass in context for reply

        Returns:
            None
        """
        if not ctx.invoked_subcommand:
            pre = CustomTools.prefix(self, ctx)

            embed = discord.Embed(
                title="`Word Trigger` Commands",
                colour=0xff6b6b
            )
            embed.add_field(inline=False, name=f"{pre}ignore <user mention or ID>",
                            value="Adds the mentioned user into the word trigger ignore list and ask whether or not to "
                                  "remove the user if they are already in the list.")
            embed.add_field(inline=False, name=f"{pre}il", value="List members in the word trigger's ignore list.")
            embed.add_field(inline=False, name=f"{pre}wt c <name> (True/False to auto delete message)",
                            value="Create a new word trigger menu with given info. Auto delete is default to false.")
            embed.add_field(inline=False, name=f"{pre}wt s <word trigger name>",
                            value="Open up the setting menu with option to turn on or off the mentioned word trigger, "
                                  "delete word trigger, or toggle auto delete.")
            embed.add_field(inline=False, name=f"{pre}wt + <word trigger name> <word>",
                            value="Add the word into that specified word trigger.")
            embed.add_field(inline=False, name=f"{pre}wt - <word trigger name> <existing word>",
                            value="Remove the word from the specified word trigger.")
            embed.add_field(inline=False, name=f"{pre}wt ++ <'words to add'>...",
                            value="Add multiple words into the specified word trigger separated by space.")
            embed.add_field(inline=False, name=f"{pre}wt -- <'words to remove'>...",
                            value="Remove multiple words into the specified word trigger separated by space.")
            embed.add_field(inline=False, name=f"{pre}wt list (word trigger name)",
                            value="List all the word triggers in the server no name mentioned, else will list word "
                                  "list of that word trigger.")
            embed.add_field(inline=False, name=f"{pre}wt = <word trigger name> <word>",
                            value="See if the mentioned word is in the mentioned word trigger.")
            embed.add_field(inline=False, name=f"{pre} wt data <use mention or ID>",
                            value="Display word trigger data of the mentioned user in the server")

            await ctx.send(embed=embed)

    @word_trigger.command("i")
    async def ignore(self, ctx: commands.Context, user: discord.Member = None):
        """
        Sub-command of word_trigger that will add a person to the ignore list of word trigger.

        Args:
            ctx(commands.Context): pass in context for reply and potential analysis
            user(discord.Member): user to add to the ignore list, if none then add message author

        Returns:
            None
        """
        user = ctx.author if not user else user

        data = self.find_ignore(ctx.guild.id, user.id)

        if data:
            def check(reaction1, user1):
                if (reaction1.message.id == message.id) and (user1.id == ctx.author.id):
                    if str(reaction1.emoji) in self.checks:
                        return True

            message = await ctx.send(f"User `{user.name}` is already in the ignore list. "
                                     f"Do you want to remove this user?")
            for i in self.checks:
                await message.add_reaction(emoji=i)

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=check)
            except asyncio.TimeoutError:
                await message.edit(content="Ignore list timed out ⏱")
                return

            if reaction.emoji == "❎":
                await message.edit(content="Action cancelled")
                await message.clear_reactions()

            if reaction.emoji == "✅":
                self.ignore_db.delete_one({"guild_id": ctx.guild.id, "user_id": user.id})
                self.ignores[ctx.guild.id].remove(user.id)
                await message.edit(content=f"`{user.name}` has been removed from the word trigger ignore list")
                await message.clear_reactions()

        else:
            self.ignore_db.insert_one({"guild_id": ctx.guild.id, "user_id": user.id})
            try:
                self.ignores[ctx.guild.id].append(user.id)
            except KeyError:
                self.ignores.update({ctx.guild.id: [user.id]})
            await ctx.send(f"`{user.name}` has been added into the ignore list")

    @word_trigger.command(aliases=['il'])
    async def ignore_list(self, ctx: commands.Context):
        """
        Sub-command of word_trigger, this command will list the users within the word trigger ignore list.

        Args:
            ctx(commands.Context): pass in context for reply

        Returns:
            None
        """
        try:
            data = self.ignores[ctx.guild.id]
        except KeyError:
            await ctx.send("*Cricket sound* No one is here.")
            return

        temp = "I won't scan the inputs for bad words from these people:\n"
        for i in data:
            person = ctx.guild.get_member(i)
            if person:
                temp += f"**>** {person.mention} (ID: {person.id})\n"
            else:
                self.ignores[ctx.guild.id].remove(i)
                self.ignore_db.delete_one({"guild_id": ctx.guild.id, "user_id": i})

        embed = discord.Embed(
            colour=0xb2bec3,
            title="Word Trigger Ignore List",
            description=temp
        )

        await ctx.send(embed=embed)

    @word_trigger.command(aliases=['c'])
    async def create(self, ctx: commands.Context, name: str, auto: bool = False):
        """
        Sub-command of word_trigger that creates a new word trigger.

        Args:
            ctx(commands.Context): pass in context for reply
            name(str): name of the new word trigger
            auto(bool): whether or not the message will be auto deleted, default to false

        Returns:
            None
        """
        result = self.findin(ctx.guild.id, name)
        if result is None:
            self.wt_db.insert_one({"guild_id": ctx.guild.id, "name": name, "auto_del": auto, "active": True,
                                   "words": []})
            await self.local_update(ctx.guild.id)
            await ctx.send(f"word list `{name}` has been created")

    def findin(self, guild: id, name: str):
        """
        Method for WordTrigger that will try find the word trigger scanner from what specified.

        Args:
            guild(int): guild ID of the word trigger
            name(str): name of the word trigger

        Returns:
            Detector: the word trigger / scanner associated with the input
        """
        try:
            data = self.memory[guild]
        except KeyError:
            return
        for i in data:
            if i.label == name and i.guild == guild:
                return i

    @word_trigger.command(aliases=['s'])
    async def setting(self, ctx: commands.Context, name: str):
        """
        Sub-command of word_trigger that will pull up the setting menu for the specified word trigger.

        Args:
            ctx(commands.Context): pass in context for reply
            name(str): name of the word trigger

        Returns:
            None
        """
        data = self.findin(ctx.guild.id, name)

        if not data:
            await ctx.send(f"word list `{name}` don't exist")
            return

        embed = discord.Embed(
            colour=0x55efc4 if data.active else 0xff6b81,
            title=f"Settings for `{name}` - " + ("Active" if data.active else "Inactive"),
            timestamp=ctx.message.created_at
        )
        embed.add_field(name="Word count", value=f"{len(data.words)}", inline=False)
        embed.add_field(name="Auto delete on detection", value=data.delete)
        embed.add_field(name="Options", inline=False,
                        value="💡 - Toggle on or off word list\n🗑 - Toggle on or off auto-delete\n"
                              "💥 - Delete the word list\n⏸ - Freeze the setting menu")

        message = await ctx.send(embed=embed)
        for i in self.labels:
            await message.add_reaction(emoji=i)

        def check(reaction1, user1):
            if (reaction1.message.id == message.id) and (user1.id == ctx.author.id):
                if str(reaction1.emoji) in self.labels:
                    return True

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=check)
        except asyncio.TimeoutError:
            await message.edit(embed=None, content="Word Trigger setting menu timed out ⌛")
            await message.clear_reactions()
            return

        if reaction.emoji == '💡':
            tog = False if data.active else True
            self.wt_db.update_one({"guild_id": ctx.guild.id, "name": name}, {"$set": {"active": tog}})
            await message.edit(embed=None, content=f"word list `{name}` is now " + ("on" if tog else "off"))
        if reaction.emoji == '🗑':
            auto = not data.delete
            self.wt_db.update_one({"guild_id": ctx.guild.id, "name": name}, {"$set": {"auto_del": auto}})
            await message.edit(embed=None, content=f"auto deletion for `{name}` is now " + ("on" if auto else "off"))
        if reaction.emoji == '⏸':
            embed.remove_field(2)
            embed.set_footer(text="Setting menu paused", icon_url=self.bot.user.avatar_url_as(size=64))
            await message.edit(embed=embed)
        if reaction.emoji == '💥':
            def check(reaction1, user1):
                if (reaction1.message.id == message.id) and (user1.id == ctx.author.id):
                    if reaction1.emoji in self.checks:
                        return True

            await message.clear_reactions()
            await message.edit(embed=None, content=f"You sure you want to delete word list `{name}`?")
            for i in self.checks:
                await message.add_reaction(emoji=i)

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=check)
            except asyncio.TimeoutError:
                await message.edit("Word list deletion confirmation menu timed out ⌛")
            else:
                if reaction.emoji == "❎":
                    await message.edit(content="Action cancelled")
                if reaction.emoji == "✅":
                    self.wt_db.delete_one({"guild_id": ctx.guild.id, "name": name})
                    await self.local_update(ctx.guild.id)
                    await message.edit(content=f"word list `{name}` deleted")

        if reaction.emoji in ['💡', '🗑', '💥']:
            await self.local_update(ctx.guild.id)

        await message.clear_reactions()

    @word_trigger.command(aliases=['+'])
    async def add(self, ctx: commands.Context, name: str, *, word: str):
        """
        Sub-command of word_trigger that adds a specified word into the specified word trigger.

        Args:
            ctx(commands.Context): pass in context for reply
            name(str): name of the word trigger
            word(str): the word to add into the word trigger

        Returns:
            None
        """
        data = self.findin(ctx.guild.id, name)

        if not data:
            await ctx.send(f"word list `{name}` don't exist")
            return

        word = word.lower()
        if word in data.words:
            await ctx.send(f"**{word}** is already in the word list `{name}`")

        if len(", ".join(data.words)) >= 960:
            await ctx.send("This list is getting a bit too big, try make a new one.")
            return

        data.words.append(word)

        self.wt_db.update_one({"guild_id": ctx.guild.id, "name": name}, {"$set": {"words": data.words}})
        await self.local_update(ctx.guild.id)
        await ctx.send(f"**{word}** has been added into `{name}`")

    @word_trigger.command(aliases=['-'])
    async def remove(self, ctx: commands.Context, name: str, *, word: str):
        """
        Sub-command of word_trigger that removes a specified word from the specified word trigger.

        Args:
            ctx(commands.Context): pass in context for reply
            name(str): name of the word trigger
            word(str): the word to remove from word trigger

        Returns:
            None
        """
        data = self.findin(ctx.guild.id, name)

        if not data:
            await ctx.send(f"word list `{name}` don't exist")
            return

        word = word.lower()
        if word in data.words:
            data.words.remove(word)
            self.wt_db.update_one({"guild_id": ctx.guild.id, "name": name}, {"$set": {"words": data.words}})
            await self.local_update(ctx.guild.id)
            await ctx.send(f"**{word}** has been removed from `{name}`")
        else:
            await ctx.send(f"**{word}** not found in `{name}`")

    @word_trigger.command(aliases=['++'])
    async def multi_add(self, ctx: commands.Context, name: str, *words: str):
        """
        Sub-command of word_trigger that add multiple words into the specified word trigger.

        Args:
            ctx(commands.Context): pass in context for reply
            name(str): name of the word trigger
            words(list): the words to add into the word trigger

        Returns:
            None
        """
        data = self.findin(ctx.guild.id, name)

        if not data:
            await ctx.send(f"word list `{name}` not found")
            return

        if len(", ".join(data.words)) >= 960:
            await ctx.send("This list is getting a bit too big, try make a new one.")
            return

        success = 0
        fail = 0

        for a in words:
            word = a.lower()
            if word in data.words:
                fail += 1
            else:
                data.words.append(word)
                success += 1

        self.wt_db.update_one({"guild_id": ctx.guild.id, "name": name}, {"$set": {"words": data.words}})
        await self.local_update(ctx.guild.id)
        await ctx.send(f"Successfully added **{success}** words into `{name}` and failed to add **{fail}** words.")

    @word_trigger.command(aliases=['--'])
    async def multi_remove(self, ctx: commands.Context, name: str, *words: str):
        """
        Sub-command of word_trigger that remove multiple words from the specified word trigger.

        Args:
            ctx(commands.Context): pass in context for reply
            name(str): name of the word trigger
            words(list): the words to remove from word trigger

        Returns:
            None
        """
        data = self.findin(ctx.guild.id, name)

        if not data:
            await ctx.send(f"word list `{name}` not found")
            return

        success = 0
        fail = 0

        for a in words:
            word = a.lower()
            if word in data.words:
                data.words.remove(word)
                success += 1
            else:
                fail += 1

        self.wt_db.update_one({"guild_id": ctx.guild.id, "name": name}, {"$set": {"words": data.words}})
        await self.local_update(ctx.guild.id)
        await ctx.send(f"Successfully removed **{success}** words into `{name}` and failed to remove **{fail}** words.")

    @word_trigger.command()
    async def list(self, ctx: commands.Context, name: str = None):
        """
        Sub-command of word_trigger that list either the word trigger for the server or words within a specified
        word trigger.

        Args:
            ctx(commands.Context): pass in context for reply
            name(str): name of the word trigger if any.

        Returns:
            None
        """
        if not name:
            try:
                data = self.memory[ctx.guild.id]
            except KeyError:
                await ctx.send("There is no word trigger set for this server")
            else:
                temp = []
                mes = ""
                for i in data:
                    if i.label not in data:
                        temp.append(i.label)
                        a = "Delete Word List" if i.delete else "Trigger Word List"
                        if i.active:
                            mes += f"✅ **{i.label}** - {a}\n"
                        else:
                            mes += f"❌ **{i.label}** - {a}\n"
                await ctx.send(embed=discord.Embed(
                    title="Server Word Lists",
                    description=mes,
                    colour=0x81ecec
                ))
        else:
            data = self.findin(ctx.guild.id, name)

            if not data:
                await ctx.send(f"word list `{name}` don't exist")
                return

            if len(data.words) <= 0:
                await ctx.send(f"word list `{name}` is empty")
                return

            temp = ""
            data.words.sort()
            for i in data.words:
                temp += f"**-** {i} \n"

            embed = discord.Embed(
                title=f"Words in **{name}**",
                timestamp=ctx.message.created_at,
                colour=0xffdd59
            )
            ret = CustomTools.split_string(temp, 1000)
            for i in range(len(ret)):
                embed.add_field(name=f"Word list Page{i+1}", value=ret[i])

            await ctx.send(embed=embed)

    @word_trigger.command("=")
    async def find(self, ctx: commands.Context, name: str, *, word: str):
        """
        Sub-command of word_trigger, this command will attempt to see if the specified word is in the specified word
        trigger.

        Args:
            ctx(commands.Context): pass in context for reply
            name(str): name of the word trigger to search for
            word(str): the specified word to look for

        Returns:
            None
        """
        data = self.findin(ctx.guild.id, name)

        if not data:
            await ctx.send(f"word list `{name}` don't exist")
            return

        word = word.lower()
        if word in data.words:
            await ctx.send(f"there is **{word}** in `{name}`")
        else:
            await ctx.send(f"there is no **{word}** in `{name}`")

    @word_trigger.command()
    async def data(self, ctx: commands.Context, target: typing.Union[discord.Member, discord.User, int] = None):
        """
        Sub-command of word_trigger that searches for stored user data on word trigger.

        Args:
            ctx(commands.Context): pass in context for reply
            target(typing.Union[discord.Member, discord.User, int, None]): user to search word trigger data for

        Returns:
            None
        """
        target = ctx.author if not target else target
        if isinstance(target, discord.Member) or isinstance(target, discord.User):
            target = target.id

        data = self.wt_data_db.find({"guild_id": ctx.guild.id, "user_id": target})

        if data.count() == 0:
            await ctx.send("User data not found")
        else:
            temp = "**Word**    |=>    Amount\n --------------------------------------\n"
            total = 0
            for i in data:
                temp += f"|=> **{i['word']}** |=> {i['amount']}\n"
                total += i['amount']
            us = ctx.guild.get_member(target)
            embed = discord.Embed(
                colour=0xED4C67,
                title=f"Word Trigger Data For `{us if us else target}`",
                description=temp,
                timestamp=ctx.message.created_at
            )
            embed.set_footer(icon_url=ctx.guild.icon_url_as(size=64), text=f"Trigger Total: {total}")

            embed.add_field(name="Functions:",
                            value="⏸ - Pause the menu\n💥 - Deletes User Data")

            message = await ctx.send(embed=embed)
            cus = ['⏸', '💥']

            for i in cus:
                await message.add_reaction(emoji=i)

            def rep(reaction1, user1):
                if (reaction1.message.id == message.id) and (user1.id == ctx.author.id):
                    if str(reaction1.emoji) in cus:
                        return True

            async def clear():
                embed.remove_field(0)

                await message.clear_reactions()
                await message.edit(embed=embed)

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=rep)
            except asyncio.TimeoutError:
                await clear()
                return

            if reaction.emoji == '💥':
                await message.clear_reactions()
                await message.edit(embed=None,
                                   content=f"You sure you want to delete the user data of "
                                   f"{us if us else target}?")

                def check(reaction1, user1):
                    if (reaction1.message.id == message.id) and (user1.id == ctx.author.id):
                        if reaction1.emoji in self.checks:
                            return True

                for i in self.checks:
                    await message.add_reaction(emoji=i)

                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=check)
                except asyncio.TimeoutError:
                    await message.edit(content="User data deletion menu timed out ⌛")
                else:
                    if reaction.emoji == '✅':
                        self.wt_data_db.delete_many({"guild_id": ctx.guild.id, "user_id": target})
                        await message.edit(content=f"[{us.mention if us else target}] data has been removed")
                    else:
                        await message.edit(content="User word trigger data removal cancelled.")

                await message.clear_reactions()

                return

            await clear()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Event listener for word trigger that scans for the sent message for word trigger process.

        Args:
            message(discord.Message): the new message sent

        Returns:
            None
        """
        if message.author.bot:
            return

        if message.channel.type != discord.ChannelType.text:
            return

        if message.content == "":
            return

        if self.find_ignore(message.guild.id, message.author.id):
            return

        try:
            data = self.memory[message.guild.id]
        except KeyError:
            return

        delete, word_type, problem = self.scanner(message, data)

        try:
            location = self.bot.get_cog('Notification').memory[message.guild.id]
        except KeyError:
            return

        if not location:
            return

        if len(word_type) <= 0:
            return

        if delete:
            await message.delete()
            embed = discord.Embed(
                colour=0xe74c3c,
                timestamp=message.created_at,
                description=message.content,
                title=f"Message from **{message.author}** in **{message.channel}**"
            )
            jump = await message.channel.send(f"Watch your language {message.author.mention}")
            embed.set_author(icon_url=message.guild.icon_url_as(size=128), name="Automatic message deletion")
            jump = jump.jump_url
            reason = ", ".join(problem)

            data2 = CustomTools.add_warn(self.bot, message.created_at, message.guild.id, message.author.id,
                                         self.bot.user.id, 1, f"Used banned words: {reason}")

            try:
                await message.author.send("⚠ You received an auto warn ⚠", embed=discord.Embed(
                    timestamp=message.created_at,
                    description=f"Use of **{reason}** are banned. Go wash your hands.",
                    colour=0xf1c40f
                ).set_footer(icon_url=message.author.avatar_url_as(size=64), text=f"{data2} offenses")
                                          .set_author(icon_url=message.guild.icon_url_as(size=128),
                                                      name=f"{message.guild.name}"))
            except discord.HTTPException:
                pass
        else:
            embed = discord.Embed(
                colour=0xf1c40f,
                timestamp=message.created_at,
                description=message.content,
                title=f"Message from **{message.author}** in **#{message.channel}**"
            )
            embed.set_author(icon_url=message.guild.icon_url_as(size=128), name="Word Trigger")
            jump = message.jump_url
        embed.add_field(name="Message Location", value=f"[Jump]({jump})")
        embed.add_field(name="Time", value=message.created_at.strftime("%#d %B %Y, %I:%M %p UTC"))
        embed.add_field(inline=False, name="Categories", value=f"{word_type}")
        embed.add_field(inline=False, name="Problematic words", value=f"{problem}")
        embed.set_footer(icon_url=message.author.avatar_url_as(size=64), text=f"User ID: {message.author.id}")
        embed.add_field(name="Mention", value=message.author.mention)

        for i in location:
            if i.data['trigger']:
                await message.guild.get_channel(i.channel).send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, message: discord.Message):
        """
        Event listener for word trigger that scans for the edited message for word trigger process.

        Args:
            before(discord.Message): the old message
            message(discord.Message): the new edited message

        Returns:
            None
        """
        if message.author.bot:
            return

        if message.channel.type != discord.ChannelType.text:
            return

        if message.content == "":
            return

        if self.find_ignore(message.guild.id, message.author.id):
            return

        try:
            location = self.bot.get_cog('Notification').memory[message.guild.id]
        except KeyError:
            return

        if not location:
            return

        try:
            data = self.memory[message.guild.id]
        except KeyError:
            return

        delete, word_type, problem = self.scanner(message, data)

        if len(word_type) <= 0:
            return

        if delete:
            await message.delete()
            embed = discord.Embed(
                colour=0xEA2027,
                timestamp=message.created_at,
                title=f"Message from **{message.author}** in **{message.channel}**"
            )
            embed.add_field(inline=False, name="Message Before", value=before.content)
            embed.add_field(inline=False, name="Message After Edit:", value=message.content)
            jump = await message.channel.send(f"Watch your language {message.author.mention}, even editing.")
            embed.set_author(icon_url=message.guild.icon_url_as(size=128), name="Automatic message deletion")
            jump = jump.jump_url
            reason = ", ".join(problem)

            data2 = CustomTools.add_warn(self.bot, message.created_at, message.guild.id, message.author.id,
                                         self.bot.user.id, 1, f"Used banned words in edited message: {reason}")

            try:
                await message.author.send("⚠ You received an auto warn ⚠", embed=discord.Embed(
                    timestamp=message.created_at,
                    description=f"Use of **{reason}** are banned, even in edited message. Go wash your hands.",
                    colour=0xf1c40f
                ).set_footer(icon_url=message.author.avatar_url_as(size=64), text=f"{data2} offenses")
                                          .set_author(icon_url=message.guild.icon_url_as(size=128),
                                                      name=f"{message.guild.name}"))
            except discord.HTTPException:
                pass
        else:
            embed = discord.Embed(
                colour=0xf1c40f,
                timestamp=message.created_at,
                title=f"Message edited by **{message.author}** in **#{message.channel}**"
            )
            embed.add_field(inline=False, name="Message Before:", value=before.content)
            embed.add_field(inline=False, name="Message Edited to:", value=message.content)
            embed.set_author(icon_url=message.guild.icon_url_as(size=128), name="Word Trigger")
            jump = message.jump_url
        embed.add_field(name="Message Location", value=f"[Jump]({jump})")
        embed.add_field(name="Time", value=message.created_at.strftime("%#d %B %Y, %I:%M %p UTC"))
        embed.add_field(inline=False, name="Categories", value=f"{word_type}")
        embed.add_field(inline=False, name="Problematic words", value=f"{problem}")
        embed.set_footer(icon_url=message.author.avatar_url_as(size=64), text=f"User ID: {message.author.id}")
        embed.add_field(name="Mention", value=message.author.mention)

        for i in location:
            if i.data['trigger']:
                await message.guild.get_channel(i.channel).send(embed=embed)

    def scanner(self, message: discord.Message, data: Detector):
        """
        Method for WordTrigger that passes in a message and scans it for problem.

        Args:
            message(discord.Message): the discord message to scan for
            data(Detector): pass in word lists

        Returns:
            bool: this will return whether or not the message needs the be deleted
            list: list of word trigger names that have detects the problem
            list: list of problematic words
        """

        # code from (Jack)Tewi#8723 and Commando950#0251
        temp = str(unicodedata.normalize('NFKD', message.content).encode('ascii', 'ignore')).lower()
        # https://stackoverflow.com/questions/4128332/re-findall-additional-criteria
        # https://stackoverflow.com/questions/14198497/remove-char-at-specific-index-python
        # https://stackoverflow.com/questions/1798465/python-remove-last-3-characters-of-a-string
        analyze = re.findall(r"[\w']+", (temp[:0]) + temp[2:])
        f = len(analyze) - 1
        analyze[f] = analyze[f][:-1]

        word_type = []
        problem = []
        delete = False

        for i in data:
            for w in analyze:
                if i.active:
                    if w in i.words:
                        ud = self.wt_data_db.find_one({"guild_id": message.guild.id, "user_id": message.author.id,
                                                       "category": i.label, "word": w})
                        if w not in problem:
                            problem.append(w)
                        if i.label not in word_type:
                            word_type.append(i.label)
                        if i.delete:
                            delete = True
                        if not ud:
                            self.wt_data_db.insert_one({"guild_id": message.guild.id, "user_id": message.author.id,
                                                        "category": i.label, "word": w, "amount": 1})
                        else:
                            self.wt_data_db.update_one(
                                {"guild_id": message.guild.id, "user_id": message.author.id, "category": i.label,
                                 "word": w}, {"$inc": {"amount": 1}}
                            )
        return delete, word_type, problem


def setup(bot: commands.Bot):
    """
    Necessary function for a cog that initialize the WordTrigger class.

    Args:
        bot (commands.Bot): passing in bot for class initialization

    Returns:
        None
    """
    bot.add_cog(WordTrigger(bot))
    print("Loaded Cog: WordTrigger")


def teardown(bot: commands.Bot):
    """
    Function to be called upon Cog unload, in this case, it will print message in CMD.

    Args:
        bot (commands.Bot): passing in bot reference for unload.

    Returns:
        None
    """
    bot.remove_cog("WordTrigger")
    print("Unloaded Cog: WordTrigger")
