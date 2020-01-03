import discord
from discord.ext import commands
import typing


class AutoClean(commands.Cog):
    """
    A class of events that updates the SQL database.

    Attributes:
        bot(command.Bot): bot reference
    """
    def __init__(self, bot: commands.Bot):
        """
        Constructor of AutoClean cog class.

        Args:
            bot(commands.Bot): pass in bot reference to append
        """
        self.bot = bot

    async def update(self):
        """
        Method required for hana bot function, does nothing.

        Returns:
            None
        """
        pass

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: typing.Union[discord.TextChannel, discord.VoiceChannel]):
        """
        Async function that will be called on channel deletion and wipes that channel from SQL database.

        Args:
            channel (typing.Union[discord.TextChannel, discord.VoiceChannel]): the server channel being deleted

        Returns:
            None
        """
        try:
            temp = self.bot.get_cog("Notification").find(channel.guild.id, channel.id)
            if temp:
                self.bot.mongodb["system_message"].delete_many({"channel_id": channel.id})
                await self.bot.get_cog("Notification").local_update(channel.guild.id)
        except ValueError:
            pass
        except KeyError:
            pass

        try:
            temp = self.bot.get_cog("Ignores").data[channel.guild.id]
            self.bot.mongodb["ignore_channel"].delete_many({"channel_id": channel.id})
            await temp.local_update(channel.guild.id)
        except ValueError:
            pass
        except KeyError:
            pass

        try:
            temp = self.bot.get_cog("Message").staring[channel.guild.id]
            self.bot.mongodb["pin"].delete_many({"channel_id": channel.id})
            await temp.local_update(channel.guild.id)
        except ValueError:
            pass
        except KeyError:
            pass

        try:
            temp = self.bot.get_cog("VoiceRole").data[channel.guild.id]
            self.bot.mongodb["vc_text"].delete_many({"channel_id": channel.id})
            await temp.local_update(channel.guild.id)
        except ValueError:
            pass
        except KeyError:
            pass

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """
        Async function that will be called when a role is deleted, and bot will try remove anything associated with
        the role from the SQL.

        Args:
            role(discord.Role): the role being deleted

        Returns:
            None
        """
        try:
            temp = self.bot.get_cog("RoleMenu").dynamic[role.guild.id]
            self.bot.mongodb["role_menu"].delete_many({"role_id": role.id})
            await temp.update(role.guild.id)
        except ValueError:
            pass
        except KeyError:
            pass

        try:
            temp = self.bot.get_cog("Server").data[role.guild.id]
            self.bot.mongodb["vc_text"].delete_many({"role_id": role.id})
            await temp.local_update(role.guild.id)
        except ValueError:
            pass
        except KeyError:
            pass

        try:
            temp = self.bot.get_cog("AntiRaid").logging[role.guild.id]
            self.bot.mongodb["anti_raid"].delete_many({"role_id": role.id})
            await temp.local_update(role.guild.id)
        except ValueError:
            pass
        except KeyError:
            pass

        try:
            temp = self.bot.get_cog("StaticRole").data[role.guild.id]
            self.bot.mongodb["static_role"].delete_many({"role_id": role.id})
            await temp.update(role.guild.id)
        except ValueError:
            pass
        except KeyError:
            pass

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: discord.guild, before: list, after: list):
        """
        Async function called when client detects change in emoji, and removes the "removed" emoji from the SQL database.

        Args:
            guild (discord.guild): the guild with the change in emoji
            before (list): list of emoji before the change
            after (list): list of emoji after the change

        Returns:
            None
        """

        # reference: https://www.geeksforgeeks.org/python-difference-two-lists/
        removed = [i for i in before if i not in after]
        for i in removed:
            self.bot.mongodb["role_menu"].delete_one({"emoji": str(i.id)})
            self.bot.mongodb["pin"].delete_one({"emote": str(i.id)})

    # TODO additional auto clean feature here


def setup(bot: commands.Bot):
    """
    Necessary function for a cog that initialize the AutoClean class.

    Args:
        bot (commands.Bot): passing in bot for class initialization

    Returns:
        None
    """
    bot.add_cog(AutoClean(bot))
    print("Loaded Cog: AutoClean")


def teardown(bot: commands.Bot):
    """
    Function to be called upon Cog unload, in this case, it will print message in CMD.

    Args:
        bot (commands.Bot): passing in bot reference for unload.

    Returns:
        None
    """
    bot.remove_cog("AutoClean")
    print("Unloaded Cog: AutoClean")
