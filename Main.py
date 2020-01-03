import discord
from discord.ext import commands

import os
import typing
import traceback
import platform
import CustomTools
from pymongo import MongoClient
from CustomTools import BotCommanders as Control

# References:
# https://www.youtube.com/playlist?list=PLW3GfRiBCHOiEkjvQj0uaUB1Q-RckYnj9
# https://www.youtube.com/playlist?list=PLpbRB6ke-VkvP1W2d_nLa1Ott3KrDx2aN

# Resources:
# https://flatuicolors.com/
# https://discordpy.readthedocs.io/


def read(file: str, line: int):
    """
    Function that reads the specified file and return specified line.

    Args:
        file (str): the file name to read
        line (int): line to return

    Returns:
        str: the specified line from file
    """
    with open(file, "r") as f:
        lines = f.readlines()
        f.close()
        return lines[line].strip()


token = read("keys.txt", 0)
default_prefix = "[]"


def get_prefix(client: commands.Bot, message: discord.Message):
    """
    A function for the command_prefix parameter in command.Bot that fetches the prefix for a server and allows
    command input via mention.

    Args:
        client (commands.Bot): passing in the bot client
        message (discord.message): the message received

    Returns:
        commands.when_mentioned_or: callable implementation for command_prefix
    """
    if not message.guild:
        return commands.when_mentioned_or(default_prefix)(client, message)
    try:
        prefix = client.get_cog('Prefix').prefix[message.guild.id]
    except AttributeError:
        prefix = None
    except KeyError:
        prefix = None

    if not prefix:
        return commands.when_mentioned_or(default_prefix)(client, message)

    return commands.when_mentioned_or(prefix)(client, message)


bot = commands.Bot(command_prefix=get_prefix)
# remove included help command (help from: (Jack)Tewi# #8723 > https://github.com/JackSkellet )
bot.remove_command('help')


@bot.event
async def on_ready():
    """
    A function that will be called upon when the bot is ready, prints out bot information and owner information.

    Returns:
        None
    """

    bot.defaultPre = default_prefix
    bot.appinfo = await bot.application_info()
    bot.loaded = loaded_cogs
    bot.unloaded = unloaded_cogs
    await Control.refresh(client=bot, sql=bot.mongodb)
    print(f"==================================================\n"
          f"Bot has logged in as: {bot.user.name}\n"
          f"ID:     {bot.user.id}\n"
          f"Owner:  {bot.appinfo.owner} ({bot.appinfo.owner.id})\n"
          f"Platform OS: {platform.system()}\n"
          "Initialization complete\n"
          "==================================================")


@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    """
    A function that will be called when bot encounters a error.
    This function may be removed after testing phase.

    Args:
        ctx (commands.Context): passing in the error context
        error(Exception): the error

    Returns:
        None

    Raises:
        commands.errors: when error that isn't caught
    """
    # Send appropriate error message on command error
    # Code Reference: From Commando950#0251 (119533809338155010) > https://gitlab.com/Commando950

    try:
        show_error = bot.get_cog("Admin").debug
    except AttributeError:
        return

    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.NotOwner):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        return
    elif isinstance(error, commands.BadArgument):
        return
    elif isinstance(error, commands.MissingPermissions):
        if CustomTools.ignore_check(bot, ctx.channel, from_main=True):
            await ctx.send(str(error))
        return

    try:
        await ctx.message.add_reaction(emoji="⚠")
    except discord.HTTPException:
        pass

    if show_error:

        try:
            dest = bot.get_cog("Message")
        except ValueError:
            return

        try:
            raise error
        except Exception:
            await bot.appinfo.owner.send("Error has occurred on this message")
            await dest.encode_message(ctx.message, bot.appinfo.owner)
            report = f"{traceback.format_exc()}"
            mes = CustomTools.split_string(report, 1900)
            for i in range(len(mes)):
                await bot.appinfo.owner.send(f"discord error page{i + 1}:\n```python\n{mes[i]}\n```")
        raise error


loaded_cogs = []
unloaded_cogs = []


@bot.command(aliases=['cs'])
@commands.check(Control.has_control)
async def cog_status(ctx: commands.Context):
    """
    Bot administrators only command that is called with prefix and "cog_status" or "cs". This will reply
    the Cog status of the bot.

    Args:
        ctx (commands.Context): passing in the context for reply location

    Returns:
        None
    """
    loaded = [f"+ **{i}**" for i in loaded_cogs]
    unloaded = [f"- ~~{i}~~" for i in unloaded_cogs]
    embed = discord.Embed(
        colour=0xFFB300,
        title="System Cog Status",
        timestamp=ctx.message.created_at
    ).set_footer(icon_url=bot.user.avatar_url, text="")
    embed.add_field(name=f"Active Cogs [{len(loaded_cogs)}]",
                    value="\n".join(loaded) if len(loaded) > 0 else "None", inline=False)
    embed.add_field(name=f"Inactive Cogs [{len(unloaded_cogs)}]",
                    value="\n".join(unloaded) if len(unloaded) > 0 else "None", inline=False)
    await ctx.send(embed=embed)


@bot.command()
@commands.check(Control.has_control)
async def reload(ctx: commands.Context, *, inputs: str):
    """
    Bot administrators only command that reloads a specified Cog.

    Args:
        ctx (commands.Context): passing in context for reply
        inputs (str): target Cog name

    Returns:
        None
    """
    try:
        bot.unload_extension(f"cogs.{inputs}")
        bot.load_extension(f"cogs.{inputs}")
        temp = bot.get_cog(inputs)
        await temp.update()
        embed = discord.Embed(
            title="COG Reloaded ♻", colour=0x1dd1a1, timestamp=ctx.message.created_at,
            description=f"[**{inputs}**] module got reloaded!")
        await ctx.send(embed=embed)
    except Exception as ex:
        print(f"**{inputs}** failed to reload:")
        await ctx.send(f"```py\n{traceback.format_exc()}\n```")
        raise ex


# unload a specific COG
@bot.command()
@commands.check(Control.has_control)
async def unload(ctx: commands.Context, *, inputs: str):
    """
    Bot administrators only command that unload an active Cog.

    Args:
        ctx (commands.Context): passing in context for reply
        inputs: targeted active Cog

    Returns:
        None
    """
    try:
        bot.unload_extension(f"cogs.{inputs}")
        embed = discord.Embed(
            title="COG Unloaded ⬅", colour=0xEA2027, timestamp=ctx.message.created_at,
            description=f"[**{inputs}**] module got unloaded!")
        await ctx.send(embed=embed)
        unloaded_cogs.append(inputs)
        loaded_cogs.remove(inputs)
    except Exception as ex:
        print(f"**{inputs}** failed to unload:")
        await ctx.send(f"```py\n{traceback.format_exc()}\n```")
        raise ex


# unload a specific COG
@bot.command()
@commands.check(Control.has_control)
async def load(ctx: commands.Context, *, inputs: str):
    """
    Bot administrators only command that loads an inactive Cog.

    Args:
        ctx (commands.Context): passing in context for reply
        inputs (str): targeted inactive Cog

    Returns:
        None
    """
    try:
        bot.load_extension(f"cogs.{inputs}")
        temp = bot.get_cog(inputs)
        await temp.update()
        embed = discord.Embed(
            title="COG Loaded ↪", colour=0x12CBC4, timestamp=ctx.message.created_at,
            description=f"[**{inputs}**] module has been loaded!")
        await ctx.send(embed=embed)
        loaded_cogs.append(inputs)
        unloaded_cogs.remove(inputs)
    except Exception as ex:
        print(f"Failed to load {inputs}:")
        await ctx.send(f"```py\n{traceback.format_exc()}\n```")
        raise ex


@bot.command(aliases=['+staff'])
@commands.is_owner()
async def add_staff(ctx: commands.Context, target: typing.Union[discord.Member, discord.User, int]):
    """
    A bot owner only command that adds a user to the bot administrator list.

    Args:
        ctx (commands.Context): passing in the context for reply
        target (typing.Union[discord.Member, discord.User, int]): passing in the user information

    Returns:
        None
    """
    if isinstance(target, int):
        try:
            target = await bot.fetch_user(target)
        except discord.NotFound:
            await ctx.send("Can not find that user.")
            return
    if Control.master:
        if target.id == Control.master.id:
            await ctx.send("That's my master.")
            return
    if await Control.add(bot.mongodb, target):
        await ctx.message.add_reaction(emoji='👍')
        await ctx.send(f"Added **{target}** to administrator list.")
    else:
        await ctx.message.add_reaction(emoji='👎')


@bot.command(aliases=['-staff'])
@commands.is_owner()
async def remove_staff(ctx: commands.Context, target: typing.Union[discord.Member, discord.User, int]):
    """
    A bot owner only command that removes a user from the bot administrator list.

    Args:
        ctx (commands.Context): passing in the context for reply
        target (typing.Union[discord.Member, discord.User, int]): deletion target

    Returns:
        None
    """
    if not isinstance(target, int):
        target = target.id
    if await Control.remove(bot.mongodb, target):
        await ctx.message.add_reaction(emoji='👍')
    else:
        await ctx.message.add_reaction(emoji='👎')

# cog loader
# reference: https://gist.github.com/EvieePy/d78c061a4798ae81be9825468fe146be
if __name__ == '__main__':
    # append database
    bot.mongodb = MongoClient(read("keys.txt", 1))[read("keys.txt", 2)]
    if platform.system() == "Windows":
        special = ".\\cogs"
    else:
        special = "./cogs"

    print("--------------------------------------------------")
    for cog in os.listdir(special):
        if cog.endswith(".py") and not cog.startswith("_"):
            try:
                element = cog.replace('.py', '')
                cog = f"cogs.{element}"
                bot.load_extension(cog)
                loaded_cogs.append(element)
            except Exception as e:
                print(f"{cog} failed to load:")
                unloaded_cogs.append(cog)
                raise e
    print("--------------------------------------------------")

# run the bot, do not delete or move position
bot.run(token)
