import discord
from discord.ext import commands

import typing
import asyncio
import CustomTools
from CustomTools import ignore_check as ic
from CustomTools import prefix

# References:
# https://www.youtube.com/playlist?list=PLW3GfRiBCHOiEkjvQj0uaUB1Q-RckYnj9
# https://www.youtube.com/playlist?list=PLpbRB6ke-VkvP1W2d_nLa1Ott3KrDx2aN

# Resources:
# https://flatuicolors.com/
# https://discordpy.readthedocs.io/


class Moderation(commands.Cog):
    """
    A class of moderator commands.

    Attributes:
        bot(commands.Bot): bot reference
        role(list): list of server whom used the role all or un-role all command within an hour
        instance(list):: list of server who is currently using the download emote command
        cooling(list): list of server whom used the download emote command within an hour
        warn_db: mongoDB reference on warns collection
    """
    def __init__(self, bot: commands.Bot):
        """
        Constructor for Moderation class.

        Args:
            bot(commands.Bot): pass in bot reference
        """
        self.bot = bot
        self.role = []
        self.instance = []
        self.cooling = []
        self.warn_db = bot.mongodb["warns"]

    async def update(self):
        """
        Required method for Moderation class for hana bot to function [not native to discord.py].

        Returns:
            None
        """
        pass

    # check if user have the permission, if so, prune
    @commands.command(aliases=["prune"])
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, amount: int, target: typing.Union[discord.Member, str] = None,
                    word: str = None):
        """
        Async method of Moderation class. This command will require manage messages permission for clearing messages.

        Args:
            ctx(commands.Context): pass in context for execution and reply
            amount(int): amount of messages to scan for and delete
            target(typing.Union[discord.Member, str]): pass in mention or string command for specific message prune
            word(str): if request for "have/contains" prune mode, the word to scan the messages for

        Returns:
            None
        """
        # reference: https://github.com/AlexFlipnote/discord_bot.py/blob/master/cogs/mod.py
        special = " "
        if target is None:
            check = None
        elif isinstance(target, discord.Member):
            def check(m):
                return m.author == target
            special = f" **from {target}** "
        else:
            target = target.lower()
            if target not in ['embed', 'mention', 'attachments', 'attach', 'attachment', 'mentions', 'embeds',
                              'contain', 'contains', 'have', 'image', 'images', 'video', 'media']:
                await ctx.send("Unknown operation, please check your input")
                return

            if target in ['embed', 'embeds']:
                def check(m):
                    return len(m.embeds) > 0
                special = ' **with embeds** '
            elif target in ['attachments', 'attach', 'attachment']:
                def check(m):
                    return len(m.attachments) > 0
                special = ' **with attachments** '
            elif target in ['mention', 'mentions']:
                def check(m):
                    return (len(m.mentions) > 0) or (len(m.role_mentions) > 0)
                special = ' **with mentions** '
            elif target in ['contain', 'contains', 'have']:
                if not word:
                    await ctx.send("Please remember to input words to scan for after the operation")
                    return
                else:
                    def check(m):
                        return word.lower() in m.content.lower()
                    special = f" containing `{word.lower()}` "
            elif target in ['image', 'images']:
                def check(m):
                    if m.attachments:
                        for i in m.attachments:
                            if i.url.lower.endswith(('.jpg', '.png', '.jpeg', '.gif', '.webp', '.bmp', '.tiff')):
                                return True
                    elif m.embeds:
                        for i in m.embeds:
                            if i.image or i.thumbnail:
                                return True
                special = " **with images** "
            elif target in ['video', 'media']:
                def check(m):
                    if m.attachments:
                        for i in m.attachments:
                            if i.url.endswith(('.mp4', '.mov', '.avi', '.mkv', 'webm')):
                                return True
                    elif m.embeds:
                        for i in m.embeds:
                            if i.video:
                                return True
                special = " **with videos** "
            else:
                print(f"Error around Line 91 -> {ctx.content}")
                check = None
                # should never reach this point but ait
            # Possible more future prune checks

        await ctx.message.delete()
        deleted = len(await ctx.channel.purge(limit=amount, check=check))
        embed = discord.Embed(
            title="Purged! 🗑", colour=0xff6b6b,
            description=f"{deleted} messages{special}have been deleted from **{ctx.channel}**.",
            timestamp=ctx.message.created_at
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url_as(size=64))
        await ctx.send(embed=embed, delete_after=8)

    # if an error occurs when using clear command
    @clear.error
    async def clear_error(self, ctx: commands.Context, error):
        """
        Async method of Moderation with relation to clear command, with purpose of handling errors throw on clear
        command execution.

        Args:
            ctx(commands.Context): pass in context for process and reply
            error: the error thrown on clear command usage

        Returns:
            None
        """
        nope = ic(self, ctx.channel)
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please specify the amount to delete.", delete_after=10)
            return
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Please enter a whole number!!", delete_after=10)
            return
        elif isinstance(error, commands.MissingPermissions):
            if nope or ctx.channel.type == discord.ChannelType.private:
                return
            embed = discord.Embed(
                title="👮 No Permission", colour=0x34ace0,
                description='You will need the permission of [Manage Messages] to use this command.'
            )
            embed.set_footer(text=f"Input by {ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed, delete_after=7)
            return
        elif isinstance(error, commands.CommandInvokeError):
            if nope:
                return
            embed = discord.Embed(
                title="😔 Not Enough Permission", colour=0xf9ca24,
                description="I don't have the permission required to perform prune. To do this, I will need: "
                            "[Manage Messages] permission."
            )
            embed.set_footer(text=f"Input by {ctx.author}", icon_url=ctx.author.avatar_url_as(size=64))
            await ctx.send(embed=embed, delete_after=10)
            return

        raise error

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, args: str):
        """
        Command that requires kick member permission to use, and kicks the targeted user if possible with specified
        reason.

        Args:
            ctx(commands.Context): pass in context for process and reply
            member(discord.Member): the member to kick
            args(str): Kick reason

        Returns:
            None
        """
        reason = f"""{ctx.author}[{ctx.author.id}]: "{args}" """
        await member.kick(reason=reason)
        await ctx.message.add_reaction(emoji='✅')

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, target: typing.Union[discord.Member, int, discord.User], *, args: str):
        """
        Command that requires ban member permission to use, and bans the targeted user if possible with specified
        reason.

        Args:
            ctx(commands.Context): pass in context for analysis and reply
            target(typing.Union[discord.Member, int, discord.User]): the target user to ban, can be user ID
            args(str): ban reason

        Returns:
            None
        """
        if len(args) == 0:
            temp = "No Reason"
        else:
            temp = args
        reason = f"""{ctx.author}[{ctx.author.id}]: "{temp}" """
        if isinstance(target, discord.Member):
            await target.ban(reason=reason)
            await ctx.message.add_reaction(emoji='✅')
            return
        elif isinstance(target, int):
            target = await self.bot.fetch_user(target)
        await ctx.message.guild.ban(user=target, reason=reason)
        await ctx.message.add_reaction(emoji='✅')

    @commands.command(aliases=["mBan", "massBan", 'mban', 'massban'])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def mass_ban(self, ctx: commands.Context, reason: str,
                       *targets: typing.Union[int, discord.Member, discord.User]):
        """
        Command that requires ban member permission to use, this will ban all user listed from the server.

        Args:
            ctx(commands.Context): pass in context for analysis and reply
            reason(str): all the ban reasoning capitulated in ""
            *targets(typing.Union[int, discord.Member, discord.User]): all the user to ban after the "reasoning"

        Returns:
            None
        """
        if len(reason) == 0:
            reason = "No Reason"
        reason = f"""{ctx.author}[{ctx.author.id}]: "{reason}" """
        for i in targets:
            if isinstance(i, int):
                member = await self.bot.fetch_user(i)
                await ctx.message.guild.ban(user=member, reason=reason)
            elif isinstance(i, discord.Member):
                await i.ban(reason=reason)
            else:
                await ctx.message.guild.ban(user=i, reason=reason)
        await ctx.message.add_reaction(emoji='✅')

    # TODO MissingPermissions ban error message
    # TODO BadArgument ban error message - Member not found

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, target: typing.Union[int, discord.User], *, args: str):
        """
        Unban command that unbans the targeted user from the server.

        Args:
            ctx(commands.Context): pass in context for analysis and reply
            target(typing.Union[int, discord.User]): target to unban from the server
            args(str): reason for unban

        Returns:
            None
        """
        # https://stackoverflow.com/questions/55742719/is-there-a-way-i-can-unban-using-my-discord-py-rewrite-bot
        if len(args) == 0:
            temp = "No Reason"
        else:
            temp = args
        reason = f"{temp}\n |=> {ctx.author}[{ctx.author.id}]"
        if isinstance(target, int):
            member = await self.bot.fetch_user(target)
        else:
            member = target
        await ctx.message.guild.unban(user=member, reason=reason)
        await ctx.message.add_reaction(emoji='✅')

    @commands.command(aliases=['ra'])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def role_all(self, ctx: commands.Context, *gives: discord.Role):
        """
        Command for Moderation class that add specified roles to all member of the server.

        Args:
            ctx(commands.Context): pass in context for process and reply
            *gives(discord.Roles): the roles to add to all your server members

        Returns:
            None
        """
        if ctx.guild.id in self.role:
            await ctx.send("Command on cooldown(1hr), please try again later.")
            return
        self.role.append(ctx.guild.id)
        people = ctx.guild.members
        size = len(people)

        message = await ctx.send("Processing")

        count = 0
        for i in people:
            temp = False
            for k in gives:
                if k not in i.roles:
                    temp = True
                    break
            if temp:
                count += 1
                try:
                    await i.add_roles(*gives, reason=f"Add roles to all request by {ctx.author.name}")
                except discord.HTTPException:
                    await ctx.send(f"Failed to add roles to **{i}** (ID: {i.id})")

                if count % 10 == 0:
                    await message.edit(content=f"Progress: {count}/{size} added")

        await message.edit(content="Roles given to all server members")
        await asyncio.sleep(3600)
        self.role.remove(ctx.guild.id)

    @commands.command(aliases=['ua'])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def unrole_all(self, ctx: commands.Context, *removes: discord.Role):
        """
        Command for Moderation class that remove specified roles from all member of the server.

        Args:
            ctx(commands.Context): pass in context for process and reply
            *removes(discord.Roles): the roles to add to all your server members

        Returns:
            None
        """
        if ctx.guild.id in self.role:
            await ctx.send("Command on cooldown(1hr), please try again later.")
            return
        self.role.append(ctx.guild.id)
        people = ctx.guild.members
        size = len(people)

        message = await ctx.send("Processing")

        count = 0

        for i in people:
            temp = False
            for k in removes:
                if k in i.roles:
                    temp = True
                    break
            if temp:
                try:
                    await i.remove_roles(*removes, reason=f"Remove roles to all request by {ctx.author.name}")
                except discord.HTTPException:
                    await ctx.send(f"Failed to remove roles from **{i.name}** (ID: {i.id})")

                if count % 10 == 0:
                    await message.edit(content=f"Progress: {count}/{size} removed")

        await message.edit(content="Roles removed from all server members")
        await asyncio.sleep(3600)
        self.role.remove(ctx.guild.id)

    @commands.command(aliases=['de'])
    @commands.guild_only()
    @commands.has_permissions(manage_emojis=True)
    async def download_emote(self, ctx: commands.Context):
        """
        Command for Moderation class that downloads and zip server emote and reply it back to the requester.

        Args:
            ctx(commands.Context): pass in context for process and reply

        Returns:
            None
        """
        if ctx.guild.id in self.instance:
            await ctx.send("This command is already running...")
            return
        if ctx.guild.id in self.cooling:
            await ctx.send("This command is on cooldown(1hr), please try again later.")
            return
        emotes = ctx.guild.emojis
        if len(emotes) <= 0:
            await ctx.send("There is no emotes in this server")
            return
        self.instance.append(ctx.guild.id)
        # references:
        # https://stackabuse.com/creating-and-deleting-directories-with-python/
        # https://stackoverflow.com/questions/6996603/delete-a-file-or-folder
        import requests
        import os
        import zipfile
        import shutil

        try:
            os.makedirs(f"tmp/{ctx.guild.id}/animated")
            os.makedirs(f"tmp/{ctx.guild.id}/normal")
        except OSError:
            await ctx.send("Error happened on line 298 of **Moderation.py**, please report this to Necomi")
            return

        message = await ctx.send("Downloading emotes right now, going to take a while.")

        size = len(emotes)

        for i in emotes:
            r = requests.get(str(i.url), allow_redirects=True)
            if i.animated:
                path = f"tmp/{ctx.guild.id}/animated/{i.name}.gif"
            else:
                path = f"tmp/{ctx.guild.id}/normal/{i.name}.png"
            open(path, 'wb').write(r.content)

        await message.edit(content=f"{size} emotes all successfully downloaded. Zipping")

        name = f"tmp/{ctx.guild.id} - Emotes.zip"

        zipf = zipfile.ZipFile(name, 'w', zipfile.ZIP_DEFLATED)

        for root, dires, files in os.walk(f"tmp/{ctx.guild.id}/"):
            for file in files:
                zipf.write(os.path.join(root, file))

        zipf.close()
        shutil.rmtree(f"tmp/{ctx.guild.id}/")
        await message.edit(content="File zipped, uploading...")
        await ctx.send(content=f"All the emotes for {ctx.guild.name}", file=discord.File(name))
        await message.delete()
        os.remove(name)
        self.instance.remove(ctx.guild.id)
        self.cooling.append(ctx.guild.id)
        await asyncio.sleep(3600)
        self.cooling.remove(ctx.guild.id)

    @commands.command(aliases=['w'])
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def warn(self, ctx: commands.Context, target: discord.Member, *, reason: str):
        """
        Part of the Moderation command that warns the targeted member with the specified reason and append it to
        database.

        Args:
            ctx(commands.Context): pass in context for reply
            target(discord.Member): member to warn
            reason(str): warn reasoning

        Returns:
            None
        """
        if target.bot:
            await ctx.send("Warn a bot? Why?")
            return
        if len(reason) <= 0:
            await ctx.send("Please specify a reason.")
            return
        if ctx.author.id == target.id:
            await ctx.send("LOL, why?")
            return

        data = CustomTools.add_warn(self.bot, ctx.message.created_at, ctx.guild.id, target.id, ctx.author.id, 0, reason)

        try:
            await target.send("⚠ You received a warning ⚠", embed=discord.Embed(
                timestamp=ctx.message.created_at,
                description=reason,
                colour=0xd63031
            ).set_footer(icon_url=target.avatar_url, text=f"{data} offenses")
                              .set_author(icon_url=ctx.guild.icon_url, name=f"{ctx.guild.name}"))
            await ctx.message.add_reaction(emoji='👍')
        except discord.HTTPException:
            await ctx.send("Warning stored in system, however, can not warn the target via DM.")

    @commands.guild_only()
    @commands.group(aliases=['wm'])
    @commands.has_permissions(ban_members=True)
    async def warn_menu(self, ctx: commands.Context):
        """
        Command of Moderation class, part of a group command. Will bring up warn menu help if no additional param.
        specified.

        Args:
            ctx(commands.Context): pass in context for reply

        Returns:
            None
        """
        if not ctx.invoked_subcommand:
            embed = discord.Embed(title="`Warn Menu` Commands", colour=0x9b59b6)
            embed.add_field(inline=False, name=f"{prefix(self, ctx)}wm <mode> <User ID/Mention> (warning ID )",
                            value="Mode 'show' will list amount of warning the user have\nMode 'purge' will delete all"
                                  " the warnings the user have\nMode 'remove' will remove the specified warnings "
                                  "the user have by warn ID")
            await ctx.send(embed=embed)

    @warn_menu.command(aliases=['s'])
    async def show(self, ctx: commands.Context, target: typing.Union[discord.Member, discord.User, int]):
        """
        Command of Moderation class and sub-command of warn_menu. This will list the amount of warnings the user
        have received in the guild.

        Args:
            ctx(commands.Context): pass in context for analysis and reply
            target(typing.Union[discord.Member, discord.User, int]): the user to fetch warnings for

        Returns:
            None
        """
        if isinstance(target, int):
            target = target
        else:
            target = target.id

        data = self.warn_db.find_one({"guild_id": ctx.guild.id, "user_id": target})
        user = ctx.guild.get_member(target)
        if not data:
            await ctx.send(f"**{user}** have a clean record")
        else:
            embed = discord.Embed(
                colour=user.colour,
                timestamp=ctx.message.created_at
            ).set_author(icon_url=user.avatar_url, name=f"{user} Warn List")
            line1 = ""
            line2 = ""
            line3 = ""
            for i in range(len(data["warn_id"])):
                if data["kind"][i] == 0:
                    line1 += f"**{data['warn_id'][i]}**. [`{data['time'][i]}`] |<@!{data['warner'][i]}>| - " \
                             f"{data['reason'][i]}\n"
                if data["kind"][i] == 1:
                    line2 += f"**{data['warn_id'][i]}**. [`{data['time'][i]}`] - {data['reason'][i]}\n"
                if data["kind"][i] == 2:
                    line3 += f"**{data['warn_id'][i]}**. [`{data['time'][i]}`] ({data['addition'][i]} mute) -  " \
                             f"{data['reason'][i]}\n"

            if len(line1) > 0:
                result = CustomTools.split_string(line1, 1000)
                for i in range(len(result)):
                    embed.add_field(inline=False, name=f"Manual Warns {i+1}", value=result[i])
            if len(line2) > 0:
                result = CustomTools.split_string(line2, 1000)
                for i in range(len(result)):
                    embed.add_field(inline=False, name=f"Auto Warns {i+1}", value=result[i])
            if len(line3) > 0:
                result = CustomTools.split_string(line3, 1000)
                for i in range(len(result)):
                    embed.add_field(inline=False, name=f"Mutes {i+1}", value=result[i])
            await ctx.send(embed=embed)

    @warn_menu.command()
    async def purge(self, ctx, target: typing.Union[discord.Member, discord.User, int]):
        """
        Command of Moderation class and sub-command of warn_menu that removes all the warnings a user have.

        Args:
            ctx(commands.Context): pass in context for process and reply
            target(typing.Union[discord.Member, discord.User, int]): the target to purge warning for

        Returns:
            None
        """
        if isinstance(target, int):
            target = target
        else:
            target = target.id

        self.warn_db.delete_many({"guild_id": ctx.guild.id, "user_id": target})
        await ctx.send(f"Purged warn data of user with ID:`{target}`")

    @warn_menu.command(aliases=['-'])
    async def remove(self, ctx: commands.Context, target: typing.Union[discord.Member, discord.User, int], what: int):
        """
        Command of Moderation class and sub-command of warn_menu. Removes a single specified warning from user
        warning list.

        Args:
            ctx(commands.Context): pass in context for process and reply
            target(typing.Union[discord.Member, discord.User, int]): the target to remove warnings from
            what(int): the warn ID of the target warning to remove

        Returns:
            None
        """
        if isinstance(target, int):
            target = target
        else:
            target = target.id

        data = self.warn_db.find_one({"guild_id": ctx.guild.id, "user_id": target})
        if data is None:
            await ctx.send("There is no warning to delete")
        else:
            if what not in data["warn_id"]:
                await ctx.send("Can not find that warn_id")
            else:
                if len(data["warn_id"]) == 1:
                    self.warn_db.delete_one({"guild_id": ctx.guild.id, "user_id": target})
                else:
                    re = data["warn_id"].index(what)
                    data["warn_id"].pop(re)
                    data["kind"].pop(re)
                    data["warner"].pop(re)
                    data["reason"].pop(re)
                    data["time"].pop(re)
                    data["addition"].pop(re)
                    self.warn_db.update_one({"guild_id": data["guild_id"], "user_id": data["user_id"]},
                                            {"$set": {"warn_id": data["warn_id"], "kind": data["kind"],
                                             "warner": data["warner"], "reason": data["reason"], "time": data["time"],
                                                      "addition": data["addition"]}})
                await ctx.message.add_reaction(emoji='👍')

    # TODO more moderation related commands


def setup(bot: commands.Bot):
    """
    Necessary function for a cog that initialize the Moderation class.

    Args:
        bot (commands.Bot): passing in bot for class initialization

    Returns:
        None
    """
    bot.add_cog(Moderation(bot))
    print("Loaded Cog: Moderation")


def teardown(bot: commands.Bot):
    """
    Function to be called upon Cog unload, in this case, it will print message in CMD.

    Args:
        bot (commands.Bot): passing in bot reference for unload.

    Returns:
        None
    """
    bot.remove_cog("Moderation")
    print("Unloaded Cog: Moderation")
