import discord
import typing
import asyncio
from discord.ext import commands
from CustomTools import ignore_check as ic
from CustomTools import prefix


class Help(commands.Cog):
    """
    A class of help command for hana bot.

    Attributes:
        bot (commands.Bot): bot reference
        indicate (list): emote for help menu action
        info (discord.Embed): An embed of how to read the help menu
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.indicate = ['⏮', '⏪', '⏹', '⏩', '⏭', '📋']
        self.info = discord.Embed(
            title="Command Information",
            colour=0x16a085,
            description="""<> - means mandatory input\n() - means optional input\n|> Multi-action will require " " """ 
                        "around the phrase to add or remove the desire words\n\n"""
                        "Do note that some command will require permission to perform. Notably **Moderation**, **Anti "
                        "Raid**, **Ignores**, **Join Role**, **Star Board** in Message, **Mute**, **Log Channels**,"
                        "most of the **Role Menu**, **Prefix**, **Name Scanner**, **Voice Role**, and **Word Trigger**"
        ).set_footer(text="Information Menu, react with other reactions to exit.")

    async def update(self):
        """
        Required for Hana-bot function, not native to discord.py

        Returns:
            None
        """
        pass

    @commands.command()
    async def help(self, ctx: commands.Context, *, stuff: typing.Union[int, str] = None):
        """
        Async method of Help class, bot help command.

        Args:
            ctx(commands.Context): pass in context for analysis and reply
            stuff(typing.Union[int, str]): optional parameters for a specific help menu

        Returns:
            None
        """
        if ic(self, ctx.channel):
            return

        if not ctx.invoked_subcommand:
            data = self.help_pages(self.bot.loaded, prefix(self, ctx), self.bot.user.avatar_url_as(size=64), stuff)
            if data:
                message = await ctx.send(embed=data if stuff else data[0])
                if not stuff:
                    await self.paging(message, ctx.author, data, 0, True)
            else:
                await ctx.send("Can not find the specified help page")

    async def paging(self, m: discord.Message, author: discord.User, data: list, now: int, new: bool = False,
                     in_help: bool = False):
        """
        Async method of Help class, allows user to scroll through help page with reaction. Recursive.

        Args:
            m(discord.Message): the target discord message sent by the bot
            author(discord.User): the author who called the Help menu
            data(list): list of help pages
            now(int): the current help page the user is on
            new(bool): whether or not this is the initial call for the help page
            in_help(bool): whether or not user is in "how to read help" help menu

        Returns:
            None
        """
        if new:
            for i in self.indicate:
                await m.add_reaction(i)

        def check(reaction1: discord.Reaction, user1: discord.User):
            return (reaction1.message.id == m.id) and (user1.id == author.id) and (reaction1.emoji in self.indicate)

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30, check=check)
        except asyncio.TimeoutError:
            await m.clear_reactions()
            await m.edit(content="Help menu timed out.")
            return

        if reaction.emoji == '⏮':
            now = 0
            add = data[now]
        elif reaction.emoji == '⏪':
            if not (now - 1 < 0):
                now -= 1
            add = data[now]
        elif reaction.emoji == '⏹':
            await m.edit(content="Help menu paused")
            if m.channel.type != discord.ChannelType.private:
                await m.clear_reactions()
            return
        elif reaction.emoji == '⏩':
            if not (now + 1 >= len(data)):
                now += 1
            add = data[now]
        elif reaction.emoji == '⏭':
            now = len(data) - 1
            add = data[now]
        else:
            if in_help:
                add = data[now]
                in_help = False
            else:
                add = self.info
                in_help = True

        await m.edit(embed=add)
        if m.channel.type != discord.ChannelType.private:
            await m.remove_reaction(reaction.emoji, user)
        await self.paging(m, author, data, now, in_help=in_help)

    @staticmethod
    def help_pages(available: list, pre: str, icon: str, single: typing.Union[int, str] = None):
        """
        Static method of Help class that returns the generated list of help page base on input or just a page.

        Args:
            available(list): String list of active Cogs
            pre(str): prefix of the bot in that server
            icon(str): icon url for the embed footer
            single(typing.Union[int, str]): try return a single page of help menu if there specification here

        Returns:
            list: resulting help page embeds
            discord.Embed: single help page if single are specified
        """
        pages = {}

        if "Normal" in available:
            pages.update({"Normal": discord.Embed(
                title="`Normal` Commands",
                colour=0xf1c40f
            )})
            pages["Normal"].add_field(inline=False, name=f"{pre}ping", value="Measure the ping connection to discord")
            pages["Normal"].add_field(inline=False, name=f"{pre}avatar (user mention)",
                                      value="Returns the target avatar picture, else your own's")
            pages["Normal"].add_field(inline=False, name=f"{pre}uinfo (user mention)",
                                      value="Return user discord information else your own")
            pages["Normal"].add_field(inline=False, name=f"{pre}utc", value="Return the current time in UTC")
            pages["Normal"].add_field(inline=False, name=f"{pre}sicon",
                                      value="Return the server icon if any [server only]")
            pages["Normal"].add_field(inline=False, name=f"{pre}banner",
                                      value="Return the server's banner if any [server only]")
            pages["Normal"].add_field(inline=False, name=f"{pre}splash",
                                      value="Return the server splash screen if any [server only]")
            pages["Normal"].add_field(inline=False, name=f"{pre}sinfo",
                                      value="Returns the server information if any [server only]")
            pages["Normal"].add_field(inline=False, name=f"{pre}ei",
                                      value="Sends a prompt for user to react to and get the reaction information")
            pages["Normal"].add_field(inline=False, name=f"{pre}lem",
                                      value="Returns a list of the server emotes [server only]")
            pages["Normal"].add_field(inline=False, name=f"{pre}binfo", value="Returns information about this bot")

        if "Moderation" in available:
            pages.update({"Moderation": discord.Embed(
                title="`Moderation` Commands",
                colour=0x9b59b6
            )})
            pages["Moderation"].add_field(inline=False,
                                          name=f"{pre}clear <number of message> (mode/mention) (word to remove)",
                                          value="Clear command the removes targeted all messages\n"
                                                "Remove only messages of the mentioned user by mention after prune "
                                                "integer\n"
                                                "Mode 'have' then followed by key words will remove message containing "
                                                "that\n"
                                                "Mode 'image' or 'video' or 'embed' will clear messages containing file"
                                                " type of mode")
            pages["Moderation"].add_field(inline=False, name=f"{pre}kick <user mention> <reasoning>",
                                          value="Command to kick the mentioned user out of the server")
            pages["Moderation"].add_field(inline=False, name=f"{pre}ban <user mention or ID> <reasoning>",
                                          value="Command to ban the mentioned user out of the server "
                                                "(ID if not in server)")
            pages["Moderation"].add_field(inline=False, name=f"{pre}mban <'reasoning'> "
                                                             f"<all the user mention or ID to ban>...",
                                          value="Command to ban all the mentioned user out of the server")
            pages["Moderation"].add_field(inline=False, name=f"{pre}unban <mention or ID> <reasoning>",
                                          value="Attempt to un-ban the target from server ban list")
            pages["Moderation"].add_field(inline=False, name=f"{pre}warn <member mention> <reason>",
                                          value="Send a warning to that member's DMs and add the warning to record")
            pages["Moderation"].add_field(inline=False, name=f"{pre}wm <mode> <User ID/Mention> (warning ID )",
                                          value="Mode 'show' will list amount of warning the user have\n"
                                                "Mode 'purge' will delete all the warnings the user have\n"
                                                "Mode 'remove' will remove the specified warnings the user have by "
                                                "warn ID")
            pages["Moderation"].add_field(inline=False, name=f"{pre}role_all <role IDs or role mention>...",
                                          value="Apply all the specified role to all the server members, this command "
                                                "have cooldown of 1hr after completion.")
            pages["Moderation"].add_field(inline=False, name=f"{pre}unrole_all <role IDs or role mentions>...",
                                          value="Remove all the specified role from all the server members, "
                                                "this command have cooldown of 1hr after completion")
            pages["Moderation"].add_field(inline=False, name=f"{pre}de", value="Pack all the server emote into a zip, "
                                                                               "this command have 1hr cooldown.")

        if "JoinRole" in available:
            pages.update({"Join Role": discord.Embed(
                title="`Join Role` Commands",
                colour=0x12CBC4
            )})
            pages["Join Role"].add_field(inline=False, name=f"{pre}jr + <Role mention or ID>...",
                                         value="Adds in one or multiple roles into the system.")
            pages["Join Role"].add_field(inline=False, name=f"{pre}jr- <Role mention or ID>...",
                                         value="Remove one or multiple roles from the system.")
            pages["Join Role"].add_field(inline=False, name=f"{pre}jr t", value="Turn on or off auto role system")
            pages["Join Role"].add_field(inline=False, name=f"{pre}jr list",
                                         value="Shows the number of roles in the join role system.")
            pages["Join Role"].add_field(inline=False, name=f"{pre}jr reset",
                                         value="Turns join role system off and wipes the existing setting.")

        if "Ignores" in available:
            pages.update({"Ignore": discord.Embed(
                title="`Ignore` Channel Commands",
                colour=0x95a5a6
            )})
            pages["Ignore"].add_field(inline=False, name=f"{pre}ic", value="List ignored normal command channels")
            pages["Ignore"].add_field(inline=False, name=f"{pre}ignore (channel mention or ID)",
                                      value="Either ignore or un-ignore specified channel")

        if "Message" in available:
            pages.update({"Message": discord.Embed(
                title="`Message` and Star board Commands",
                colour=0xf1c40f
            )})
            pages["Message"].add_field(inline=False, name=f"{pre}getm <message ID> "
                                                          f"(channel mention or ID if not from current one)",
                                       value="Sends the message requested if found on the command call channel.")
            pages["Message"].add_field(inline=False, name=f"{pre}fb info",
                                       value="Obtain information about the fame board if it exist")
            pages["Message"].add_field(inline=False, name=f"{pre}fb c <channel ID / mention> (emote amount req)",
                                       value="Create a fame board with the requirement if it don't exist, "
                                             "emote amount default to 3 if not specified")
            pages["Message"].add_field(inline=False, name=f"{pre}fb delete",
                                       value="Removes fame board if it exist")
            pages["Message"].add_field(inline=False, name=f"{pre}modify <channel mention or ID or number <= 100>",
                                       value="Changes the star board target channel or reaction requirement")

        if "Mute" in available:
            pages.update({"Mute": discord.Embed(
                title="`Mute` Commands",
                colour=0xe74c3c
            )})
            pages["Mute"].add_field(inline=False, name=f"{pre}mr", value="Show the mute role for the server")
            pages["Mute"].add_field(inline=False, name=f"{pre}mr set <role ID or mention>",
                                    value="Set the new mute role to what is specified")
            pages["Mute"].add_field(inline=False, name=f"{pre}mute <target mention or ID> <integer time> <time type> "
                                                       f"(reason for muting)...",
                                    value="Command used to mute a member with specified reason")
            pages["Mute"].add_field(inline=False, name=f"{pre}unmute <target mention or ID> (reason)...",
                                    value="Un-mute a muted member with specified reason")

        if "Notification" in available:
            pages.update({"Log Channels": discord.Embed(
                title="`Log Channel` Commands",
                colour=0x1abc9c
            )})
            pages["Log Channels"].add_field(inline=False, name=f"{pre}lc list",
                                            value="List the log channels in the server")
            pages["Log Channels"].add_field(inline=False, name=f"{pre}lc + (channel mention or ID)",
                                            value="Add a channel as a log channels, current channel if not mentioned")
            pages["Log Channels"].add_field(inline=False, name=f"{pre}lc s (channel mention or ID)",
                                            value="Show a setting menu for the targeted channel, "
                                                  "current channel if not mentioned")

        if "Prefix" in available:
            pages.update({"Prefix": discord.Embed(
                title="`Prefix` Commands",
                colour=0xecf0f1
            )})
            pages["Prefix"].add_field(inline=False, name=f"{pre}prefix", value="Shows the current prefix on the server")
            pages["Prefix"].add_field(inline=False, name=f"{pre}prefix set <new prefix>",
                                      value="Change the bot's prefix for the server to what specified")

        if "RoleMenu" in available:
            pages.update({"Role Menu": discord.Embed(
                title="`Role Menu` Command",
                colour=0x81ecec
            )})
            pages["Role Menu"].add_field(inline=False, name=f"{pre}rm l (Menu Name)",
                                         value="List the menu in the server or about the mentioned role menu")
            pages["Role Menu"].add_field(inline=False, name=f"{pre}rm c (new Menu Name)",
                                         value="Create a new role menu")
            pages["Role Menu"].add_field(inline=False, name=f"{pre}rm + <menu name> <role mention or ID>",
                                         value="Add specified role to the mentioned role menu")
            pages["Role Menu"].add_field(inline=False, name=f"{pre}rm - <menu name> <emote/ID or role mention/ID>",
                                         value="Remove the emote or role from the mentioned menu")
            pages["Role Menu"].add_field(inline=False, name=f"{pre}rm r <menu name>",
                                         value="Attempt to resolve any potential issue in that role menu")
            pages["Role Menu"].add_field(inline=False, name=f"{pre}rm p <menu name>",
                                         value="Remove the role menu")
            pages["Role Menu"].add_field(inline=False,
                                         name=f"{pre}rm s <menu name> <message ID> channel mention or ID)",
                                         value="Set the target message to the target message, if no channel mention"
                                               ", then will attempt to scan the current channel for the message")
            pages["Role Menu"].add_field(inline=False, name=f"{pre}rm toggle <menu name>",
                                         value="Turn the mentioned role menu on or off")
            pages["Role Menu"].add_field(inline=False, name=f"{pre}rm m <menu name>",
                                         value="Switch the mentioned menu's mode between single or multiple")
            pages["Role Menu"].add_field(inline=False, name=f"{pre}rm emote <menu name>",
                                         value="Add all the reactions onto the target message for that mentioned menu")
            pages["Role Menu"].add_field(inline=False, name=f"{pre}rm clear <menu name>",
                                         value="Clear all the reactions on the target message for that mentioned menu")

        if "AntiRaid" in available:
            pages.update({"Anti Raid": discord.Embed(
                title="`Anti Raid` Commands",
                colour=0xf368e0
            )})
            pages["Anti Raid"].add_field(inline=False, name=f"{pre}ar create <raider role mention or ID>",
                                         value="Create anti raid system with given raider role")
            pages["Anti Raid"].add_field(inline=False, name=f"{pre}ar no",
                                         value="Turn off the anti raid alarm if it's on.")
            pages["Anti Raid"].add_field(inline=False, name=f"{pre}ar raid",
                                         value="Turn on the anti raid alarm if it's off.")
            pages["Anti Raid"].add_field(inline=False, name=f"{pre}ar kick (True or False)",
                                         value="Kick all members inside the anti raid cell and pass in whether or not "
                                               "to switch off the anti raid alarm. Default is no.")
            pages["Anti Raid"].add_field(inline=False, name=f"{pre}ar ban (True or False)",
                                         value="Ban all members inside the anti raid cell and pass in whether or not to"
                                               " switch off the anti raid alarm. Default is yes.")
            pages["Anti Raid"].add_field(inline=False, name=f"{pre}ar cell", value="Show anti raid cell status.")
            pages["Anti Raid"].add_field(inline=False, name=f"{pre}ar + <member mention or ID>",
                                         value="Add the target into the anti raid cell.")
            pages["Anti Raid"].add_field(inline=False, name=f"{pre}ar - <user mention or ID>",
                                         value="Remove the target from the anti raid cell if they are in it.")
            pages["Anti Raid"].add_field(inline=False, name=f"{pre}ar s",
                                         value="Bring up anti raid setting menu")

        if "ScanName" in available:
            pages.update({"Name Scan": discord.Embed(
                title="`Name Scan` Commands",
                colour=0x5f27cd
            )})
            pages["Name Scan"].add_field(inline=False, name=f"{pre}ns", value="Shows name scanner status and info.")
            pages["Name Scan"].add_field(inline=False, name=f"{pre}ns toggle", value="Switches name scanner on or off.")
            pages["Name Scan"].add_field(inline=False, name=f"{pre}ns change <new nickname for offenders>",
                                         value="Changes the nickname to give offenders.")
            pages["Name Scan"].add_field(inline=False, name=f"{pre}ns + <new bad name>",
                                         value="Add a new bad name into the name scanner")
            pages["Name Scan"].add_field(inline=False, name=f"{pre}ns - <existing bad name>",
                                         value="Remove a existing 'bad' name from the name scanner")
            pages["Name Scan"].add_field(inline=False, name=f"{pre}ns ++ <'bad names'>...",
                                         value="Adds multiple bad names into the name scanner separated by spaces.")
            pages["Name Scan"].add_field(inline=False, name=f"{pre}ns -- <'existing bad names'>...",
                                         value="Remove multiple name from the name scanner if it exist")
            pages["Name Scan"].add_field(inline=False, name=f"{pre}ns load <word trigger menu name>",
                                         value="Import word list from mentioned word trigger menu into the name "
                                               "scanner.")
            pages["Name Scan"].add_field(inline=False, name=f"{pre}ns unload <word trigger menu name>",
                                         value="Remove words from name scanner based on the mentioned word trigger "
                                               "word list")

        if "WordTrigger" in available:
            pages.update({"Word Trigger": discord.Embed(
                title="`Word Trigger` Commands",
                colour=0xff6b6b
            )})
            pages["Word Trigger"].add_field(inline=False, name=f"{pre}ignore <user mention or ID>",
                                            value="Adds the mentioned user into the word trigger ignore list and ask "
                                                  "whether or not to remove the user if they are already in the list.")
            pages["Word Trigger"].add_field(inline=False, name=f"{pre}il",
                                            value="List members in the word trigger's ignore list.")
            pages["Word Trigger"].add_field(inline=False, name=f"{pre}wt c <name> (True/False to auto delete message)",
                                            value="Create a new word trigger menu with given info. Auto delete is "
                                                  "default to false.")
            pages["Word Trigger"].add_field(inline=False, name=f"{pre}wt s <word trigger name>",
                                            value="Open up the setting menu with option to turn on or off the mentioned"
                                                  " word trigger, delete word trigger, or toggle auto delete.")
            pages["Word Trigger"].add_field(inline=False, name=f"{pre}wt + <word trigger name> <word>",
                                            value="Add the word into that specified word trigger.")
            pages["Word Trigger"].add_field(inline=False, name=f"{pre}wt - <word trigger name> <existing word>",
                                            value="Remove the word from the specified word trigger.")
            pages["Word Trigger"].add_field(inline=False, name=f"{pre}wt ++ <'words to add'>...",
                                            value="Add multiple words into the specified word trigger separated by "
                                                  "space.")
            pages["Word Trigger"].add_field(inline=False, name=f"{pre}wt -- <'words to remove'>...",
                                            value="Remove multiple words into the specified word trigger separated by "
                                                  "space.")
            pages["Word Trigger"].add_field(inline=False, name=f"{pre}wt list (word trigger name)",
                                            value="List all the word triggers in the server no name mentioned, "
                                                  "else will list word list of that word trigger.")
            pages["Word Trigger"].add_field(inline=False, name=f"{pre}wt = <word trigger name> <word>",
                                            value="See if the mentioned word is in the mentioned word trigger.")
            pages["Word Trigger"].add_field(inline=False, name=f"{pre} wt data <use mention or ID>",
                                            value="Display word trigger data of the mentioned user in the server")

        if "VoiceRole" in available:
            pages.update({"Voice Role": discord.Embed(
                title="`Voice Role` Commands",
                colour=0x01a3a4
            )})
            pages["Voice Role"].add_field(name=f"{pre}vcr set <Role mention or ID>",
                                          value="Sets the auto role upon joining vc", inline=False)
            pages["Voice Role"].add_field(name=f"{pre}vcr reset",
                                          value="Disable auto voice chat role.", inline=False)

        if isinstance(single, str):
            try:
                return pages[single]
            except KeyError:
                return
        else:
            ret = []
            for i in pages.values():
                ret.append(i)
            if isinstance(single, int):
                try:
                    return ret[single - 1]
                except IndexError:
                    return
            else:
                count = 1
                for i in ret:
                    i.set_footer(text=f"{count} / {len(pages)} pages", icon_url=icon)
                    count += 1
                return ret

    # TODO help for all commands


def setup(bot: commands.Bot):
    """
    Necessary function for a cog that initialize the Help class.

    Args:
        bot (commands.Bot): passing in bot for class initialization

    Returns:
        None
    """
    bot.add_cog(Help(bot))
    print("Loaded Cog: Help")


def teardown(bot: commands.Bot):
    """
    Function to be called upon Cog unload, in this case, it will print message in CMD.

    Args:
        bot (commands.Bot): passing in bot reference for unload.

    Returns:
        None
    """
    bot.remove_cog("Help")
    print("Unloaded Cog: Help")
