import discord
from discord.ext import commands
import datetime
import unicodedata
import re
import CustomTools


class BadNicknames:
    """
    Class BadNicknames used to store the words tos can for in name.

    Attributes:
        show(list): list of banned names
        switch(bool): whether or not to change / give nickname
        guild(int): guild ID the name scanner belong to
        change(str): the nickname to give when user uses banned nickname
    """
    def __init__(self, package):
        """
        Constructor for BadNicknames.

        Args:
            package: the passed in database data
        """
        self.show = package['bad']
        self.switch = package['power']
        self.guild = package['guild_id']
        self.change = package['switch_to']


class ScanName(commands.Cog):
    """
    Commands of ScanName for the bot.

    Attributes:
        bot(commands.Bot): the bot reference
        nicking(dict): dictionary that stores the BadNicknames
        db: mongoDB "bad_nicks" reference
    """
    def __init__(self, bot: commands.Bot):
        """
        Constructor for ScanName class.

        Args:
            bot(commands.Bot): pass in bot reference
        """
        self.bot = bot
        self.nicking = {}
        self.db = bot.mongodb["bad_nicks"]

    async def update(self):
        """
        Async method for ScanName class that updates the nicking dictionary from database.

        Returns:
            None
        """
        self.nicking = {}
        data = self.db.find({})
        for i in data:
            self.nicking.update({i['guild_id']: BadNicknames(i)})

    async def local_update(self, guild: int):
        """
        Async method for ScanName class that updates the specified server nicking dictionary from database.

        Returns:
            None
        """
        data = self.db.find_one({"guild_id": guild})
        try:
            self.nicking[guild] = BadNicknames(data)
        except KeyError:
            self.nicking.update({guild: BadNicknames(data)})

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Event listener that calls the update function when the bot is ready.

        Returns:
            None
        """
        await self.update()

    @commands.group(aliases=['ns'])
    @commands.has_permissions(manage_nicknames=True)
    async def name_scan(self, ctx: commands.Context):
        """
        Command for ScanName class and command group named nickname_scan, this will return the current name scanner
        status menu.

        Args:
            ctx(commands.Context): pass in context for reply

        Returns:
            None
        """
        if not ctx.invoked_subcommand:
            try:
                self.nicking[ctx.guild.id]
            except KeyError:
                self.db.insert_one({"guild_id": ctx.guild.id, "bad": [], "switch_to": "Bad Name", "power": True})
                await self.local_update(ctx.guild.id)
            data = self.nicking[ctx.guild.id]
            data.show.sort()
            embed = discord.Embed(
                title="Name Scanner" + ("[Active]" if data.switch else "[Inactive]"),
                timestamp=ctx.message.created_at,
                colour=0x2ed573 if data.switch else 0xff4757
            ).set_footer(text=" ", icon_url=self.bot.user.avatar_url_as(size=64))
            embed.add_field(name="Switch to", inline=False, value=data.change)
            embed.add_field(name="Words", inline=False, value=", ".join(data.show) if len(data.show) > 0 else "None")
            await ctx.send(embed=embed)

    async def find(self, ctx: commands.Context):
        """
        Async function of ScanName class that will attempt to find the name scanner and reply if nothing is found.

        Args:
            ctx(commands.Context): pass in context for reply

        Returns:
            BadNicknames: if found in nicking dictionary
        """
        try:
            return self.nicking[ctx.guild.id]
        except KeyError:
            try:
                pre = self.bot.get_cog('Prefix').prefix[ctx.guild.id]
            except KeyError:
                pre = '[]'
            except AssertionError:
                pre = '[]'
            await ctx.send(f"This server have not setup `Name Scanner`, try **{pre}ns** to set it up.")

    @name_scan.command()
    async def toggle(self, ctx: commands.Context):
        """
        Sub-command of name_scan that will swiches the name scanner on or off depending on it's current status.

        Args:
            ctx(commands.Context): pass in context for reply

        Returns:
            None
        """
        data = await self.find(ctx)
        if data:
            self.db.update_one({"guild_id": ctx.guild.id}, {"$set": {"power": not data.switch}})
            msg = "`Name Scanner` is now off" if data.switch else "`Name Scanner` is now on"
            self.nicking[ctx.guild.id].switch = False if data.switch else True
            await ctx.send(msg)

    @name_scan.command()
    async def change(self, ctx: commands.Context, *, to: str):
        """
        Sub-command of name_scan that will change the nickname to give/change for name scanner.

        Args:
            ctx(commands.Context): pass in context for reply
            to(str): what to change the nickname to if it's bad

        Returns:
            None
        """
        data = await self.find(ctx)
        if data:
            if to.lower() not in data.show:
                self.db.update_one({"guild_id": ctx.guild.id}, {"$set": {"switch_to": to}})
                self.nicking[ctx.guild.id].change = to
                await ctx.send(f"Bad nicknames or username will be changed to `{to}`.")
            else:
                await ctx.send("Not funny!!")

    @name_scan.command(aliases=['+'])
    async def add(self, ctx: commands.Context, *, word: str):
        """
        Sub-command of name_scan that adds a specified word to the name scanner.

        Args:
            ctx(commands.Context): pass in context for reply
            word(str): the word to add to the name scanner

        Returns:
            None
        """
        data = await self.find(ctx)
        if data:
            word = word.lower()
            if word in data.show:
                await ctx.send(f"`{word}` is already in the **Name Scanner**")
            else:
                if word.lower() != data.change.lower():
                    data.show.append(word)
                    self.nicking[ctx.guild.id].show = data.show
                    self.db.update_one({"guild_id": ctx.guild.id}, {"$set": {"bad": data.show}})
                    await ctx.send(f"`{word}` has been added into **Name Scanner**")
                else:
                    await ctx.send("I see what you are trying to do 😰")

    @name_scan.command(aliases=['-'])
    async def remove(self, ctx: commands.Context, *, word: str):
        """
        Sub-command of name_scan that removes a specified word from the name scanner.

        Args:
            ctx(commands.Context): pass in context for reply
            word(str): the word to remove from the name scanner

        Returns:
            None
        """
        data = await self.find(ctx)
        if data:
            word = word.lower()
            if word not in data.show:
                await ctx.send(f"`{word}` is not in the **name Scanner**")
            else:
                data.show.remove(word)
                # self.nicking[ctx.guild.id].show = data.show
                self.db.update_one({"guild_id": ctx.guild.id}, {"$set": {"bad": data.show}})
                await ctx.send(f"`{word}` has been removed from **Name Scanner**")

    @name_scan.command(aliases=['++'])
    async def multi_add(self, ctx: commands.Context, *words: str):
        """
        Sub-command of name_scan that add specified words to the name scanner.

        Args:
            ctx(commands.Context): pass in context for reply
            words(list): the words to add to the name scanner

        Returns:
            None
        """
        data = await self.find(ctx)
        if data:
            success = 0
            fail = 0
            for i in words:
                i = i.lower()
                if i in data.show:
                    fail += 1
                elif i == data.change.lower():
                    fail += 1
                else:
                    success += 1
                    data.show.append(i)
            if success > 0:
                self.db.update_one({"guild_id": ctx.guild.id}, {"$set": {"bad", data.show}})
                self.nicking[ctx.guild.id].show = data.show
            await ctx.send(f"Successfully added `{success}` words and failed `{fail}`.")

    @name_scan.command(aliases=['--'])
    async def multi_remove(self, ctx: commands.Context, *words: str):
        """
        Sub-command of name_scan that remove specified words from the name scanner.

        Args:
            ctx(commands.Context): pass in context for reply
            words(list): the words to remove from the name scanner

        Returns:
            None
        """
        data = await self.find(ctx)
        if data:
            success = 0
            fail = 0
            for i in words:
                i = i.lower()
                if i in data.show:
                    success += 1
                    data.show.remove(i)
                else:
                    fail += 1
            if success > 0:
                self.db.update_one({"guild_id": ctx.guild.id}, {"$set": {"bad", data.show}})
                self.nicking[ctx.guild.id].show = data.show
            await ctx.send(f"Successfully removed `{success}` words and failed `{fail}`.")

    @name_scan.command(aliases=['import'])
    async def load(self, ctx: commands.Context, *, name: str):
        """
        Sub-command of name_scan that will attempt to import the word list from an existing word trigger.

        Args:
            ctx(commands.Context): pass in context for reply
            name(str): name of the word trigger for import

        Returns:
            None
        """
        data = await self.find(ctx)
        if data:
            success = 0
            fail = 0
            try:
                temp = self.bot.get_cog('WordTrigger')
                put = temp.memory[ctx.guild.id]
            except AttributeError:
                await ctx.send("System busy, try again later")
            except KeyError:
                await ctx.send("I don't think this server have any word trigger to load from.")
            else:
                target = None
                for i in put:
                    if i.label == name:
                        target = i
                        break
                if not target:
                    await ctx.send(f"Can't find `{name}` in this server's word triggers")
                else:
                    for i in target.words:
                        i = i.lower()
                        if i in data.show:
                            fail += 1
                        else:
                            data.show.append(i)
                            success += 1
                    if success > 0:
                        self.nicking[ctx.guild.id].show = data.show
                        self.db.update_one({"guild_id": ctx.guild.id}, {"$set": {"bad", data.show}})
                    await ctx.send(f"Successfully loaded `{success}` words and failed `{fail}` from **{name}** into "
                                   f"Name Scanner.")

    @name_scan.command(aliases=[])
    async def unload(self, ctx: commands.Context, *, name: str):
        """
        Sub-command of name_scan that will attempt to remove words from name scan based on specified word list of word
        trigger.

        Args:
            ctx(commands.Context): pass in context for reply
            name(str): name of the word trigger to scan

        Returns:
            None
        """
        data = await self.find(ctx)
        if data:
            success = 0
            fail = 0
            try:
                temp = self.bot.get_cog('WordTrigger')
                put = temp.memory[ctx.guild.id]
            except AttributeError:
                await ctx.send("System busy, try again later")
            except KeyError:
                await ctx.send("I don't think this server have any word trigger to unload from.")
            else:
                target = None
                for i in put:
                    if i.label == name:
                        target = i
                        break
                if not target:
                    await ctx.send(f"Can't find `{name}` in this server's word triggers")
                else:
                    for i in target.words:
                        i = i.lower()
                        if i in data.show:
                            success += 1
                            data.show.remove(i)
                        else:
                            fail += 1
                    if success > 0:
                        self.nicking[ctx.guild.id].show = data.show
                        self.db.update_one({"guild_id": ctx.guild.id}, {"$set": {"bad", data.show}})
                    await ctx.send(f"Successfully unloaded `{success}` words and failed `{fail}` from in Name Scanner "
                                   f"base on **{name}**.")

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        """
        Event listener for ScanName class that detects username update and scans it for banned words and take
        appropriate active.

        Args:
            before(discord.User): user before the update
            after(discord.User): user after the update

        Returns:
            None
        """
        if (before.name != after.name) or (before.discriminator != after.discriminator):
            try:
                cog = self.bot.get_cog("Notification")
            except AssertionError:
                cog = None

            is_in = []
            for i in self.bot.guilds:
                if i.get_member(after.id):
                    is_in.append(i)

            for i in is_in:
                bad_name = self.scan_name(i.id, after.name, after.id)
                if not cog:
                    data = None
                else:
                    try:
                        data = cog.memory[i.id]
                    except KeyError:
                        data = None
                if not bad_name:
                    if data:
                        for a in data:
                            if a.data['member_update']:
                                channel = self.bot.get_channel(a.channel)
                                if not channel:
                                    self.db.delete_many({"guild_id": i.guild, "channel_id": i.channel})
                                    await cog.local_update(i.guild)
                                else:
                                    embed = discord.Embed(
                                        colour=0x45aaf2,
                                        timestamp=datetime.datetime.utcnow(),
                                        description=after.mention
                                    )
                                    embed.set_author(name="✍ Username change!", icon_url=after.avatar_url)
                                    embed.add_field(name="Before", value=before.display_name, inline=False)
                                    embed.add_field(name="Now", value=after.display_name, inline=False)

                                    await channel.send(embed=embed)
                else:
                    member = i.get_member(after.id)
                    await member.edit(nick=self.nicking[i.id].change, reason="Bad Username")

                    current = datetime.datetime.utcnow()
                    reason = ", ".join(bad_name)
                    CustomTools.add_warn(self.bot, current, i.id, member.id, None, 1,
                                         f"Username contains banned words: {reason}")

                    if data:
                        for a in data:
                            if a.data['trigger']:
                                channel = self.bot.get_channel(a.channel)
                                if not channel:
                                    self.bot.mongodb["system_message"].delete_many({"guild_id": i.guild,
                                                                                    "channel_id": i.channel})
                                    await cog.local_update(i.guild)
                                else:
                                    embed = discord.Embed(
                                        colour=0xF79F1F,
                                        timestamp=datetime.datetime.utcnow(),
                                        description=after.mention
                                    )
                                    embed.set_author(icon_url=after.avatar_url, name="🚨 Bad Username!")
                                    embed.add_field(name="Triggered Words", value=reason)
                                    await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """
        Event listener for ScanName class that detects member nickname update and scans it to take appropriate action.

        Args:
            before(discord.Member): member before update
            after(discord.Member): member after update

        Returns:
            None
        """
        if before.nick != after.nick:
            self_change = False
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                if entry.user.id == entry.target.id and after.id == entry.target.id:
                    self_change = True

            if not self_change:
                return
            else:
                try:
                    temp = self.bot.get_cog("Notification")
                    data = temp.memory[after.guild.id]
                except KeyError:
                    return
                except AssertionError:
                    return

                bad_nick = self.scan_name(after.guild.id, after.nick, after.id)
                if bad_nick:
                    await after.edit(nick=self.nicking[after.guild.id].change, reason="Bad Username")

                    current = datetime.datetime.utcnow()
                    reason = ", ".join(bad_nick)
                    data2 = CustomTools.add_warn(self.bot, current, after.guild.id, after.id, None, 1,
                                                 f"Nickname contains banned words: {reason} in "
                                                 f"{self.bot.get_guild(after.guild.id).name}")

                    try:
                        await after.send("⚠ You received an auto warn ⚠", embed=discord.Embed(
                            timestamp=current,
                            description=f"Having **{reason}** in your nickname isn't allowed here.",
                            colour=0xf1c40f
                        ).set_footer(icon_url=after.avatar_url_as(size=64), text=f"{data2} offenses")
                                         .set_author(icon_url=after.guild.icon_url, name=f"{after.guild.name}"))
                    except discord.HTTPException:
                        pass

                for i in data:
                    if i.data['member_update'] and not bad_nick:
                        channel = self.bot.get_channel(i.channel)
                        if not channel:
                            self.bot.mongodb["system_message"].delete_many({"guild_id": i.guild})
                            return

                        embed = discord.Embed(
                            timestamp=datetime.datetime.utcnow(),
                            colour=0x9980FA,
                            description=after.mention
                        )
                        embed.set_author(name="✍ Nickname change!", icon_url=after.avatar_url)
                        if before.nick:
                            embed.add_field(name="Before", value=before.nick, inline=False)
                        if after.nick:
                            embed.add_field(name="Now", value=after.nick, inline=False)

                        await channel.send(embed=embed)
                    if bad_nick:
                        if i.data['trigger']:
                            channel = self.bot.get_channel(i.channel)
                            if not channel:
                                self.bot.mongodb["system_message"].delete_many({"guild_id": i.guild,
                                                                                "channel_id": i.channel})
                                await temp.local_update(i.guild)
                            else:
                                embed = discord.Embed(
                                    colour=0xF79F1F,
                                    timestamp=datetime.datetime.utcnow(),
                                    description=after.mention
                                )
                                embed.set_author(icon_url=after.avatar_url, name="🚨 Bad Nickname!")
                                embed.add_field(name="Triggered Words", value=", ".join(bad_nick))
                                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Event listener for ScanName that scans the newly joined member's username and take appropriate action.

        Args:
            member(discord.Member): the newly joined member

        Returns:
            None
        """
        scan = self.scan_name(member.guild.id, member.name, member.id)
        if scan:
            await member.edit(nick = self.nicking[member.guild.id].change, reason="Bad username on join")

            try:
                temp = self.bot.get_cog("Notification")
                data = temp.memory[member.guild.id]
            except KeyError:
                return
            except AssertionError:
                return
            for i in data:
                if i.data['trigger']:
                    channel = self.bot.get_channel(i.channel)
                    if not channel:
                        self.bot.mongodb["system_message"].delete_many({"guild_id": i.guild, "channel_id": i.channel})
                        await temp.local_update(i.guild)
                    else:
                        embed = discord.Embed(
                            colour=0xF79F1F,
                            timestamp=datetime.datetime.utcnow(),
                            description=member.mention
                        )
                        embed.set_author(icon_url=member.avatar_url, name="🚨 Bad Name on Join ⚠")
                        embed.add_field(name="Triggered Words", value=", ".join(scan))
                        await channel.send(embed=embed)

    def scan_name(self, guild: int, name: str, num: int):
        """
        Method for ScanName class that will try scan the given name.

        Args:
            guild(int): the guild ID
            name(str): the name to scan
            num(int): that user ID

        Returns:
            list: list of un-acceptable words within the given name
        """
        if not name:
            return
        try:
            ignore = self.bot.get_cog("WordTrigger").ignores[guild]
        except AssertionError:
            pass
        except KeyError:
            pass
        else:
            if num in ignore:
                return

        try:
            data = self.nicking[guild]
        except KeyError:
            return

        if not data.switch:
            return
        # code from (Jack)Tewi#8723 and Commando950#0251
        temp = str(unicodedata.normalize('NFKD', name).encode('ascii', 'ignore')).lower()
        # https://stackoverflow.com/questions/4128332/re-findall-additional-criteria
        # https://stackoverflow.com/questions/14198497/remove-char-at-specific-index-python
        # https://stackoverflow.com/questions/1798465/python-remove-last-3-characters-of-a-string
        analyze = re.findall(r"[\w']+", (temp[:0]) + temp[2:])
        f = len(analyze) - 1
        analyze[f] = analyze[f][:-1]
        problem = []
        for i in data.show:
            if i in analyze:
                problem.append(i)
        if len(problem) <= 0:
            return
        else:
            return problem


def setup(bot: commands.Bot):
    """
    Necessary function for a cog that initialize the ScanName class.

    Args:
        bot (commands.Bot): passing in bot for class initialization

    Returns:
        None
    """
    bot.add_cog(ScanName(bot))
    print("Loaded Cog: ScanName")


def teardown(bot: commands.Bot):
    """
    Function to be called upon Cog unload, in this case, it will print message in CMD.

    Args:
        bot (commands.Bot): passing in bot reference for unload.

    Returns:
        None
    """
    bot.remove_cog("ScanName")
    print("Unloaded Cog: ScanName")
