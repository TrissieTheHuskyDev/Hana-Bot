import discord
from discord.ext import commands

import time
import typing
import datetime
import asyncio
from CustomTools import ignore_check as ic
from CustomTools import BotCommanders as Details


def verification(ver: discord.VerificationLevel):
    """
    Function that converts Verification Level type to string.

    Args:
        ver(discord.VerificationLevel): discord server verification level to convert

    Returns:
        None
    """
    if ver is discord.VerificationLevel.none:
        return "Free crossing 🚶"
    elif ver is discord.VerificationLevel.low:
        return "visa? 📧"
    elif ver is discord.VerificationLevel.medium:
        return "5 minutes and older only ⌛"
    elif ver is discord.VerificationLevel.high:
        return "Wait 10 minute, have some tea ⏲💬"
    else:
        return "Can I have your number? 📱"


class Normal(commands.Cog):
    """
    Class of Normal commands for Hana bot.

    Attributes:
        bot(commands.Bot): bot reference
    """
    def __init__(self, bot: commands.Bot):
        """
        Constructor for Normal class.

        Args:
            bot(commands.Bot): pass in bot reference
        """
        self.bot = bot

    async def update(self):
        """
        Async method of Normal class that is required for hana bot function. [Not native to discord.py]

        Returns:
            None
        """
        pass

    # get bot connection command
    @commands.command(aliases=["ping"])
    async def connection(self, ctx: commands.Context):
        """
        Command for Normal class that will return the estimated bot ping.

        Args:
            ctx(commands.Context): pass in context for analysis and reply

        Returns:
            None
        """
        if ic(self, ctx.channel):
            return

        # Reference: https://stackoverflow.com/questions/46307035/ping-command-with-discord-py
        before = time.monotonic()
        message = await ctx.send(":ping_pong:")
        ping = int(round((time.monotonic() - before) * 1000))
        web = int(round(self.bot.latency * 1000))
        average = int(round((ping + web) / 2))

        # default bad ping color
        c = 0xe74c3c

        if average <= 200:
            # medium ping
            c = 0xf1c40f
        if average <= 90:
            # fast ping
            c = 0x2ecc71

        embed = discord.Embed(
            title="Bot's Current Latency:",
            timestamp=ctx.message.created_at,
            colour=c)
        embed.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url_as(size=64))
        embed.add_field(name="Discord Ping:", value=f"{web} ms")
        embed.add_field(name="Estimated Ping: ", value=f"{ping} ms")

        await message.edit(content="", embed=embed)

    # get avatar command
    @commands.command(aliases=["pfp"])
    async def avatar(self, ctx: commands.Context, target: discord.Member = None):
        """
        Command for Normal class that will attempt to return embed of target's avatar, if not then author's.

        Args:
            ctx(commands.Context): pass in context for reply
            target(discord.Member): the target

        Returns:
            None
        """
        if ic(self, ctx.channel):
            return

        person = ctx.author if not target else target

        datLink = person.avatar_url
        embed = discord.Embed(
            timestamp=ctx.message.created_at,
            title=f"{person.name}'s Avatar:",
            colour=person.color,
            url=f"{datLink}"
        )
        embed.set_image(url=f"{datLink}")

        await ctx.send(embed=embed)

    @commands.command(aliases=['utc'])
    async def UTC(self, ctx: commands.Context):
        """
        Command for Nomral class that returns the current time in UTC.

        Args:
            ctx(commands.Context): pass in context for reply

        Returns:
            None
        """
        if ic(self, ctx.channel):
            return
        await ctx.send(datetime.datetime.utcnow().strftime("UTC Time:\n`%B %#d, %Y`\n%I:%M %p"))

    # get user info
    @commands.command(aliases=["userinfo", "uinfo"])
    async def user_info(self, ctx: commands.Context, member: typing.Union[discord.Member, discord.User, int, None]):
        """
        Command for Normal that will return the target information.

        Args:
            ctx(commands.Context): pass in context for reply
            member(typing.Union[discord.Member, discord.User, int, None]): variable for analysis

        Returns:
            None
        """
        if ic(self, ctx.channel):
            return

        admin = Details.has_control(ctx)

        if isinstance(member, int) and admin:
            member = await self.bot.fetch_user(member)

        if isinstance(member, discord.User) and admin:
            # reference video: https://youtu.be/vV2B5cxj9kw
            embed = discord.Embed(
                colour=0x81ecec,
                timestamp=ctx.message.created_at
            )

            embed.set_author(name=f"Found User!")
            embed.set_thumbnail(url=str(member.avatar_url_as(size=256)))
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url_as(size=64))

            embed.add_field(name="Name:", value=member.name, inline=False)
            embed.add_field(name="Mention:", value=member.mention, inline=False)
            embed.add_field(name="ID:", value=member.id, inline=False)
            embed.add_field(name="Joined discord on:", value=member.created_at.strftime("%#d %B %Y, %I:%M %p UTC"),
                            inline=False)

            if member.bot:
                embed.set_author(name=f"Found a Bot!")
        else:
            # reference video: https://youtu.be/vV2B5cxj9kw
            member = ctx.author if not member or \
                                   (isinstance(member, int) or isinstance(member, discord.User)) else member
            roles = [role for role in member.roles]

            embed = discord.Embed(
                colour=member.color,
                timestamp=ctx.message.created_at
            )

            embed.set_thumbnail(url=member.avatar_url_as(size=256))
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url_as(size=64))

            embed.add_field(name="Mention", value=member.mention)
            embed.add_field(name="ID:", value=member.id)
            embed.add_field(name="Username", value=member)
            embed.add_field(name="Server Nickname:", value=member.display_name)

            embed.add_field(name="Joined discord on:", value=member.created_at.strftime("%#d %B %Y, %I:%M %p UTC"),
                            inline=False)
            embed.add_field(name="Joined server on:", value=member.joined_at.strftime("%#d %B %Y, %I:%M %p UTC"),
                            inline=False)

            embed.add_field(name=f"Roles ({len(roles)})", value=" ".join([role.mention for role in roles]),
                            inline=False)
            embed.add_field(name="Status", value=member.status)
            embed.add_field(name="Is on Mobile", value=member.is_on_mobile())
            if member.bot:
                embed.set_field_at(index=0, name="Bot", value=f"{member.mention}")

        await ctx.send(embed=embed)

    @commands.command(aliases=["sBanner", "sbanner", "banner"])
    @commands.guild_only()
    async def server_banner(self, ctx: commands.Context):
        """
        Command for Normal class that returns the server banner if used in a server.

        Args:
            ctx(commands.Context): pass in context for analysis and reply

        Returns:
            None
        """
        if ic(self, ctx.channel):
            return

        if ctx.guild.banner is None:
            await ctx.send("This server don't have a banner 😢")
        else:
            await ctx.send(embed=discord.Embed(
                colour=0xecf0f1,
                timestamp=ctx.message.created_at,
                title=f"Server Banner for {ctx.guild}"
            ).set_image(url=ctx.guild.banner_url_as(size=2048, format='png'))
                           .set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url_as(size=64)))

    @commands.command(aliases=['sicon', 'spfp'])
    @commands.guild_only()
    async def server_icon(self, ctx: commands.Context):
        """
        Command for Normal class that returns the server icon if used in a server.

        Args:
            ctx(commands.Context): pass in context for analysis and reply

        Returns:
            None
        """
        if ic(self, ctx.channel):
            return

        await ctx.send(embed=discord.Embed(
            colour=0xecf0f1,
            title=f"Server Icon for {ctx.guild}",
            timestamp=ctx.message.created_at
        ).set_image(url=ctx.guild.icon_url_as(static_format="png", size=1024))
                       .set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url_as(size=64)))

    @commands.command(aliases=['splash', 'sSplash'])
    @commands.guild_only()
    async def server_splash(self, ctx: commands.Context):
        """
        Command for Normal class that returns the server splash screen if used in a server.

        Args:
            ctx(commands.Context): pass in context for analysis and reply

        Returns:
            None
        """
        if ic(self, ctx.channel):
            return

        if ctx.guild.splash is None:
            await ctx.send("This server don't have a invite splash screen 😢")
        else:
            await ctx.send(embed=discord.Embed(
                timestamp=ctx.message.created_at,
                colour=0xecf0f1,
                title=f"Invite Splash Screen for {ctx.guild}"
            ).set_image(url=ctx.guild.splash_url_as(size=2048, format='png'))
                    .set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url_as(size=64)))

    @commands.command(aliases=["sinfo"])
    @commands.guild_only()
    async def server_info(self, ctx: commands.Context):
        """
        Command for Normal class that returns the server information if used in a server.

        Args:
            ctx(commands.Context): pass in context for analysis and reply

        Returns:
            None
        """
        if ic(self, ctx.channel):
            return

        server = ctx.guild
        temp = server.premium_tier

        c = 0x535c68
        if temp == 1:
            c = 0xff9ff3
        elif temp == 2:
            c = 0xf368e0
        elif temp == 3:
            c = 0xbe2edd

        normal = 0
        animated = 0
        emotes = await server.fetch_emojis()
        for i in emotes:
            if i.animated:
                animated += 1
            else:
                normal += 1

        embed = discord.Embed(
            timestamp=ctx.message.created_at,
            colour=c,
            title="𝕊𝕖𝕣𝕧𝕖𝕣 𝕀𝕟𝕗𝕠" if not server.large else "🅱🅸🅶 🆂🅴🆁🆅🅴🆁 🅸🅽🅵🅾"
        )
        embed.add_field(name="Server Name (ID)", value=f"{server.name} ({server.id})")
        embed.set_thumbnail(url=f"{server.icon_url_as(static_format='png', size=256)}")
        embed.add_field(name="Owner", value=server.get_member(server.owner_id).mention, inline=False)
        embed.add_field(name="Member Count", value=str(len(server.members)))
        embed.add_field(name="Booster Count", value=server.premium_subscription_count)
        embed.add_field(name="Region", value=server.region)
        embed.add_field(name="Filter", value=server.explicit_content_filter)
        embed.add_field(name="Security Level",
                        value=f"{verification(server.verification_level)}" + ("and need 2FA" if server.mfa_level == 1
                                                                              else ""),
                        inline=False)
        embed.add_field(name="Upload Limit", value=f"{server.filesize_limit / 1048576} MB")
        embed.add_field(name="Bitrate Limit", value=f"{server.bitrate_limit / 1000} kbps")
        embed.add_field(name="Emote Slots", value=f"{normal} / {server.emoji_limit}")
        embed.add_field(name="Animated Emote Slots", value=f"{animated} / {server.emoji_limit}")
        embed.add_field(name="Server Birthday",
                        value=server.created_at.strftime("%#d %B %Y, %I:%M %p UTC"), inline=False)

        if server.banner is not None:
            embed.set_image(url=server.banner_url_as(format='png', size=2048))

        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url_as(size=64))

        await ctx.send(embed=embed)

    @commands.command(aliases=['ei'])
    async def emote_info(self, ctx: commands.Context):
        """
        Command for Normal class that will attempt to analyze requested emote to return either it's ID or UTF-8 form.

        Args:
            ctx(commands.Context): pass in  context for reply

        Returns:
            None
        """
        if ic(self, ctx.channel):
            return

        message = await ctx.send("React to this message")

        def check(reaction1, user1):
            return reaction1.message.id == message.id and user1.id == ctx.author.id

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=check)
        except asyncio.TimeoutError:
            await message.edit(content="Timed out")
        else:
            if isinstance(reaction.emoji, str):
                temp = reaction.emoji
            else:
                temp = reaction.emoji.id
            await message.edit(content=f"```{temp}```")

    @commands.command(aliases=['lem'])
    @commands.guild_only()
    async def list_emotes(self, ctx: commands.Context):
        """
        Command for Normal class that list the emotes within the server in embed.

        Args:
            ctx(commands.Context): pass in Context for analysis and reply

        Returns:
            None
        """
        if ic(self, ctx.channel):
            return
        emotes = ctx.guild.emojis
        if len(emotes) <= 0:
            await ctx.send("This server don't have any emotes.")
            return
        normal = []
        animated = []
        for i in emotes:
            if i.animated:
                animated.append(i)
            else:
                normal.append(i)
        temp = ""
        embed = discord.Embed(
            colour=0x1abc9c,
            timestamp=ctx.message.created_at
        ).set_author(icon_url=ctx.guild.icon_url, name=f"{ctx.guild.name} | Emote List")
        count = 1
        for i in normal:
            temp += f"{i} "
            if len(temp) >= 950:
                embed.add_field(name=f"Normal Emotes {count}", value=temp + " ")
                temp = ""
                count += 1
        embed.add_field(name=f"Normal Emotes {count}", value=temp + " ")
        count = 1
        temp = ""
        if len(animated) > 0:
            for i in animated:
                temp += f"{i} "
                if len(temp) >= 950:
                    embed.add_field(name=f"Animated Emotes {count}", value=temp + " ")
                    temp = ""
                    count += 1
            embed.add_field(name=f"Animated Emotes {count}", value=temp + " ")
        await ctx.send(embed=embed)

    @commands.command(aliases=["binfo"])
    async def botinfo(self, ctx: commands.Context):
        """
        Command for Normal class that replies with Hana bot information.

        Args:
            ctx(commands.Context): pass in Context for reply

        Returns:
            None
        """
        if ic(self, ctx.channel):
            return

        embed = discord.Embed(
            colour=0x48dbfb,
            title="I am a discord bot filled with random features! I am made using Python and implements "
                  "MongoDB! Try out some command and you might like what I can do!"
        )
        embed.set_author(name=f"Hi! I am {self.bot.user.name}!",
                         icon_url="http://icons.iconarchive.com/icons/cornmanthe3rd/plex/128/Other-python-icon.png")
        embed.set_thumbnail(url=self.bot.user.avatar_url_as(size=256))
        creator = await self.bot.fetch_user(267909205225242624)
        embed.add_field(name="Bot Master", value=self.bot.appinfo.owner.mention)
        details = Details.workers
        if len(details) > 0:
            embed.add_field(name="Bot Staffs", value="\n".join(f"> {i.mention}" for i in details), inline=False)
        embed.add_field(name="Creator / Developer",
                        value=f"{creator.mention} / [Necomi#1555](https://github.com/Necom1/Hana-Bot)", inline=False)
        embed.add_field(name="I am born on", value=self.bot.user.created_at.strftime("%#d %B %Y, %I:%M %p UTC"))
        embed.add_field(name="Support Server", value="[Flower Field](http://discord.gg/sWYPsU7)")

        embed.set_footer(text="v 0.9 | Beta", icon_url="https://i.imgur.com/RPrw70n.jpg")

        await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    """
    Necessary function for a cog that initialize the Normal class.

    Args:
        bot (commands.Bot): passing in bot for class initialization

    Returns:
        None
    """
    bot.add_cog(Normal(bot))
    print("Loaded Cog: Normal")


def teardown(bot: commands.Bot):
    """
    Function to be called upon Cog unload, in this case, it will print message in CMD.

    Args:
        bot (commands.Bot): passing in bot reference for unload.

    Returns:
        None
    """
    bot.remove_cog("Normal")
    print("Unloaded Cog: Normal")
