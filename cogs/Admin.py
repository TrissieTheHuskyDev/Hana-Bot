import discord
from discord import Webhook, AsyncWebhookAdapter
from discord.ext import commands, tasks

import aiohttp
import asyncio
import random
import typing
from CustomTools import BotCommanders as Control


def image_check(name: str):
    """
    A function that checks the string end for image file suffix.

    Args:
        name (str): the string to test the suffix for

    Returns:
        True: if the suffix suffix contains image extension
        False; if the string suffix does not contain image extension
    """
    name = name.lower()
    checks = [".jpg", ".png", ".jpeg", ".gif", ".webp"]
    for i in checks:
        if name.endswith(i):
            return True
    return False


async def send(ctx: commands.Context, args: str, destination: typing.Union[discord.TextChannel, discord.User,
                                                                           discord.Member]):
    """
    A function that sends message to the input location.

    Args:
        ctx (discord.Context): passing in the context for send status
        args (str): the message to send
        destination (typing.Union[discord.TextChannel, discord.User, discord.Member]):
            Send message to either DM or a channel

    Returns:
        None
    """
    if not destination:
        await ctx.message.add_reaction(emoji='❌')
        await ctx.send("Please specify the destination.", delete_after=5)
        return

    if args:
        await destination.send(args)
        await ctx.message.add_reaction(emoji='✅')

    attach = ctx.message.attachments
    if attach:
        for i in attach:
            if image_check(i.url):
                await destination.send(embed=discord.Embed(timestamp=ctx.message.created_at).set_image(url=i.url))
            else:
                await destination.send(embed=discord.Embed(timestamp=ctx.message.created_at).add_field(
                    name="Attachment:", value=i.url
                ))
        await ctx.message.add_reaction(emoji='✅')

    if not attach and not args:
        await ctx.message.add_reaction(emoji='❌')


class Admin(commands.Cog):
    """
    A class of bot administrators only commands.

    Attributes:
        stat (list): list string filled with the rich presence text
        bot (commands.Bot): bot reference
        goal (discord.ActivityType): the activity type to display on random rich presence
        webList (list): list string contains the web hook addresses
        randomRP (bool): boolean switch for random rich presence
        timer (int): integer timer in seconds on when the rich presence change for random rich presence
        currently (discord.Status): the current bot display status
        temping (discord.Activity): the current bot rich presence
        online_stat(list): list of the 3 discord status for random rich presence
    """

    def __init__(self, bot):
        """
        The constructor for Admin class.

        Args:
            bot (command.Bot): passing in the bot reference
        """
        self.debug = True
        self.stat = []
        self.bot = bot
        self.goal = discord.ActivityType.playing
        self.webList = []
        self.randomRP = False
        self.timer = 30
        self.currently = discord.Status.online
        self.temping = None
        self.online_stat = [discord.Status.dnd, discord.Status.idle, discord.Status.online]

    @commands.Cog.listener()
    async def on_ready(self):
        """
        A function that automatically calls the update function when bot is ready.

        Returns:
            None
        """
        await self.update()

    async def update(self):
        """
        Async function that refreshed the class' list of rrp and web hooks.

        Returns:
            None
        """
        self.stat = []
        data = self.bot.mongodb["rrp"].find({})
        for i in data:
            self.stat.append(i['title'])
        self.webList = []
        data = self.bot.mongodb["webhooks"].find({})
        for i in data:
            self.webList.append([i['name'], i['link']])

    @tasks.loop(seconds=30)
    async def change_pr(self):
        """
        A function of task loop for random rich presence.

        Returns:
            None
        """
        ac = discord.Activity(name=random.choice(self.stat), type=self.goal)
        self.currently = random.choice(self.online_stat)
        await self.bot.change_presence(status=self.currently, activity=ac)
        self.temping = ac

    @change_pr.after_loop
    async def end(self):
        """
        A function of end of task loop that switch the bot's rich presence and status back to normal.

        Returns:
            None
        """
        self.currently = discord.Status.online
        self.temping = None
        await self.bot.change_presence(status=self.currently, activity=None)

    async def ran(self, ctx: commands.Context):
        """
        A function that either stop or start the bot's rich presence system depending the on randomRP.

        Args:
            ctx (commands.Context): passing in the context for reply

        Returns:
            None
        """
        if self.randomRP:
            self.randomRP = False
            self.change_pr.stop()
            await ctx.send("**Random rich presence is now off.**")
        else:
            self.randomRP = True
            self.change_pr.start()
            await ctx.send("**Random rich presence is now on.**")

    @commands.command()
    @commands.check(Control.has_control)
    async def status(self, ctx: commands.Context):
        """
        A command that summons a menu to modify the bot's current rich presence or status.

        Args:
            ctx (commands.Context): passing in the context for reply

        Returns:
            None
        """
        if self.randomRP:
            await ctx.send("Random Rich Presence is currently running, which will effect bot's static status.")
            return
        arr = ['📗', '💛', '🔴', '👻', '💬', '🔁']
        index = [discord.Status.online, discord.Status.idle, discord.Status.do_not_disturb, discord.Status.invisible]

        def check(reaction1, user1):
            return reaction1.emoji in arr and user1.id == ctx.author.id

        msg = await ctx.send(embed=discord.Embed(
            colour=0xe84393,
            title="Bot Status Change Menu",
            description="📗 - Online\n💛 - Idle\n🔴 - Do Not Disturb\n👻 - Invisible\n💬 - Presence Setting\n"
                        "🔁 - Reset Bot Status and Presence"
        ).set_footer(icon_url=self.bot.user.avatar_url_as(size=64), text="React to change bot status (10s)"))
        for i in arr:
            await msg.add_reaction(emoji=i)

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=check)
            await msg.clear_reactions()

            if reaction.emoji in ['📗', '💛', '🔴', '👻']:
                change = index[arr.index(reaction.emoji)]
                await self.bot.change_presence(status=change, activity=self.temping)
                self.currently = change
                await msg.edit(content=f"""Changed status to {change}!""", embed=None)
                await msg.clear_reactions()
            elif reaction.emoji == '🔁':
                self.currently = discord.Status.online
                self.temping = None
                await self.bot.change_presence(status=self.currently, activity=self.temping)
                await msg.edit(embed=None, content="Bot's status is now **online** and presence is now `none`.")
                await msg.clear_reactions()
            else:
                def mess(m):
                    return m.author.id == ctx.author.id

                arr = ['🎮', '🎵', '👀', '📺']
                other = ['playing', 'listening to', 'watching', 'streaming']
                st = [discord.ActivityType.playing, discord.ActivityType.listening, discord.ActivityType.watching,
                      discord.ActivityType.streaming]
                await msg.edit(embed=discord.Embed(
                    colour=0x2c3e50,
                    title="Bot Status Change Menu",
                    description="🎮 - Playing\n🎵 - Listening to\n👀 - Watching\n📺 - Streaming"
                ).set_footer(icon_url=self.bot.user.avatar_url_as(size=64), text="React to change bot status (10s)"))
                for i in arr:
                    await msg.add_reaction(emoji=i)

                reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=check)
                await msg.edit(embed=None, content="Now enter the status text")
                await msg.clear_reactions()
                text = await self.bot.wait_for('message', timeout=30, check=mess)
                ty = st[arr.index(reaction.emoji)]
                ac = discord.Activity(type=ty, name=text.content)
                await self.bot.change_presence(status=self.currently, activity=ac)
                self.temping = ac
                await msg.edit(content=f"I am now {other[arr.index(reaction.emoji)]} {text.content}!")

        except asyncio.TimeoutError:
            await msg.delete()
            return

    @commands.group()
    @commands.check(Control.has_control)
    async def rrp(self, ctx: commands.Context):
        """
        Main command group for random rich presence, if not additional argument is given, this will toggle random rich
        presence.

        Args:
            ctx (commands.Context): passing in the context for reply

        Returns:
            None
        """
        if ctx.invoked_subcommand is None:
            await self.ran(ctx)

    @rrp.command(aliases=['+'])
    async def add(self, ctx: commands.Context, *, addition: str):
        """
        Sub command of rrp, inserts a new rich presence text into random rich presence system.

        Args:
            ctx (commands.Context): passing in context to reply
            addition (str): the new random rich presence

        Returns:
            None
        """
        if addition in self.stat:
            await ctx.send("That status is already in the database.")
        else:
            self.stat.append(addition)
            self.bot.mongodb["rrp"].insert_one({"title": addition})
            await ctx.message.add_reaction("✔")

    @rrp.command(aliases=['-'])
    async def remove(self, ctx: commands.Context, label: int):
        """
        Sub command of rrp that removes a random rich presence base on the given label.

        Args:
            ctx (commands.Context): passing in the context for reply
            label (int): deletion label

        Returns:
            None
        """
        try:
            hold = self.stat.pop(label - 1)
            self.bot.mongodb["rrp"].delete_one({"title": hold})
            await ctx.message.add_reaction("✔")
        except IndexError:
            await ctx.send(f"`{label}` is not within range.")

    @rrp.command(aliases=['l'])
    async def show(self, ctx: commands.Context):
        """
        Sub command of rrp that lists the random rich presence with the appropriate label.

        Args:
            ctx (commands.Context): passing in the location to send the list

        Returns:
            None
        """
        if len(self.stat) == 0:
            await ctx.send("Random rich presence list is empty.")
        else:
            hold = "```autohotkey\n"
            num = 1
            for i in self.stat:
                hold += f"{num}.\t{i}\n"
                num += 1
            hold += "```"
            await ctx.send(hold)

    @rrp.command(aliases=['s'])
    async def setting(self, ctx: commands.Context):
        """
        Sub group of random rich presence command, opens up the setting menu for random rich presence.

        Args:
            ctx (commands.Context): passing in the context for menu display

        Returns:
            None
        """
        emotes = ['⚙', '⏲']
        msg = await ctx.send(embed=discord.Embed(
            colour=0xe67e22,
            title="Random Rich Presence Setting Menu",
            description="⚙ - Change Status\n⏲ - Change Delay"
        ).set_footer(text="10 second timeout!", icon_url=self.bot.user.avatar_url_as(size=64)))

        def check(reaction1, user1):
            return reaction1.emoji in emotes and user1.id == ctx.author.id

        for i in emotes:
            await msg.add_reaction(emoji=i)

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=check)
            await msg.clear_reactions()

            if reaction.emoji == '⏲':
                def ms(m1):
                    return m1.author.id == ctx.author.id

                await msg.edit(embed=None, content="Enter the desired timer (in integer)")
                try:
                    m = await self.bot.wait_for('message', timeout=10, check=ms)
                    m = int(m.content)
                    if m < 5:
                        await msg.edit(content="Value must be greater than or equal to than 5 seconds.")
                        return
                    self.timer = m
                    self.change_pr.change_interval(seconds=self.timer)
                    await msg.edit(content=f"Timer has been set to **{m}** seconds!")
                except ValueError:
                    await msg.edit(content="Value is not a integer! Action cancelled.")
            else:
                emotes = ['🎮', '🎵', '👀', '📺']
                other = ['playing', 'listening to', 'watching', 'streaming']
                st = [discord.ActivityType.playing, discord.ActivityType.listening, discord.ActivityType.watching,
                      discord.ActivityType.streaming]
                await msg.edit(embed=discord.Embed(
                    colour=0xe67e22,
                    title="Random Rich Presence - Mode Selection",
                    description="🎮 - Playing\n🎵 - Listening to\n👀 - Watching\n📺 - Streaming"
                ).set_footer(text="10 second timeout!", icon_url=self.bot.user.avatar_url_as(size=64)))
                for i in emotes:
                    await msg.add_reaction(emoji=i)
                reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=check)
                index = emotes.index(reaction.emoji)
                self.goal = st[index]
                await msg.edit(embed=None, content=f"Random rich presence type has been set to `{other[index]}`.")
        except asyncio.TimeoutError:
            await msg.delete()
        await msg.clear_reactions()

    @commands.group(aliases=['h'])
    @commands.check(Control.has_control)
    async def hook(self, ctx: commands.Context):
        """
        The main command group for web hooks.

        Args:
            ctx (commands.Context): passing in context

        Returns:
            None
        """
        if not ctx.invoked_subcommand:
            pass

    @hook.command(aliases=['l'])
    async def list(self, ctx: commands.Context):
        """
        Sub command of hook that shows the list of stored web hooks in the system.

        Args:
            ctx (commands.Context): passing in context for reply

        Returns:
            None
        """
        if len(self.webList) == 0:
            await ctx.send("Web hook list is empty")
        else:
            hold = "```autohotkey\n"
            count = 1
            for i in self.webList:
                hold += f"{count}.\t {i[0]}\n> {i[1]}\n\n"
                count += 1
            hold += "```"
            await ctx.send(hold)

    @hook.command(aliases=['+'])
    async def add(self, ctx: commands.Context, name: str, *, link: str):
        """
        Sub command of hook that adds a new web hook.

        Args:
            ctx (commands.Context): passing in the context
            name (str): the name for the web hook
            link (str): the web hook address to store

        Returns:
            None
        """
        temp = [name, link]
        if temp in self.webList:
            await ctx.send("That web hook already exists.")
        else:
            self.webList.append(temp)
            self.bot.mongodb["webhooks"].insert_one({"name": name, "link": link})
            await ctx.message.add_reaction("✔")

    @hook.command(aliases=['-'])
    async def remove(self, ctx: commands.Context, label: int):
        """
        Sub command of hook that removes a web hook from storage base on label.

        Args:
            ctx (commands.Context): passing in the context for reply
            label (int): deletion label

        Returns:
            None
        """
        try:
            hold = self.webList.pop(label - 1)
            self.bot.mongodb["webhooks"].delete_one({"name": hold[0], "link": hold[1]})
            await ctx.message.add_reaction("✔")
        except IndexError:
            await ctx.send(f"`{label}` is not within range.")

    @hook.command(aliases=['t'])
    async def text(self, ctx: commands.Context, target: int, name: str, *, args: str):
        """
        A command part of hook that sends web hook messages(and only messages) base on the stored web hooks.

        Args:
            ctx (commands.Context): passing in the context to scan
            target (int): passing in the webhook label
            name (str): naming the webhook on send
            args (str): the message to send

        Returns:
            None
        """
        if target <= 0:
            await ctx.send("Line number can't be 0 or less.")
            await ctx.message.add_reaction(emoji='❌')
        elif len(self.webList) == 0:
            await ctx.send("Web hook list is empty.")
            await ctx.message.add_reaction(emoji='❌')
        else:
            async with aiohttp.ClientSession() as session:
                webhook = Webhook.from_url(self.webList[target - 1][1], adapter=AsyncWebhookAdapter(session))
                await webhook.send(args, username=name)
                await ctx.message.add_reaction(emoji='✅')

    @hook.command(aliases=['e'])
    async def embed(self, ctx: commands.Context, target: int, name: str, *, args: str):
        """
        Sub command of hook that sends the given message in embed format.

        Args:
            ctx (commands.Context): passing in the context for reply and cans the command call message for attachments
            target (int): the web hook the embed will be sent to
            name (str): name of the web hook on send
            args (str): message to append to embed if any

        Returns:
            None
        """
        if target <= 0:
            await ctx.send("Line number can't be 0 or less.")
            await ctx.message.add_reaction(emoji='❌')
            return
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(self.webList[target - 1][1], adapter=AsyncWebhookAdapter(session))

            attach = ctx.message.attachments

            embed = discord.Embed(description=args, colour=0xffeaa7)

            image = False
            formats = [".png", ".jpg", ".gif", "jpeg"]

            if attach:
                if len(attach) == 1:
                    for i in range(len(formats)):
                        if attach[0].filename.lower().endswith(formats[i]):
                            image = True

                    if not image:
                        await ctx.send("Has to be an image")
                        await ctx.message.add_reaction(emoji='❌')
                        return

            if image:
                embed.set_image(url=attach[0].url)

            await webhook.send(embed=embed, username=name)
            await ctx.message.add_reaction(emoji='✅')

    @commands.command(aliases=["say"])
    @commands.check(Control.has_control)
    async def echo(self, ctx: commands.Context, *, args: str):
        """
        A command that makes the bot repeat what caller said.

        Args:
            ctx (commands.Context): pass in context for echo reply
            args (str): the message for the bot to repeat

        Returns:
            None
        """
        await ctx.send(args)

    @commands.command()
    @commands.check(Control.has_control)
    async def sm(self, ctx: commands.Context,
                 target: typing.Union[discord.User, discord.Member, discord.TextChannel, int], *, args: str = None):
        """
        A commands that sends a message to the desired text or private channel.

        Args:
            ctx (commands.Context): pass in context for reply and scan message for attachments
            target (typing.Union[discord.User, discord.Member, discord.TextChannel, int]: message destination
            args (str): the message to send

        Returns:
            None
        """
        if isinstance(target, discord.User) or isinstance(target, discord.User) or isinstance(target,
                                                                                              discord.TextChannel):
            destination = target
        else:
            destination = self.bot.get_channel(target)
            if not destination:
                destination = self.bot.get_user(target)
        if destination:
            await send(ctx, args, destination)
        else:
            await ctx.send("Can not locate the destination.")

    @sm.error
    async def sm_error(self, ctx: commands.Context, error: commands.errors):
        """
        A function that will be called on sm command error, and take appropriate action.

        Args:
            ctx (commands.Context): passing in context for analyze and reply
            error (commands.errors): the error sm command received

        Returns:
            None
        """
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.message.add_reaction(emoji='❌')
            await ctx.send("The correct command usage is `sm <user mention or channel mention or id> <messages>`",
                           delete_after=20)
            return

        raise error

    @commands.command(aliases=["dump"])
    @commands.check(Control.has_control)
    async def spam(self, ctx: commands.Context, amount: int, *, args: str):
        """
        A command that sends multiple desired messages of desire amount in the same channel.

        Args:
            ctx (commands.Context): passing in context to send message and to reply
            amount (int): amount of times to send the message
            args (str): the message to "spam"

        Returns:
            None
        """
        for i in range(0, amount):
            await ctx.send(args)
            await asyncio.sleep(2.5)
        await ctx.send(f"""**Done dumping {amount} messages.**""", delete_after=5)

    @commands.command()
    @commands.check(Control.has_control)
    async def debug(self, ctx: commands.Context):
        """
        A command that turns on or off debug mode depending on the debug mode switch.

        Args:
            ctx (commands.Context): passing in context for reply

        Returns:
            None
        """

        if self.debug:
            self.debug = False
            reply = "off"
        else:
            self.debug = True
            reply = "on"
        await ctx.send(f"Turned {reply} debug mode.")

    # TODO add SQL clean up command near the end


def setup(bot: commands.Bot):
    """
    Necessary function for a cog that initialize the Admin class.

    Args:
        bot (commands.Bot): passing in bot for class initialization

    Returns:
        None
    """
    bot.add_cog(Admin(bot))
    print("Loaded Cog: Admin")


def teardown(bot: commands.Bot):
    """
    Function to be called upon Cog unload, in this case, it will print message in CMD.

    Args:
        bot (commands.Bot): passing in bot reference for unload.

    Returns:
        None
    """
    bot.remove_cog("Admin")
    print("Unloaded Cog: Admin")
