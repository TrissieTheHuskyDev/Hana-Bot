import discord
import typing
import asyncio
from CustomTools import prefix
from discord.ext import commands


class StaticRoleMenu:
    """
    Class designed for role menu function.

    Attributes:
        name(str): role menu name
        active(bool): whether or not the role menu is active
        guild(int): guild ID of that role menu
        target(int): the target message of "role menu"
        channel(int): channel ID of the target message
        custom(list): list indicating whether or not the emotes within are custom
        raw(list): list of emotes when received from database
        multiple(bool): indicator for whether or not the role menu allow multiple roles within the group
        data(dict): dictionary style store discord emote as keys and roles as values
        error(list): list of emote or role that failed to append to data dictionary
    """
    def __init__(self, bot: commands.Bot, pack):
        """
        Constructor for StaticRoleMenu.

        Args:
            bot(commands.Bot): pass in bot reference for processing
            pack: data received from database
        """
        self.name = pack['name']
        self.active = pack['active']
        self.guild = pack['guild_id']
        self.target = pack['message_id']
        self.channel = pack['channel_id']
        self.custom = pack['custom']
        self.raw = pack['emote']
        self.multiple = pack['multi']
        self.hidden = []
        if not self.target or not self.channel:
            self.active = False
        self.data = {}
        self.error = []
        guild = bot.get_guild(pack['guild_id'])
        if not guild:
            raise discord.DiscordException("Can't find the given guild")
        else:
            for i in range(len(pack['custom'])):
                role = guild.get_role(pack['role_id'][i])
                emote = bot.get_emoji(int(pack['emote'][i])) if pack['custom'][i] else pack['emote'][i]
                if role and emote:
                    self.hidden.append(emote)
                    self.data.update({str(pack['emote'][i]): role})
                else:
                    self.error.append(pack['role_id'][i])

    def contain_emote(self, emote: typing.Union[discord.Emoji, str]):
        """
        Method of StaticRoleMenu that checks whether or not the system contains the input specified emote.

        Args:
            emote(typing.Union[discord.Emoji, str]): check whether or not system contains this emote

        Returns:
            bool: indicator whether or not the system contains the specified emote
        """
        return emote in self.hidden

    def contain_role(self, role: discord.Role):
        """
        Method of StaticRoleMenu that checks whether or not the system contains the specified role.

        Args:
            role(discord.Role): the role to check

        Returns:
            bool: indicator whether or not the system contains the specified role
        """
        return role in self.data.values()

    def to_string(self):
        """
        Method of StaticRoleMenu that tries to convert data within the class to string.

        Returns:
            str: data in string form
            None: if the class data is empty
        """
        ret = ""
        for i in self.data.keys():
            num = self.raw.index(str(i))
            hold = i
            if self.custom[num]:
                i = self.hidden[num]
            ret += f"{i} >> {self.data[hold].mention}\n"
        if ret == "":
            return None
        return ret

    def size(self):
        """
        Method of StaticRoleMenu that returns size of dictionary data.

        Returns:
            int: size of dictionary data
        """
        return len(self.data)


class RoleMenu(commands.Cog):
    """
    class of RoleMenu commands.

    Attributes:
        bot(commands.Bot):
        data(dict):
        label(dict):
        db:
    """
    def __init__(self, bot: commands.Bot):
        """
        Constructor for RoleMenu class.

        Args:
            bot(commands.Bot): pass in bot reference
        """
        self.bot = bot
        self.data = {}
        self.label = {}
        self.db = bot.mongodb["static_role"]

    async def update(self, guild: int = None):
        """
        Async method for role menu class that is responsible for updating the label and data from database.

        Args:
            guild(int): specific data to update, if none then update everything from database

        Returns:
            None
        """
        if guild:
            ret = self.db.find({"guild_id": guild})
            try:
                self.data[guild] = {}
            except KeyError:
                self.data.update({guild: {}})
            try:
                self.label[guild] = {}
            except KeyError:
                self.label.update({guild: {}})
        else:
            ret = self.db.find({})
            self.data = {}
            self.label = {}

        for i in ret:
            try:
                self.label[i['guild_id']]
            except KeyError:
                self.label.update({i['guild_id']: {}})
                self.data.update({i['guild_id']: {}})
            self.label[i['guild_id']].update({i['name']: i['message_id']})
            try:
                self.data[i['guild_id']].update({i['message_id']: StaticRoleMenu(self.bot, i)})
            except discord.DiscordException:
                self.db.delete_many({"guild_id": i['guild_id']})

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Event listener for RoleMenu class that calls upon update method when bot is ready.

        Returns:
            None
        """
        await self.update()

    def search(self, guild: int, name: str):
        """
        Method for RoleMenu class that searches the data dictionary for target.

        Args:
            guild(int): the guild ID
            name(int): RoleMenu name

        Returns:
            StaticRoleMenu: reference to that specific StaticRoleMenu in data
            None: if nothing is found
        """
        try:
            return self.data[guild][self.label[guild][name]]
        except KeyError:
            return None

    @commands.group(aliases=['rm'])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def role_menu(self, ctx: commands.Context):
        """
        Command for RoleMenu class and group of role_menu commands. Will reply with correct sub-command usage if none
        or wrong sub-command is provided.

        Args:
            ctx(commands.Context): pass in context for reply

        Returns:
            None
        """
        if not ctx.invoked_subcommand:
            pre = prefix(self, ctx)

            embed = discord.Embed(
                title="`Role Menu` Command",
                colour=0x81ecec
            )
            embed.add_field(inline=False, name=f"{pre}rm l (Menu Name)",
                            value="List the menu in the server or about the mentioned role menu")
            embed.add_field(inline=False, name=f"{pre}rm c (new Menu Name)", value="Create a new role menu")
            embed.add_field(inline=False, name=f"{pre}rm + <menu name> <role mention or ID>",
                            value="Add specified role to the mentioned role menu")
            embed.add_field(inline=False, name=f"{pre}rm - <menu name> <emote/ID or role mention/ID>",
                            value="Remove the emote or role from the mentioned menu")
            embed.add_field(inline=False, name=f"{pre}rm r <menu name>",
                            value="Attempt to resolve any potential issue in that role menu")
            embed.add_field(inline=False, name=f"{pre}rm p <menu name>", value="Remove the role menu")
            embed.add_field(inline=False, name=f"{pre}rm s <menu name> <message ID> channel mention or ID)",
                            value="Set the target message to the target message, if no channel mention, then will "
                                  "attempt to scan the current channel for the message")
            embed.add_field(inline=False, name=f"{pre}rm toggle <menu name>",
                            value="Turn the mentioned role menu on or off")
            embed.add_field(inline=False, name=f"{pre}rm m <menu name>",
                            value="Switch the mentioned menu's mode between single or multiple")
            embed.add_field(inline=False, name=f"{pre}rm emote <menu name>",
                            value="Add all the reactions onto the target message for that mentioned menu")
            embed.add_field(inline=False, name=f"{pre}rm clear <menu name>",
                            value="Clear all the reactions on the target message for that mentioned menu")

            await ctx.send(embed=embed)

    @role_menu.command(aliases=['l'])
    async def list(self, ctx: commands.Context, *, name: str = None):
        """
        Sub-command of role_menu and will list the entire RoleMenu by name for the server if no specified ones are
        given, else it will return embed of emote and the associated role for that role menu.

        Args:
            ctx(commands.Context): pass in context for analysis and reply
            name(str): the specific role menu to show info for if any

        Returns:
            None
        """
        temp = ""
        if not name:
            try:
                data = self.label[ctx.guild.id]
            except KeyError:
                await ctx.send("This server don't have any role menus 😔")
                return
            else:
                for i in data.keys():
                    temp += f"|> **{i}**\n"
            size = len(data.keys())
            c = 0x7ed6df
        else:
            data = self.search(ctx.guild.id, name)
            if not data:
                await ctx.send(f"Can not find the role menu named **{name}**")
                return
            temp = data.to_string()
            size = data.size()
            c = 0x55efc4 if data.active else 0xd63031
        embed = discord.Embed(
            colour=c,
            title="List of role menu(s):" if not name else f"Emotes and Roles in {name}",
            description=temp,
            timestamp=ctx.message.created_at
        ).set_footer(icon_url=self.bot.user.avatar_url_as(size=64), text=f"{size} item(s)")
        if name:
            embed.add_field(name="Mode", value="Single" if not data.multiple else "Multiple", inline=False)
        if name and data.channel and data.target:
            chan = self.bot.get_channel(data.channel)
            if chan:
                try:
                    mes = await chan.fetch_message(data.target)
                except discord.NotFound:
                    mes = None
                if mes:
                    embed.add_field(name="Target Message", value=f"[Jump Link]({mes.jump_url})")
        if name and len(data.error) > 0:
            note = ""
            for i in data.error:
                note += f"<@&{i}> ({i})\n"
            embed.add_field(name="Error Role(s):", value=note)

        await ctx.send(embed=embed)

    @role_menu.command(aliases=['c'])
    async def create(self, ctx: commands.Context, *, name: str):
        """
        Sub-command of role_menu that will attempt to create a new Role Menu of that specified name.

        Args:
            ctx(commands.Context): pass in context for reply
            name(str): the name of the new role menu

        Returns:
            None
        """
        try:
            self.label[ctx.guild.id][name]
        except KeyError:
            pass
        else:
            await ctx.send(f"Role menu with the name **{name}** already exists.")
            return
        self.db.insert_one(
            {"guild_id": ctx.guild.id, "name": name, "active": False, "custom": [], "emote": [], "role_id": [],
             "message_id": ctx.message.id, "channel_id": ctx.channel.id, "multi": True}
        )
        await self.update(ctx.guild.id)
        await ctx.message.add_reaction(emoji='✅')

    @role_menu.command(aliases=['+'])
    async def add(self, ctx: commands.Context, name: str, role: discord.Role):
        """
        Sub-command of role_menu that will attempt to add the specified role to the specified role menu.

        Args:
            ctx(commands.Context): pass in context for reply
            name(str): name of the existing role menu
            role(discord.Role): the role to add to that role menu

        Returns:
            None
        """
        ret = self.search(ctx.guild.id, name)
        if not ret:
            await ctx.send(f"Role menu **{name}** don't exists, please create it first.")
            return
        if ret.contain_role(role):
            await ctx.send(f"`{role}` already exists within **{name}**")
            return
        if len(ret.data) > 19:
            await ctx.send(f"**{name}** menu have reached the max amount of roles")
            return

        def check(reaction1: discord.Reaction, user1: discord.User):
            if (reaction1.message.id == message.id) and (user1.id == ctx.author.id):
                return True

        message = await ctx.send(f"React with the emote you want `{role}` to be")
        custom = False

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30, check=check)
        except asyncio.TimeoutError:
            await message.edit(content="Emote addition timed out ⌛")
            await message.clear_reactions()
            return
        warn = None
        emote = reaction.emoji

        if reaction.custom_emoji:
            if not self.bot.get_emoji(reaction.emoji.id):
                await message.edit(content="Please try use emote from this server or default ones")
                await message.clear_reactions()
                return
            elif ret.contain_emote(reaction.emoji):
                await message.edit(content=f"That emote already exists within {name} role menu. "
                                           f"Please try another one.")
                await message.clear_reactions()
                return
            else:
                emote = str(reaction.emoji.id)
                custom = True
                hold = reaction.emoji
                if hold.guild.id != ctx.guild.id:
                    warn = f"\n⚠ Although Hana can use {hold}, it is not from this server. It is recommended to " \
                           f"use emotes from this server so you have full control."

        hold = reaction
        mes = ""
        await message.clear_reactions()

        if not ret:
            await ctx.send(f"**{name}** role menu does not exists, please create it first with the "
                           f"create command.")
            return
        mes += f"{hold} >> `{role}` >> **{name}**"
        data = self.db.find_one({"guild_id": ctx.guild.id, "name": name})
        data['role_id'].append(role.id)
        data['custom'].append(custom)
        data['emote'].append(str(emote))
        self.db.update_one({"guild_id": ctx.guild.id, "name": name},
                           {"$set": {
                               "custom": data['custom'], "emote": data['emote'], "role_id": data['role_id']
                           }})
        await self.update(ctx.guild.id)
        if warn:
            mes += warn
        await message.edit(content=mes)
        await message.clear_reactions()

    @role_menu.command(aliases=['-'])
    async def remove(self, ctx: commands.Context, name: str,
                     temp: typing.Union[discord.Emoji, discord.Role, str]):
        """
        Sub-command of role_menu, this will attempt to remove the object passed in from the role menu and what's
        associated it with that (it should be either emote or role).

        Args:
            ctx(commands.Context): pass in context for reply
            name(str): name of the role menu to apply such action for
            temp(typing.Union[discord.Emoji, discord.Role, str]): the associated object to remove

        Returns:
            None
        """
        ret = self.search(ctx.guild.id, name)
        if not ret:
            await ctx.send(f"Can not find role menu with the name **{name}**")
            return
        data = self.db.find_one({"guild_id": ctx.guild.id, "name": name})
        if isinstance(temp, discord.Role):
            if not ret.contain_role(temp):
                await ctx.send(f"Can not find `{temp}` within **{name}**")
                return
            num = data['role_id'].index(temp.id)
        else:
            if not ret.contain_emote(temp):
                await ctx.send(f"Can not find {temp} within **{name}**")
                return
            temp = temp.id if isinstance(temp, discord.Emoji) else temp
            num = data['emote'].index(str(temp))

        data['custom'].pop(num)
        data['emote'].pop(num)
        data['role_id'].pop(num)
        act = data['active']
        if len(data['role_id']) < 1:
            act = False
        self.db.update_one({"guild_id": ctx.guild.id, "name": name}, {
            "$set": {"custom": data['custom'], "emote": data['emote'], "role_id": data['role_id'], "active": act}
        })
        await self.update(ctx.guild.id)
        await ctx.message.add_reaction(emoji='✅')

    @role_menu.command(aliases=['r'])
    async def resolve(self, ctx: commands.Context, *, name: str):
        """
        Sub-command of role_menu, this command will attempt to remove any problematic emotes or roles from the
        role menu.

        Args:
            ctx(commands.Context): pass in context for reply
            name(str): name of the role menu to resolve issues for

        Returns:
            None
        """
        find = self.search(ctx.guild.id, name)
        if not find:
            await ctx.send(f"Can not find role menu named **{name}**")
            return
        data = self.db.find_one({"guild_id": ctx.guild.id, "name": name})
        if not data:
            await ctx.message.add_reaction(emoji='❌')
            return
        if len(find.error) > 0:
            for i in find.error:
                num = data['role_id'].index(i)
                data['role_id'].pop(num)
                data['custom'].pop(num)
                data['emote'].pop(num)
            self.db.update_one({"guild_id": ctx.guild.id, "name": name}, {"$set": {
                "custom": data['custom'], "emote": data['emote'], "role_id": data['role_id']
            }})
            await self.update(ctx.guild.id)
            await ctx.message.add_reaction(emoji='✔')
        else:
            await ctx.send(f"**{name}** contains no errors.")

    @role_menu.command(aliases=['p'])
    async def purge(self, ctx: commands.Context, *, name):
        """
        Sub-command of role_menu that will attempt to remove that specified role menu if any.

        Args:
            ctx(commands.Context): pass in context for reply
            name(str): name of the role menu to remove

        Returns:
            None
        """
        def check(reaction1: discord.Reaction, user1: discord.User):
            if (reaction1.message.id == message.id) and (user1.id == ctx.author.id) \
                    and (str(reaction1.emoji) in ['✅', '❌']):
                return True
        data = self.search(ctx.guild.id, name)

        if not data:
            await ctx.send(f"**{name}** role menu does not exist")
        else:
            message = await ctx.send(f"You sure you want to delete role menu: **{name}**?")
            for i in ['✅', '❌']:
                await message.add_reaction(emoji=i)

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=check)
            except asyncio.TimeoutError:
                await message.edit(content="Role menu deletion timed out ⌛")
                await message.clear_reactions()
                return
            if reaction.emoji == "✅":
                self.db.delete_one({"guild_id": ctx.guild.id, "name": name})
                await self.update(ctx.guild.id)
                await message.edit(content=f"Role menu - **{name}** has been purged 💥")
            if reaction.emoji == "❌":
                await message.edit(content=f"Cancelled deletion of role menu: **{name}**")
            await message.clear_reactions()

    @role_menu.command(aliases=['s'])
    async def set(self, ctx: commands.Context, name: str, mes: int, chan: discord.TextChannel = None):
        """
        Sub-command of role_menu that will attempt to change the targeted message, channel specification is required
        if the target message is not in the same channel of command call.

        Args:
            ctx(commands.Context): pass in context for reply and potential analysis
            name(str): name of the role menu
            mes(int): message ID of that target message
            chan(discord.TextChannel): optional input, location of the target message

        Returns:
            None
        """
        find = self.search(ctx.guild.id, name)
        if not find:
            await ctx.send(f"Can not find role menu with the name **{name}**")
            return
        chan = ctx.channel if not chan else chan
        fail = False
        if not chan:
            fail = True
        else:
            mes = await chan.fetch_message(mes)
            if not mes:
                fail = True
        if fail:
            await ctx.send("Can not find the target message")
            return
        if chan.id == find.channel and mes.id == find.target:
            await ctx.send(f"Received same input as one stored in database, no changes made.")
            return
        self.db.update_one({"guild_id": ctx.guild.id, "name": name}, {"$set": {
            "message_id": mes.id, "channel_id": chan.id
        }})
        await self.update(ctx.guild.id)
        await ctx.message.add_reaction(emoji='✅')

    @role_menu.command(aliases=['t'])
    async def toggle(self, ctx: commands.Context, *, name: str):
        """
        Sub-command of role_menu, this will toggle the role menu on or off depending on it's last state.

        Args:
            ctx(commands.Context): pass in context for reply
            name(str): name of the role menu

        Returns:
            None
        """
        data = self.search(ctx.guild.id, name)
        if not data:
            await ctx.send(f"Can not find role menu named **{name}**")
            return
        if data.size() < 1:
            await ctx.send(f"Role menu **{name}** does not contain any item, toggle failed.")
            return
        self.db.update_one({"guild_id": ctx.guild.id, "name": name}, {"$set": {
            "active": not data.active
        }})
        data.active = False if data.active else True
        await ctx.message.add_reaction(emoji='✅')

    async def seek(self, ctx: commands.Context, name: str):
        """
        Async method of RoleMenu class, this method will attempt to find the target message along with the
        StaticRoleMenu.

        Args:
            ctx(commands.Context): pass in context for potential error reply
            name(str): name of the role menu

        Returns:
            discord.Message: if the target message is found
            StaticRoleMenu: the StaticRoleMenu reference for that role menu
        """
        data = self.search(ctx.guild.id, name)
        if not data:
            await ctx.send(f"Can not find role menu named **{name}**")
            return
        if not data.channel or not data.target:
            await ctx.send(f"Target message have not been configured, please use the set command before proceeding.")
            return
        chan = self.bot.get_channel(data.channel)
        if chan:
            msg = await chan.fetch_message(data.target)
            if msg:
                return msg, data

    @role_menu.command(aliases=['m'])
    async def mode(self, ctx: commands.Context, *, name: str):
        """
        Sub-command of role_menu, this command will attempt to toggle the mode of the specified role menu based on it's
        current one.

        Args:
            ctx(commands.Context): pass in context for reply
            name(str): name of the role menu

        Returns:
            None
        """
        data = self.search(ctx.guild.id, name)
        if not data:
            await ctx.send(f"Can not find role menu named **{name}**")
            return
        data.multiple = not data.multiple
        self.db.update_one({"guild_id": ctx.guild.id, "name": name}, {"$set": {
            "multi": data.multiple
        }})
        await ctx.message.add_reaction(emoji='✌' if data.multiple else '☝')

    @role_menu.command(aliases=['e'])
    async def emote(self, ctx: commands.Context, *, name: str):
        """
        Sub-command for role_menu that adds all the emote set for that role menu to that target message.

        Args:
            ctx(commands.Context): pass in context for reply
            name(str): name of the role menu

        Returns:
            None
        """
        try:
            msg, data = await self.seek(ctx, name)
        except discord.NotFound:
            await ctx.send("Target message not set/not found")
            return
        if not msg or not data:
            return
        for i in data.data.keys():
            num = data.raw.index(str(i))
            if data.custom[num]:
                i = self.bot.get_emoji(int(i))
            await msg.add_reaction(emoji=i)
        await ctx.message.add_reaction(emoji='✅')

    @role_menu.command()
    async def clear(self, ctx: commands.Context, *, name: str):
        """
        Sub-command of role_menu that will clear all the reaction for that target message.

        Args:
            ctx(commands.Context): pass in context for reply
            name(str): name of the role menu

        Returns:
            None
        """
        msg, hold = await self.seek(ctx, name)
        if not msg:
            return
        await msg.clear_reactions()
        await ctx.message.add_reaction(emoji='✅')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """
        Event listener for RoleMenu when reaction is added that tries to find the StaticRoleMenu for that message ID,
        and only process if something is found.

        Args:
            payload(discord.RawReactionActionEvent): payload on any added reaction bot can see

        Returns:
            None
        """
        try:
            data = self.data[payload.guild_id][payload.message_id]
        except KeyError:
            return
        if data.active:
            member = self.bot.get_guild(payload.guild_id).get_member(payload.user_id)
            if member.bot:
                return
            try:
                temp = payload.emoji.name if payload.emoji.is_unicode_emoji() else str(payload.emoji.id)
                role = data.data[temp]
            except KeyError:
                return
            if role not in member.roles:
                try:
                    await member.add_roles(role, reason=f"[Role Menu] {data.name} request")
                except discord.HTTPException:
                    return
            else:
                if not data.multiple:
                    await member.remove_roles(role, reason=f"[Role Menu] {data.name} request")
            chan = self.bot.get_channel(payload.channel_id)
            msg = await chan.fetch_message(payload.message_id)
            if not data.multiple:
                roles = [i for i in data.data.values() if i != role and i in member.roles]
                await member.remove_roles(*roles, reason=f"[Role Menu] {data.name} - single-only")
                await msg.remove_reaction(payload.emoji, member)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """
        Event listener for RoleMenu when reaction is removed that tries to find the StaticRoleMenu for that message ID,
        and only process if something is found.

        Args:
            payload(discord.RawReactionActionEvent): payload on any removed reaction bot can see

        Returns:
            None
        """
        try:
            data = self.data[payload.guild_id][payload.message_id]
        except KeyError:
            return
        if data.active and data.multiple:
            member = self.bot.get_guild(payload.guild_id).get_member(payload.user_id)
            if member.bot:
                return
            role = data.data[payload.emoji.name if payload.emoji.is_unicode_emoji() else str(payload.emoji.id)]
            await member.remove_roles(role, reason=f"[Role Menu] {data.name} request")


def setup(bot: commands.Bot):
    """
    Necessary function for a cog that initialize the RoleMenu class.

    Args:
        bot (commands.Bot): passing in bot for class initialization

    Returns:
        None
    """
    bot.add_cog(RoleMenu(bot))
    print("Loaded Cog: RoleMenu")


def teardown(bot: commands.Bot):
    """
    Function to be called upon Cog unload, in this case, it will print message in CMD.

    Args:
        bot (commands.Bot): passing in bot reference for unload.

    Returns:
        None
    """
    bot.remove_cog("RoleMenu")
    print("Unloaded Cog: RoleMenu")
