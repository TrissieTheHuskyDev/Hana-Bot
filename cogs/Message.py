import discord
from discord.ext import commands
import datetime
import typing
from CustomTools import prefix
from CustomTools import ignore_check as ic

import asyncio
import CustomTools


def image_check(link: str):
    """
    Function that checks the passed in link's end extension.

    Args:
        link(str): the link to check for

    Returns:
        bool: whether or not the passed in link contains "image" format ending
    """
    return link.lower.endswith(('.jpg', '.png', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'))


class Famous:
    """
    A class that stores the Star board information.

    Attributes:
        guild(int): guild ID of that starboard
        emote(str): this stores the emote in string or "ID" form
        custom(bool): whether or not the target emote is a custom emote
        channel(int): the channel to sent the starred message to
        req(int): amount of reaction required
    """
    def __init__(self, guild: int = None, custom: bool = None, emote: str = None, channel: int = None, req: int = None,
                 pack=None):
        """
        Constructor of class Famous.

        Args:
            guild(int): guild ID of the starboard
            custom(bool): whether or not the emote is custom
            emote(str): the stored emote in string form, can be a str(int)
            channel(int): channel ID of the "starboard"
            req(int): amount of reaction required to trigger
            pack(dict): pass in the dictionary package for alternate initialization
        """
        if pack:
            self.guild = pack['guild']
            self.channel = pack['channel']
            self.custom = pack['custom']
            self.emote = pack['emote']
            self.req = pack['num']
        else:
            self.guild = guild
            self.channel = channel
            self.custom = custom
            self.emote = emote
            self.req = req

    def to_emote(self):
        """
        Method of class Famous that returns the stored emote.

        Returns:
            int: returns ID of that emote if it's custom
            str: returns the string of that emote if it's default
        """
        if self.custom:
            return int(self.emote)
        else:
            return self.emote


class Message(commands.Cog):
    """
    A class of starboard command bot DM redirect methods.

    Attributes:
        bot(commands.Bot): bot reference
        ready(bool): indication for whether or not the cog is ready
        staring(dict): starboard data
        added(list): message ID of the starred message
        pin_db: mongoDB reference for pin collection
    """
    def __init__(self, bot: commands.Bot):
        """
        Constructor for Message class.

        Args:
            bot(commands.Bot): pass in bot reference
        """
        self.bot = bot
        self.ready = False
        self.staring = {}
        self.added = []
        self.pin_db = bot.mongodb["pin"]

    @staticmethod
    async def encode_message(message: discord.Message,
                             destination: typing.Union[discord.TextChannel, discord.DMChannel], jump: bool = False,
                             display: bool = True):
        """
        Static async method of Message class. This will encode the received message in embed format and sends it into
        destination channel.

        Args:
            message(discord.Message):
            destination: channel to send the encoded target message
            jump(bool): whether or not to include jump link, default to false
            display(bool): display target message author ID, default to true

        Returns:
            discord.Message: the sent encoded message at destination channel
        """
        if message:
            embed = discord.Embed(
                title=f"User ID: {message.author.id}",
                description=message.content,
                colour=0xdff9fb,
                timestamp=message.created_at
            )
            if message.channel.type is discord.ChannelType.private:
                embed.set_author(name=f"Received DM from {message.author.name}", icon_url=message.author.avatar_url)
            else:
                embed = discord.Embed(
                    title=f"User ID: {message.author.id}" if display else None,
                    description=message.content,
                    colour=message.author.color,
                    timestamp=message.created_at
                )
                embed.set_author(name=f"Message from {message.author.name} in {message.guild}",
                                 icon_url=message.author.avatar_url)
                embed.set_footer(text=f"{message.channel}")

            if jump:
                embed.add_field(name="Jump Link", value=f"[Message Location]({message.jump_url})", inline=False)

            if len(message.attachments) == 1:
                f = message.attachments[0]
                if image_check(f.url):
                    embed.set_image(url=f.url)
                else:
                    embed.add_field(name="File Attachment", value=f"{f.url}")

            main = await destination.send(embed=embed)

        attach = message.attachments

        if attach and len(attach) > 1:
            count = 1
            for i in attach:
                temp = discord.Embed(
                    title=f"User ID: {message.author.id}",
                    colour=0xdff9fb,
                    timestamp=message.created_at)
                if message.channel.type is discord.ChannelType.private:
                    temp.set_footer(text=f"DM from: {message.author}", icon_url=message.author.avatar_url_as(size=64))
                else:
                    temp.set_footer(text=f"Message from: {message.author} in {message.guild}",
                                    icon_url=message.author.avatar_url_as(size=64))
                    temp = discord.Embed(
                        title=f"User ID: {message.author.id}",
                        colour=message.author.color,
                        timestamp=message.created_at)

                if image_check(i.url):
                    temp.set_image(url=i.url)
                    temp.set_author(name=f"Attachment {count} [Image]")
                else:
                    temp.add_field(name=f"Attachment {count} [File]", value=f"[File {count}] ({i.url})")
                count += 1

                if jump:
                    embed.add_field(name="Jump Link", value=f"{message.jump_url}", inline=False)

                main = await destination.send(embed=temp)

                count += 1

        return main

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Cog Listener async method for Message class that calls the update method when the bot is ready.

        Returns:
            None
        """
        await self.update()

    async def update(self):
        """
        Async method of Message class that updates starboard data stored on the bot from mongoDB.

        Returns:
            None
        """
        self.ready = False
        self.staring = {}
        data = self.pin_db.find({})
        for i in data:
            self.staring.update({i['guild']: Famous(pack=i)})
        self.ready = True

    async def local_update(self, guild: int):
        """
        Async method of Message class that updates the starboard stored on bot for the specified server from mongoDB.

        Args:
            guild(int): guild ID for the starboard to update

        Returns:
            None
        """
        try:
            self.staring.pop(guild)
        except KeyError:
            pass
        data = self.pin_db.find_one({"guild": guild})
        if data:
            self.staring.update({guild: Famous(pack=data)})

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Async method of Message class that automatically redirect the message sent in bot's DM that isn't a command back
        to the bot master.

        Args:
            message(discord.Message): The message sent to the bot's DM

        Returns:
            None
        """
        if not self.ready:
            return

        # bot don't reply to itself
        if message.author == self.bot.user:
            return

        if message.author.bot:
            return

        own = self.bot.appinfo.owner

        # If receive anything in DM that is not from Owner
        if message.channel.type is discord.ChannelType.private:
            if message.author.id != own.id:
                if not message.content.startswith('[]'):
                    dm = message.author.id
                    me = await self.encode_message(message, own, False)
                    ret = ['💬', '🤷']

                    for i in ret:
                        await me.add_reaction(emoji=i)

                    def check(reaction1, user1):
                        if (reaction1.message.id == me.id) and (user1.id == own.id) and reaction1.emoji in ret:
                            return True

                    try:
                        reaction, user = await self.bot.wait_for('reaction_add', timeout=5, check=check)
                    except asyncio.TimeoutError:
                        await me.add_reaction(emoji='🕒')
                    else:
                        async def direct_message(m, uid):
                            destination = self.bot.get_user(uid)
                            if not destination.dm_channel:
                                destination = await destination.create_dm()
                            if m.content:
                                await destination.send(content=m.content)
                                await m.add_reaction(emoji='✅')

                            attach = m.attachments
                            if attach:
                                for i in attach:
                                    if image_check(i.url):
                                        await destination.send(
                                            embed=discord.Embed(timestamp=m.created_at).set_image(url=i.url))
                                    else:
                                        await destination.send(
                                            embed=discord.Embed(timestamp=m.created_at).add_field(
                                                name="Attachment:", value=i.url
                                            ))
                                await m.add_reaction(emoji='✅')

                            if not attach and not m:
                                await m.add_reaction(emoji='❌')

                        if reaction.emoji == '🤷':
                            await me.add_reaction(emoji='🕒')
                        else:
                            await me.channel.send(f"What do you want to reply **{self.bot.get_user(dm)}** with?")

                            def check(m):
                                return m.author.id == own.id and m.channel == me.channel

                            try:
                                msg = await self.bot.wait_for('message', check=check, timeout=120)
                            except asyncio.TimeoutError:
                                await me.channel.send("Timed out, reply cancelled.")
                            else:
                                await direct_message(msg, dm)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """
        Async method of Message class that automatically relay any message change in bot's DM back to bot master.

        Args:
            before(discord.Message): before message
            after(discord.Message):  after message

        Returns:
            None
        """
        if after.author == self.bot.user:
            return

        if after.author.bot:
            return

        # If receive anything in DM that is not from Owner
        if after.author.id != self.bot.appinfo.owner.id:
            if not after.content.startswith('[]'):
                if after.channel.type is discord.ChannelType.private:
                    embed = discord.Embed(
                        title=f"User ID: {after.author.id}",
                        colour=0xdff9fb,
                        timestamp=after.created_at
                    )
                    embed.set_author(name=f"Edited message in DM from {after.author.name}",
                                     icon_url=after.author.avatar_url)

                    embed.add_field(name="Before", value=before.content, inline=False)
                    embed.add_field(name="After", value=after.content, inline=False)

                    await self.bot.appinfo.owner.send(embed=embed)

    @commands.command(aliases=["getm"])
    async def getM(self, ctx: commands.Context, target: int, chan: discord.TextChannel = None):
        """
        command and async method of the Message class, this will attempt to fetch message in that specified channel if
        available to the user.

        Args:
            ctx(commands.Context): pass in context for reply
            target(int): the target message ID to fetch
            chan(discord.TextChannel): text channel of the target message, if none the scan from current one

        Returns:
            None
        """
        if ic(self, ctx):
            return

        chan = ctx.channel if not chan else chan
        if not chan:
            await ctx.send("Can not find the channel")
            return
        message = await chan.fetch_message(target)
        if not message:
            await ctx.send("Can not find target message")
            return

        if chan.permissions_for(ctx.author).read_messages:
            await self.encode_message(message, ctx.channel, True)
        else:
            await ctx.send("Where is the message from? Can you see it?")

    @commands.command(aliases=["force_get"])
    @commands.check(CustomTools.BotCommanders.has_control)
    async def FGetM(self, ctx: commands.Context, target: int, chan: int):
        """
        Command and async method of the Message class that fetch message from any channel the bot can see,
        bot admins only.

        Args:
            ctx(commands.Context): pass in context for reply
            target(int): target message ID
            chan(int): target channel ID

        Returns:
            None
        """
        channel = await self.bot.fetch_channel(chan)
        if channel:
            message = await channel.fetch_message(target)
            if message:
                await self.encode_message(message, ctx.channel, True)

    @commands.group(aliases=['fb'])
    @commands.guild_only()
    async def fame_board(self, ctx: commands.Context):
        """
        Command and async method of Message, group command named fame_board and will send message on wrong usage or
        no additional param.

        Args:
            ctx(commands.Context): pass in context for reply

        Returns:
            None
        """
        if not ctx.invoked_subcommand:
            if not ic(self, ctx.channel):
                pre = prefix(self, ctx)
                embed = discord.Embed(
                    title="`Message` and Star board Commands",
                    colour=0xf1c40f
                )
                embed.add_field(inline=False, name=f"{pre}fb info",
                                value="Obtain information about the fame board if it exist")
                embed.add_field(inline=False, name=f"{pre}fb c <channel ID / mention> (emote amount req)",
                                value="Create a fame board with the requirement if it don't exist, emote amount "
                                      "default to 3 if not specified")
                embed.add_field(inline=False, name=f"{pre}fb delete", value="Removes fame board if it exist")
                embed.add_field(inline=False, name=f"{pre}modify <channel mention or ID>",
                                value="Changes the star board target channel")
                await ctx.send(embed=embed)
        # help panel

    @fame_board.command()
    async def info(self, ctx: commands.Context):
        """
        Async method of class Method and sub-command of fame_board. Shows the fame board info of that server if any.

        Args:
            ctx(commands.Context): pass in context for reply

        Returns:
            None
        """
        try:
            data = self.staring[ctx.guild.id]
        except KeyError:
            await ctx.send("No fame menu has been set up.")
        else:
            if not ic(self, ctx.channel):
                if data.custom:
                    emote = self.bot.get_emoji(data.to_emote())
                    if not emote:
                        await ctx.send("Something went wrong [emote deleted], please re-setup the fame board.")
                        self.pin_db.delete_one({"guild": ctx.guild.id})
                        self.staring.pop(ctx.guild.id)
                        return
                else:
                    emote = data.to_emote()

                chan = ctx.guild.get_channel(data.channel)

                if not chan:
                    self.pin_db.delete_one({"channel": data.channel})
                    self.staring.pop(ctx.guild.id)
                    await ctx.send("Something went wrong [channel deleted], please re-setup the fame board.")
                    return

                msg = await ctx.send(embed=discord.Embed(
                    title=f"{emote} Fame Board{emote}",
                    colour=0xfeca57
                ).add_field(name="Channel", value=f"{chan}"))
                await msg.add_reaction(emoji=emote)

    @fame_board.command(aliases=['c'])
    @commands.has_permissions(manage_channels=True)
    async def create(self, ctx: commands.Context, channel: discord.TextChannel = None, num: int = 3):
        """
        Async method of class Message and sub-command of fame_board. Will attempt to create fame board for that server
        if none, and this command will need manage channel permission.

        Args:
            ctx(commands.Context): pass in context for reply and process
            channel(discord.TextChannel): the text channel the starred message will forward to
            num(int): number of reactions required

        Returns:
            None
        """
        try:
            self.staring[ctx.guild.id]
        except KeyError:
            msg = await ctx.send("Now react to this message to setup the emote.")
            channel = ctx.channel if not channel else channel

            def check(reaction1, user1):
                if (reaction1.message.id == msg.id) and (user1.id == ctx.author.id):
                    return True

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=15, check=check)
            except asyncio.TimeoutError:
                await msg.edit(content="Timed out, action cancelled.")
                return

            if reaction.custom_emoji:
                if reaction.emoji.guild_id != ctx.guild.id:
                    await ctx.send("Please use default emote or emote from this server.")
                    return
                emote = str(reaction.emoji.id)
            else:
                emote = reaction.emoji

            self.staring.update({ctx.guild.id: Famous(ctx.guild.id, reaction.custom_emoji, emote, channel.id, num)})
            data = self.staring[ctx.guild.id]
            self.pin_db.insert_one({"guild": data.guild, "channel": data.channel, "custom": data.custom,
                                    "emote": data.emote, "num": num})
            await msg.add_reaction(emoji='✔')

        else:
            await ctx.send("Fame board is already setup.")

    @fame_board.command()
    @commands.has_permissions(manage_channels=True)
    async def delete(self, ctx: commands.Context):
        """
        Async method of class Message and sub-command of fame_board. Will require user to have manage channel
        permission, this command will attempt to delete fame board of that server if any.

        Args:
            ctx(commands.Context): pass in context for reply and process

        Returns:
            None
        """
        try:
            self.staring[ctx.guild.id]
        except KeyError:
            await ctx.send("No fame board has been setup in this server.")
        else:
            self.staring.pop(ctx.guild.id)
            self.pin_db.delete_one({"guild": ctx.guild.id})
            await ctx.send("Fame board disabled.")

    @fame_board.command()
    @commands.has_permissions(manage_channels=True)
    async def modify(self, ctx: commands.Context, arg: typing.Union[discord.TextChannel, int]):
        """
        Async method of Message class and sub-command of fame_board. User require manage channels to use and this
        command will either modify the target text channel or the reaction amount of the fame board.

        Args:
            ctx(commands.Context): pass in context for reply
            arg(typing.Union[discord.TextChannel, int]): pass in either discord channel to modify target channel or int
                                                         to modify the reaction amount

        Returns:
            None
        """
        try:
            data = self.staring[ctx.guild.id]
        except KeyError:
            await ctx.send("Fame board has not been setup.")
            return

        if isinstance(arg, discord.TextChannel):
            if data.channel == arg.id:
                await ctx.send("Channel remain unchanged.")
                return

            self.pin_db.update_one({"guild": ctx.guild.id}, {"$set": {"channel": arg.id}})
        else:
            if arg < 101:
                self.pin_db.update_one({"guild": ctx.guild.id}, {"$set": {"num": arg}})
            else:
                await ctx.send("Can not find that channel or the reaction requirement is too high")
                return

        await self.local_update(ctx.guild.id)
        await ctx.send("Updated!")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        """
        Async method of Message class. On reaction detected by the bot, it will scan whether or not server have
        fame board setup and perform the appropriate action.

        Args:
            reaction(discord.Reaction): reaction received
            user(discord.User): user of that reaction

        Returns:
            None
        """
        if user.bot:
            return
        if reaction.message.channel.type is discord.ChannelType.private:
            return
        if reaction.message.id in self.added:
            return
        if (datetime.datetime.utcnow() - reaction.message.created_at).total_seconds() > 120:
            return

        try:
            data = self.staring[reaction.message.guild.id]
        except KeyError:
            return
        if reaction.count >= data.req:
            ok = False
            if reaction.custom_emoji:
                if reaction.emoji.id == int(data.emote):
                    ok = True
            else:
                if reaction.emoji == data.emote:
                    ok = True
            if ok:
                chan = reaction.message.guild.get_channel(data.channel)
                self.added.append(reaction.message.id)
                await self.encode_message(reaction.message, chan, True, False)


def setup(bot: commands.Bot):
    """
    Necessary function for a cog that initialize the Message class.

    Args:
        bot (commands.Bot): passing in bot for class initialization

    Returns:
        None
    """
    bot.add_cog(Message(bot))
    print("Loaded Cog: Message")


def teardown(bot: commands.Bot):
    """
    Function to be called upon Cog unload, in this case, it will print message in CMD.

    Args:
        bot (commands.Bot): passing in bot reference for unload.

    Returns:
        None
    """
    bot.remove_cog("Message")
    print("Unloaded Cog: Message")
