import discord
from discord.ext import commands
from pymongo import MongoClient
import typing
import datetime


def ignore_check(self, channel: discord.TextChannel, ignore_dm: bool = False, from_main: bool = False):
    """
    A function that checks whether or not that channel allows command.

    Args:
        self: instance of the class this command calls or this can be commands.Bot
        channel (discord.TextChannel): the channel the command call happened in
        ignore_dm (bool): whether or not the command is being ignored in direct messages
        from_main (bool): indicator for whether or not this call is from Main.py, which switches changes how self is
                          read

    Returns:
        True: if channel needs to be ignored
        False: if channel is fine
    """
    if ignore_dm:
        if channel.type is discord.ChannelType.private:
            return True
    try:
        if from_main:
            ignore = self.get_cog("Ignores").find(channel.guild.id, channel.id)
        else:
            ignore = self.bot.get_cog('Ignores').find(channel.guild.id, channel.id)
    except AttributeError:
        return False

    if ignore:
        return True

    return False


def prefix(self, ctx: commands.Context):
    """
    Function that will attempt to find the custom prefix for the bot and return it if any.

    Args:
        self: self reference for that class
        ctx: pass in context for analysis

    Returns:
        str: the custom prefix
    """
    if ctx.channel.type is discord.ChannelType.private:
        return "[]"

    try:
        data = self.bot.get_cog("Prefix").prefix[ctx.guild.id]
    except KeyError:
        return "[]"
    except ValueError:
        return "[]"

    return data


def split_string(line: str, n: int):
    """
    Function that will split the given string into specified length and append it to array.

    Args:
        line(str): the string to split
        n(int): max length for the string

    Returns:
        list: list of the split string
    """
    # code from: https://stackoverflow.com/questions/9475241/split-string-every-nth-character
    return [line[i:i + n] for i in range(0, len(line), n)]


def add_warn(bot: commands.Bot, time: datetime.datetime, guild: int, user: int, warner: id, kind: int, reason: str,
             addition: str = None):
    """
    Function that will attempt to add warning for the specified user base on input onto the warn database.

    Args:
        bot(commands.Bot): bot reference
        time(datetime.datetime): time of warning
        guild(int): guild ID of that warn event
        user(int): ID of the user getting warned
        warner(int): ID of the user warning
        kind(int): type of warning
        reason(str): warning reason
        addition(str): additional information input

    Returns:
        int: number of total warns the user have after
    """
    ret = 1
    warn_db = bot.mongodb["warns"]
    data = warn_db.find_one({"guild_id": guild, "user_id": user})
    time = time.strftime("%#d %B %Y, %I:%M %p UTC")
    if data:
        warn_db.update_one({"guild_id": guild, "user_id": user},
                           {"$push": {"warn_id": data["max"], "kind": kind, "warner": warner, "reason": reason,
                                      "time": time, "addition": addition}})
        warn_db.update_one({"guild_id": guild, "user_id": user}, {"$inc": {"max": 1}})
        ret = len(data["warn_id"]) + 1
    else:
        warn_db.insert_one({"guild_id": guild, "user_id": user, "warn_id": [1], "kind": [kind], "warner": [warner],
                            "reason": [reason], "time": [time], "addition": [addition], "max": 2})

    return ret


class BotCommanders:
    """
    A class that stores the data of bot administrators
    """
    master: discord.User
    workers: list
    ids: list

    @staticmethod
    async def refresh(sql: MongoClient, client: commands.Bot = None):
        """
        A static function that updates the list of bot administrators.

        Args:
            sql (MongoClient: passing in the SQL port
            client (commands.Bot): passing in the bot

        Returns:
            None
        """
        BotCommanders.workers = []
        BotCommanders.ids = []
        data = sql["special"].find({})
        if data:
            for i in data:
                temp = await client.fetch_user(i['workers'])
                BotCommanders.workers.append(temp)
                BotCommanders.ids.append(temp.id)
        if client is not None:
            BotCommanders.master = client.appinfo.owner

    @staticmethod
    async def add(sql: MongoClient, who: typing.Union[discord.Member, discord.User]):
        """
        A static function that adds a bot administrator to the list.

        Args:
            sql (MongoClient): passing in the database to update
            who (typing.Union[discord.Member, discord.User]): the user to add to bot administrators

        Returns:
            True: Successfully added
            False: Failed to add
        """
        sql["special"].insert_one({"workers": who.id})
        if sql["special"].find_one({"workers": who.id}):
            BotCommanders.workers.append(who)
            BotCommanders.ids.append(who.id)
            return True
        else:
            return False

    @staticmethod
    async def remove(sql: MongoClient, who: int):
        """
        A static method that removes a user from the bot administrators list.

        Args:
            sql (MongoClient): the database to update
            who (int): ID of the bot administrator to remove

        Returns:
            False: failed removal
            True: Successful removal
        """
        sql["special"].delete_one({"workers": who})
        if sql["special"].find_one({"workers": who}):
            return False
        else:
            temp = BotCommanders.ids.index(who)
            BotCommanders.ids.pop(temp)
            BotCommanders.workers.pop(temp)
            return True

    @staticmethod
    def has_control(ctx: commands.Context):
        """
        A method that checks whether or not the context user is part of the bot administrators.

        Args:
            ctx (commands.Context): the context to check

        Returns:
            True: if user is part of the bot administrator team
            False: if user not a bot administrator
        """
        return (ctx.author.id == BotCommanders.master.id) or (ctx.author.id in BotCommanders.ids)
