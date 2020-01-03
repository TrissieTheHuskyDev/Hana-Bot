import discord
from discord.ext import commands

import asyncio
import random
import typing
from CustomTools import ignore_check as ic
from CustomTools import BotCommanders as Control
from CustomTools import prefix


class Skill:
    def __init__(self, name: str, mode: str, sp: int, desc, shhh: int):
        self.name = name
        self.cost = sp
        self.desc = desc
        self.mode = mode
        self.secret = shhh

    def simple(self):
        return f"{self.mode} {self.name}"

    @staticmethod
    def find(name: str, data: list):
        for i in data:
            if name == i.name:
                return i


class Basic(Skill):
    def __init__(self, name: str = None, sp: int = None, desc: str = None, dmg: int = None, mode: int = None,
                 pack: dict = None):
        if pack:
            if pack['type'] != 3:
                raise ValueError(f"Unsupported type of {pack['type']} instead of 3")
            name = pack['name']
            sp = pack['cost']
            desc = pack['details']
            dmg = pack['v4']
            mode = pack['mode']
        if not (name or sp or desc or dmg or mode):
            raise ValueError("not enough data to initialize Basic")
        self.damage = dmg
        label = ["⚔", "🏹", "✡", "✨"]
        Skill.__init__(self, name, label[mode], sp, desc, mode)
        if mode > 3:
            raise ValueError(f"Unsupported operation value {mode}")

    def to_embed(self):
        embed = discord.Embed(
            colour=0x00cec9,
            title=f"{self.mode} [Basic Attack] {self.name}"
        )
        embed.add_field(name="Damage", value=f"{self.damage}% of attack power")
        embed.add_field(name="SP Cost", value=f"{self.cost}")
        embed.add_field(name="Skill Info", value=f"{self.desc}", inline=False)
        return embed


class Aggressive(Skill):
    def __init__(self, name: str = None, sp: int = None, desc: str = None, dmg: float = None, energy: int = None,
                 mode: int = None, special: int = None, pack: dict = None):
        if pack:
            if pack['type'] != 0:
                raise ValueError(f"Unsupported type of {pack['type']} instead of 0")
            name = pack['name']
            sp = pack['cost']
            desc = pack['details']
            dmg = pack['v4']
            energy = pack['v0']
            mode = pack['mode']
            special = pack['v1']
        if not (name or sp or desc or dmg or energy or mode):
            raise ValueError("Not enough data to initialize Aggressive")
        self.damage = dmg
        self.use_cost = energy
        self.special = special
        if mode > 3:
            raise ValueError(f"Unsupported operation value {mode}")
        label = ["⚔", "🏹", "✡", "✨"]
        Skill.__init__(self, name, label[mode], sp, desc, mode)

    def to_embed(self):
        embed = discord.Embed(
            colour=0xee5253,
            title=f"{self.mode} [Power Attack] {self.name}"
        )
        embed.add_field(name="Damage", value=f"{self.damage}% Boost from Attack Points", inline=False)
        embed.add_field(name="Energy Cost", value=f"{self.use_cost}")
        embed.add_field(name="SP Cost", value=f"{self.cost}")
        if self.special:
            text = ["Ignore defensive passive against this type of attack.",
                    "Drain 2.5% health of damage inflicted.",
                    "Drain 5% energy of damage inflicted.",
                    "Drain 1% of health and energy of damage inflicted.",
                    "User will take 7% of damage inflicted on use.",
                    "User will be immobilized for the next round."]
            embed.add_field(name="Special Effect", value=text[self.special])
        embed.add_field(name="Skill Info", value=f"{self.desc}", inline=False)
        return embed


class Passive(Skill):
    def __init__(self, name: str = None, sp: int = None, desc: str = None, value: float = None, mode: int = None,
                 addition: int = None, pack: dict = None):
        if pack:
            if pack['type'] != 1:
                raise ValueError(f"Unsupported type of {pack['type']} instead of 1")
            name = pack['name']
            sp = pack['cost']
            desc = pack['details']
            value = pack['v4']
            mode = pack['mode']
            addition = pack['v0']

        if not (name or sp or desc or value or mode or addition):
            raise ValueError("Not enough data to initialize Passive")
        self.modifier = value
        self.extra = addition
        if mode > 3:
            raise ValueError(f"Unsupported operation value {mode}")
        label = ["🛡", "⬆", "💖", "🍹"]
        Skill.__init__(self, name, label[mode], sp, desc, mode)

    def to_embed(self):
        embed = discord.Embed(
            colour=0x55efc4,
            title=f"{self.mode} [Passive] {self.name}"
        )
        embed.add_field(name="SP Cost", value=f"{self.cost}")
        label = ["⚔", "🏹", "✡", "✨", "**all**"]
        if self.secret == 0:
            val = f"Resist damage from {label[self.extra]} attack by {self.modifier}%."
        elif self.secret == 1:
            val = f"Increase {label[self.extra]} attack damage by {self.modifier}%."
        elif self.secret == 2:
            val = f"Health regenerates by {self.modifier}% per round."
        else:
            val = f"Energy regenerates by {self.modifier}% per round."
        embed.add_field(name="Special Effect", value=val, inline=False)
        embed.add_field(name="Skill Info", value=f"{self.desc}", inline=False)
        return embed


class Special(Skill):
    def __init__(self, name: str = None, sp: int = None, desc: str = None, value: float = None, mode: int = None,
                 req: int = None, pack: dict = None):
        if pack:
            name = pack['name']
            sp = pack['cost']
            desc = pack['details']
            mode = pack['mode']
            value = pack['v4']
            req = pack['v0']

        if not (name or sp or desc or mode):
            raise ValueError("Not enough data to initialize Special")
        label = ['🔥', '🤕', '😇', '🆙', '🙅']
        Skill.__init__(self, name, label[mode], sp, desc, mode)
        self.modifier = value
        self.extra = req

    def to_embed(self):
        embed = discord.Embed(
            colour=0x6c5ce7,
            title=f"{self.mode} [Special] {self.name}"
        )
        embed.add_field(name="SP Cost", value=f"{self.cost}")
        lab = [
            f"Attack damage raise by 2% every {self.extra} round up to {self.modifier}%",
            f"The max amount of damage you can receive is {self.modifier}% of your health",
            f"When health reaches 0, return back to life with {self.modifier}% health",
            f"Experience gained after battle is boosted by {self.modifier}%",
            f"Negates all negative effect from using power attack (energy cost excluded)"
        ]
        embed.add_field(name="Effect", value=f"{lab[self.secret]}", inline=False)
        embed.add_field(name="Skill Info", value=f"{self.desc}", inline=False)
        return embed


class Player:
    def __init__(self, pack: dict, basic, active, passive, special, nums, dis):
        self.exhausted = False
        self.victories = pack['wins']
        self.maxHP = self.hp = pack['hp']
        self.maxMP = self.mp = pack['mp']
        self.strength = pack['power']
        self.speed = pack['speed']
        self.basic = Skill.find(pack['basic'], basic)
        self.special = Skill.find(pack['special'], special)
        self.powers = {}
        self.ready = True
        self.resist = [0, 0, 0, 0]
        self.boost = [0, 0, 0, 0]
        regen_mod = [0, 0]
        self.regen = [0, 0]
        self.revive = 0
        if not self.special:
            self.revive = 0
        elif self.special.secret == 2:
            self.revive = self.special.modifier
        for i in range(5):
            check = pack['attack'][i]
            if check != '-----':
                self.powers.update({nums[i]: Skill.find(check, active)})
        for i in pack['passive']:
            if i != '-----':
                temp = Skill.find(i, passive)
                if temp:
                    if temp.secret == 0:
                        if temp.extra == 4:
                            for z in range(4):
                                self.resist[z] += temp.modifier
                        else:
                            self.resist[temp.extra] += temp.modifier
                    elif temp.secret == 1:
                        if temp.extra == 4:
                            for z in range(4):
                                self.resist[z] += temp.modifier
                        else:
                            self.boost[temp.extra] += temp.modifier
                    elif temp.secret == 2:
                        regen_mod[0] += temp.modifier
                    else:
                        regen_mod[1] += temp.modifier
        self.regen[0] = self.maxHP * (regen_mod[0] / 100)
        self.regen[1] = self.maxMP * (regen_mod[1] / 100)
        self.account = dis

    def next(self):
        if self.hp > 0:
            if not self.exhausted:
                self.ready = True
            self.exhausted = False
            self.hp += self.regen[0]
        self.mp += self.regen[1] + 10
        if self.hp > self.maxHP:
            self.hp = self.maxHP
        elif 0 > self.hp:
            self.hp = 0
        if self.mp > self.maxMP:
            self.mp = self.maxMP
        elif 0 > self.mp:
            self.mp = 0

        if self.special:
            if self.special.secret == 0:
                for i in range(4):
                    self.boost[i] += self.special.modifier

        if self.hp == 0 and self.revive > 0:
            self.hp = self.maxHP * (self.revive / 100)
            self.revive = 0

        if self.hp == 0:
            return True
        else:
            return False

    def available(self):
        ret = f"====Basic Move====\n👊 - {self.basic.mode} {self.basic.name}"
        if len(self.powers) > 0:
            ret += "\n====Power Moves====\n"
        arr = ["👊"]
        for key in self.powers:
            temp = self.powers[key]
            if (self.mp - temp.use_cost) >= 0:
                arr.append(key)
                ret += f"{key} - {temp.mode} {temp.name}\n"
            else:
                ret += f"~~{key} - {temp.mode} {temp.name}~~ Low Energy\n"
        return arr, ret

    def attack(self, label: str):
        if label == "👊":
            temp = ((self.basic.damage + self.boost[self.basic.secret]) / 100) * self.strength
            return [self.basic.secret, temp, None]
        else:
            temp = self.powers[label]
            power = (temp.damage / 100) * self.strength
            power += power * (self.boost[temp.secret] / 100)
            ret = [temp.secret, power, temp.special]
            if ret[2] is not None:
                if ret[2] == 1:
                    self.hp += int(round(0.025 * power))
                elif ret[2] == 2:
                    self.mp += int(round(0.05 * power))
                elif ret[2] == 3:
                    add = int(round(0.01 * power))
                    self.hp += add
                    self.mp += add
                elif ret[2] == 4:
                    if self.special:
                        if self.special.secret != 4:
                            self.hp -= int(round(power * 0.07))
                    else:
                        self.hp -= int(round(power * 0.07))
                elif ret[2] == 5:
                    if self.special:
                        if self.special.secret != 4:
                            self.ready = False
                            self.exhausted = True
                    else:
                        self.ready = False
                        self.exhausted = True
            return ret

    def receive(self, dmg: list):
        ouch = dmg[1]
        endure = False
        if self.special:
            if self.special.secret == 1:
                endure = True
                maxi = int(self.maxHP * (self.special.modifier / 100))
        if dmg[2] != 0:
            ouch -= int(ouch * (self.resist[dmg[0]] / 100))
        if endure:
            if ouch > maxi:
                ouch = maxi
        self.hp -= ouch
        if self.hp < 0:
            self.hp = 0
        self.hp = int(round(self.hp))


class Leveling(commands.Cog):
    nums = None
    basic = None
    active = None

    def __init__(self, bot):
        self.bot = bot
        self.time = 20
        self.mod = 1
        self.cooldown = []
        self.last_msg = {}
        self.ready = False
        self.basic = []
        self.active = []
        self.passive = []
        self.special = []
        self.all = []
        self.symbols = ['✅', '❌']
        self.nums = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣']

        self.skill_db = bot.mongodb["skills"]
        self.lv_db = bot.mongodb["user_data"]

    @commands.Cog.listener()
    async def on_ready(self):
        await self.update()

    @staticmethod
    def progress_bar(now: int, total: int):
        # reference: https://gist.github.com/vladignatyev/06860ec2040cb497f0f3
        # help from (Jack)Tewi#8723
        bar_len = 14
        fill = int(round(bar_len * now / float(total)))
        bar = "[▬](http://g.cn/)" * fill + "▬" * (bar_len - fill)
        return bar

    async def insert_skill(self, ctx, ty: int, name: str, desc: str, mode: int, cost: int, v0: int = None,
                           v1: int = None,
                           v2: int = None, v3: int = None, v4: float = None, v5: float = None, v6: float = None):
        if not self.ready:
            await ctx.send("Bot fetching, try again later")
            return

        find = self.skill_db.find_one({"name": name})
        if find:
            await ctx.send(f"`{name}` already exists")
        if not find:
            if ty == 0:
                temp = Aggressive(name, cost, desc, v4, v0, mode, v1)
            elif ty == 3:
                temp = Basic(name, cost, desc, v4, mode)
            elif ty == 1:
                temp = Passive(name, cost, desc, v4, mode, v0)
            elif ty == 2:
                temp = Special(name, cost, desc, v4, mode, v0)
            else:
                raise ValueError(f"Unknown type of {ty}")

            msg = await ctx.send("You sure you want to add this into the skill list?", embed=temp.to_embed())

            for i in self.symbols:
                await msg.add_reaction(emoji=i)

            def check(reaction1, user1):
                if (reaction1.message.id == msg.id) and (user1.id == ctx.author.id):
                    if str(reaction1.emoji) in self.symbols:
                        return True

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=20, check=check)
            except asyncio.TimeoutError:
                await msg.edit(embed=None, content="Timed out")
            else:
                if reaction.emoji == '✅':
                    self.skill_db.insert_one(
                        {"type": ty, "name": name, "mode": mode, "v0": v0, "v1": v1, "v2": v2, "v3": v3, "v4": v4,
                         "v5": v5, "v6": v6, "cost": cost, "details": desc}
                    )
                    await msg.edit(embed=None, content=f"**{name}** added!")
                    await self.update()
                else:
                    await msg.edit(embed=None, content="Action Cancelled")

            await msg.clear_reactions()

    def calculate(self, pack: dict, cheat: bool):
        ret = False
        while pack['exp'] >= self.level_limit(pack['level']):
            ret = True
            pack['power'] += random.randint(7, 20)
            pack['speed'] += random.randint(12, 31)
            pack['hp'] += random.randint(100, 150)
            pack['mp'] += random.randint(25, 50)
            pack['level'] += 1
            pack['sp'] += 10
            if not cheat:
                pack['exp'] = (pack['exp'] - self.level_limit(pack['level']))
        return ret

    async def boost(self, channel, person: discord.Member, cheat: bool = False, amount: int = None):
        ret = self.lv_db.find_one({"user_id": person.id})
        if ret:
            data = {'level': ret['level'], 'power': ret['power'], 'speed': ret['speed'], 'sp': ret['sp'],
                    'hp': ret['hp'],
                    'mp': ret['mp'], 'exp': ret['exp']}
            if not amount:
                data['exp'] += (self.mod * random.randint(12, 26))
            else:
                data['exp'] += amount
            if self.calculate(data, cheat):
                if not ic(self, channel) and not cheat:
                    await channel.send(f"{person.mention} is now Level {data['level'] + 1}!!")
            self.lv_db.update_one({"user_id": person.id}, {"$set": {
                "level": data['level'], "exp": data['exp'], "power": data['power'],
                "speed": data['speed'], "sp": data['sp'], "hp": data['hp'], "mp": data['mp']
            }})
        else:
            null = ['-----', '-----', '-----', '-----', '-----']
            self.lv_db.insert_one(
                {"user_id": person.id, "level": 1, "exp": random.randint(12, 26), "sp": 5, "power": 10, "speed": 20,
                 "skills": ["Punch"], "attack": null, "passive": null, "hp": 250, "mp": 100, "basic": "Punch",
                 "wins": 0, "special": None}
            )
            if cheat:
                await channel.send("Since the user is new, a new profile has been created. Boosting now...")
                await self.boost(channel, person, cheat, amount)

    @staticmethod
    def level_limit(level: int):
        return 7 * level ** 2 + 43

    async def update(self):
        self.ready = False
        self.basic = [Basic(pack=i) for i in self.skill_db.find({"type": 3})]
        self.active = [Aggressive(pack=i) for i in self.skill_db.find({"type": 0})]
        self.passive = [Passive(pack=i) for i in self.skill_db.find({"type": 1})]
        self.special = [Special(pack=i) for i in self.skill_db.find({"type": 2})]
        self.all = self.basic + self.active + self.passive + self.special
        self.ready = True

    async def battle(self, msg, p1: Player, p2: Player, speed1: int, speed2: int, turn: int = 1):
        speed1 += p1.speed
        speed2 += p2.speed
        emotes = []
        order = [p1, p2] if (speed1 > speed2) else [p2, p1]
        u = 0 if (speed1 > speed2) else 1
        o = 1 if u == 0 else 0
        if speed1 >= 10000 and speed2 >= 10000:
            speed1 -= 10000
            speed2 -= 10000
        for i in range(2):
            if order[i].hp > 0 and order[i].ready:
                emotes, string = order[i].available()
                for k in emotes:
                    await msg.add_reaction(emoji=k)
                op = 1 if i == 0 else 0
                embed = discord.Embed(
                    title=f"{order[op].account}'s Health: {order[op].hp}",
                    colour=order[i].account.colour
                )
                embed.set_author(icon_url=order[i].account.avatar_url, name=f"{order[i].account}'s Turn [round {turn}]")
                embed.add_field(name="Your Health",
                                value=f"{self.progress_bar(order[i].hp, order[i].maxHP)} {order[i].hp}",
                                inline=False)
                embed.add_field(name="Your Energy",
                                value=f"{self.progress_bar(order[i].mp, order[i].maxMP)} {order[i].mp}",
                                inline=False)
                emotes, moves = order[i].available()
                embed.add_field(name="Options", value=moves, inline=False)
                await msg.edit(embed=embed, content=f"{order[i].account.mention}")

                def choose(reaction1, user1):
                    return reaction1.emoji in emotes and user1.id == order[i].account.id

                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=30, check=choose)
                    temp = reaction.emoji
                    await msg.remove_reaction(temp, user)
                except asyncio.TimeoutError:
                    temp = random.choice(emotes)
                order[op].receive(order[i].attack(temp))

        t1 = not order[u].next()
        t2 = not order[o].next()

        if t1 and t2:
            await self.battle(msg, order[u], order[o], speed1, speed2, turn + 1)
        else:
            winner = order[u] if t1 else order[o]
            await msg.edit(embed=None,
                           content=f"{winner.account.mention} won the match against "
                           f"{order[o].account.mention if t1 else order[u].account.mention}!")
            self.lv_db.update_one({"user_id": winner.account.id}, {"$inc": {"wins": 1}})
            check1 = False
            check2 = False
            if p1.special:
                if p1.special.secret == 3:
                    check1 = True
            if p2.special:
                if p2.special.secret == 3:
                    check2 = True
            await self.boost(msg.channel, order[u].account,
                             amount=turn if not check1 else turn + turn * (p1.special.modifier / 100))
            await self.boost(msg.channel, order[o].account,
                             amount=turn if not check2 else turn + turn * (p2.special.modifier / 100))

    @commands.command()
    @commands.check(Control.has_control)
    async def exp_mod(self, ctx, n: int = None):
        if not n:
            await ctx.send(f"Current EXP modifier: **{self.mod}**")
        else:
            await ctx.send(f"EXP modifier has been changed from `{self.mod}` to **{n}**")
            self.mod = n

    @commands.command()
    @commands.check(Control.has_control)
    async def exp_cooldown(self, ctx, n: int = None):
        if not n:
            await ctx.send(f"The current EXP cooldown is **{self.time}**")
        else:
            await ctx.send(f"EXP cooldown changed from `{self.time}` to **{n}**")
            self.time = n

    @commands.command(aliases=['ge'])
    @commands.check(Control.has_control)
    async def give_exp(self, ctx, amount: int, target: typing.Union[discord.Member, discord.User, int, None]):
        target = ctx.author if not target else target
        if isinstance(target, int):
            target = await self.bot.fetch_user(target)
        await self.boost(ctx.channel, target, True, amount)
        await ctx.message.add_reaction(emoji='👍')

    @commands.command()
    async def skill(self, ctx, *, name: str = None):
        if not self.ready:
            return

        if ic(self, ctx.channel):
            return

        if not name:
            user = self.lv_db.find_one({"user_id": ctx.author.id})
            if not user:
                return

            b = ""
            a = ""
            p = ""
            s = ""

            for i in user['skills']:
                k = Skill.find(i, self.all)
                if isinstance(k, Basic):
                    b += f"▶ {k.mode} {k.name}\n"
                elif isinstance(k, Aggressive):
                    a += f"▶ {k.mode} {k.name}\n"
                elif isinstance(k, Passive):
                    p += f"▶ {k.mode} {k.name}\n"
                elif isinstance(k, Special):
                    s += f"▶ {k.mode} {k.name}\n"
                else:
                    temp = user['skills']
                    temp.remove(i)
                    self.lv_db.update_one({"user_id": ctx.author.id}, {"$set": {"skills": temp}})

            embed = discord.Embed(
                title=f"{ctx.author}'s skills",
                timestamp=ctx.message.created_at,
                colour=0x1abc9c
            ).set_footer(icon_url=ctx.author.avatar_url_as(size=64))

            if len(b) > 0:
                embed.add_field(name="Basic Attacks", value=b)
            if len(a) > 0:
                embed.add_field(name="Power Attacks", value=a)
            if len(p) > 0:
                embed.add_field(name="Passives", value=p)
            if len(s) > 0:
                embed.add_field(name="Specials", value=s)

            await ctx.send(embed=embed)
        elif name == "menu":
            await self.skill_menu(ctx)
        else:
            i = Skill.find(name, self.all)
            if i:
                await ctx.send(embed=i.to_embed())
            else:
                await ctx.send("Hm? What skill is that?")

    @commands.command(aliases=['lvl'])
    async def level(self, ctx, target: discord.Member = None):
        if ic(self, ctx.channel):
            return
        target = ctx.author if not target else target

        if target.bot:
            await ctx.send("That's a botto")
            return

        data = self.lv_db.find_one({"user_id": target.id})

        if not data:
            await ctx.send("Can't find anything about that person")
        else:
            level = data['level']
            bar = self.progress_bar(data['exp'], self.level_limit(level))
            embed = discord.Embed(
                colour=target.colour,
                timestamp=ctx.message.created_at,
                title=f"{target}"
            ).set_thumbnail(url=target.avatar_url_as(size=256))
            embed.add_field(name="Health 💗 ", value=f"{data['hp']}")
            embed.add_field(name="Energy ⚡ ", value=f"{data['mp']}")
            embed.add_field(name="Power 💪", value=f"{data['power']}")
            embed.add_field(name="Speed 👟 ", value=f"{data['speed']}")
            embed.add_field(name="Basic Attack 👊", value=f"{data['basic']}")
            embed.add_field(name="Special 🏆", value=data['special'] if data['special'] else "None")
            embed.add_field(name="Power Attacks 🗡", value="\n".join(data['attack']) if not len(data['attack']) == 0
                            else "None")
            embed.add_field(name="Passives 📙", value="\n".join(data['passive']) if not len(data['passive']) == 0 else
                            "None")
            embed.add_field(inline=False, name=f"𝕃𝕖𝕧𝕖𝕝 **{level}**",
                            value=f"{bar}\n"
                                  f"**{self.level_limit(data['level']) - data['exp']}** `EXP` until next level")
            embed.set_footer(text=f"Total Wins: {data['wins']}")
            await ctx.send(embed=embed)

    @commands.group(aliases=['sl'])
    async def skill_list(self, ctx):
        if ic(self, ctx.channel):
            return
        if not self.ready:
            return
        if ctx.invoked_subcommand is None:
            await ctx.send("Additional parameter needed")

    @skill_list.command(aliases=['-'])
    @commands.check(Control.has_control)
    async def remove_skill(self, ctx, *, name: str):
        self.skill_db.delete_one({"name": name})
        await self.update()
        await ctx.message.add_reaction(emoji='👍')

    @skill_list.command(aliases=[])
    async def basic(self, ctx):
        await self.form_data(ctx, 0x00cec9, "Basic Skills", 3, self.basic)

    @skill_list.command(aliases=[])
    async def power(self, ctx):
        await self.form_data(ctx, 0xeb2f06, "Attack Skills", 0, self.active)

    @skill_list.command(aliases=[])
    async def passive(self, ctx):
        await self.form_data(ctx, 0x1dd1a1, "Passive Skills", 1, self.passive)

    @skill_list.command(aliases=[])
    async def special(self, ctx):
        await self.form_data(ctx, 0x5f27cd, "Special Skills", 2, self.special)

    @skill_list.command(aliases=['+basic'])
    @commands.check(Control.has_control)
    async def add_basic(self, ctx, name: str, mode: int, desc: str):
        await self.insert_skill(ctx, ty=3, name=name, desc=desc, mode=mode, v4=100.0, cost=5)

    @skill_list.command(aliases=['+power'])
    @commands.check(Control.has_control)
    async def add_power(self, ctx, name: str, desc: str, mode: int, dmg: float, special: int = None):
        cost = 0
        energy = 0
        if special:
            if special == 0:
                cost += 10
                energy += 25
            elif special == 1:
                cost += 20
                energy += 30
            elif special == 2:
                cost -= 10
                energy -= 20
            elif special == 3:
                cost -= 15
                energy -= 30
        cost += int(round(dmg / 7))
        energy += int(round(dmg / 2))
        await self.insert_skill(ctx, ty=0, name=name, desc=desc, mode=mode, cost=cost, v0=energy, v1=special,
                                v4=dmg)

    @skill_list.command(aliases=['+passive'])
    @commands.check(Control.has_control)
    async def add_passive(self, ctx, name: str, desc: str, mode: int, sp: int, val: float, addition: int = None):
        await self.insert_skill(ctx, name=name, cost=sp, desc=desc, v4=val, mode=mode, v0=addition, ty=1)

    @skill_list.command(aliases=['+special'])
    @commands.check(Control.has_control)
    async def add_special(self, ctx, name: str, desc: str, sp: int, mode: int, val: float = None, ex: int = None):
        await self.insert_skill(ctx, name=name, cost=sp, desc=desc, mode=mode, v0=ex, v4=val, ty=2)

    @commands.group(aliases=['ul'])
    @commands.check(Control.has_control)
    async def user_level(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Additional parameter needed")

    @user_level.command(aliases=['-'])
    async def delete(self, ctx, target: int):
        self.lv_db.delete_one({"user_id": target})
        await ctx.message.add_reaction(emoji='👍')

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.channel.type == discord.ChannelType.private:
            return

        person_id = message.author.id
        if person_id not in self.cooldown:
            try:
                if self.last_msg[message.author.id] == message.content:
                    return
            except KeyError:
                pass

            await self.boost(message.channel, message.author)

            self.last_msg[person_id] = message.content
            self.cooldown.append(person_id)
            await asyncio.sleep(self.time)
            self.cooldown.remove(person_id)

    @commands.command()
    async def learn(self, ctx, *, name: str):
        if ic(self, ctx.channel):
            return
        data = self.lv_db.find_one({"user_id": ctx.author.id})
        skill = Skill.find(name, self.all)
        if not data:
            await ctx.send("You have not begin your adventure yet I see. Try again later.")
            return
        if not skill:
            await ctx.send("Such skill don't exist.")
            return
        if skill.name in data['skills']:
            await ctx.send(f"You already learned **{name}**.")
            return
        if data['sp'] < skill.cost:
            await ctx.send(f"You have `{data['sp']}` SP while learning **{name}** will cost {skill.cost} SP.")
            return

        learnt = data['skills']
        learnt.append(name)
        cal = data['sp'] - skill.cost

        msg = await ctx.send(content=f"You sure you want to learn this skill?\nYour current SP: **{data['sp']}**\n"
                                     f"SP after: **{cal}**",
                             embed=skill.to_embed())

        for i in self.symbols:
            await msg.add_reaction(emoji=i)

        def check(reaction1, user1):
            if (reaction1.message.id == msg.id) and (user1.id == ctx.author.id):
                if str(reaction.emoji) in self.symbols:
                    return True

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=20, check=check)
        except asyncio.TimeoutError:
            await msg.edit(embed=None, content="Timed out")
        else:
            if reaction.emoji == '✅':
                self.lv_db.update_one({"user_id": ctx.author.id}, {"$set": {"skills": learnt, "sp": cal}})
                await msg.edit(
                    content=f"{ctx.author.mention} learned `{name}`!\n SP: {data['sp']} ▶ {cal}", embed=None
                )
            else:
                await msg.edit(embed=None, content="Action cancelled")

        await msg.clear_reactions()

    async def get_response(self, ctx, time: int):
        def check(m):
            return m.author.id == ctx.author.id and m.channel == ctx.channel

        try:
            return await self.bot.wait_for('message', check=check, timeout=time)
        except asyncio.TimeoutError:
            pass
            # nothing happens, it will be None

    @commands.command()
    @commands.guild_only()
    async def challenge(self, ctx, target: discord.Member):
        if ic(self, ctx.channel, True):
            return
        if ctx.author.bot or ctx.author.id == target.id:
            await ctx.send("Whut")
            return
        if target.bot:
            await ctx.send(f"{ctx.author.mention} challenged a tin can... Nothing happened.")
            return
        temp = f"{target.mention}! {ctx.author} have challenged you to a duel, do you accept?"
        data1 = self.lv_db.find_one({"user_id": ctx.author.id})
        data2 = self.lv_db.find_one({"user_id": target.id})
        if not data2:
            await ctx.send("Don't go attack random citizens!")
            return
        if not data1:
            await ctx.send("Where is your weapon?")
            return
        if (int(data1['level']) - int(data2['level'])) >= 10:
            temp += f"\n\n||{ctx.author} seem to be more powerful than you, you still want to accept?||"
        msg = await ctx.send(temp)
        for i in self.symbols:
            await msg.add_reaction(emoji=i)

        def check(reaction1, user1):
            return reaction1.emoji in self.symbols and user1.id == target.id

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30, check=check)
        except asyncio.TimeoutError:
            await msg.edit(
                content=f"Well, looks like {target.mention} isn't here, fight cancelled everyone, nothing to see here.")
            await msg.clear_reactions()
            return
        await msg.clear_reactions()
        if reaction.emoji == '❌':
            await msg.edit(content=f"{target.mention} declined {ctx.author.mention}'s challenge, fight's over.")
            return
        p1 = Player(data1, self.basic, self.active, self.passive, self.special, self.nums, ctx.author)
        p2 = Player(data2, self.basic, self.active, self.passive, self.special, self.nums, target)
        p1.data = ctx.author
        p2.data = target
        await msg.edit(content="Round 1")
        try:
            await self.battle(self, msg, p1, p2, 0, 0)
        except RecursionError:
            await msg.edit(embed=None,
                           content=f"Battle dragged on... No winner can be determined...\n+10000XP for both party")
            check1 = False
            check2 = False
            if p1.special:
                if p1.special.secret == 3:
                    check1 = True
            if p2.special:
                if p2.special.secret == 3:
                    check2 = True
            await self.boost(ctx.channel, ctx.author,
                             amount=10000 if not check1 else 10000 + 10000 * (p1.special.modifier / 100))
            await self.boost(ctx.channel, target,
                             amount=10000 if not check2 else 10000 + 10000 * (p2.special.modifier / 100))

    async def skill_menu(self, ctx):
        if ic(self, ctx.channel):
            return
        if ctx.channel.type == discord.ChannelType.private:
            return

        data = self.lv_db.find_one({"user_id": ctx.author.id})
        base = ['💗', '⚡', '💪', '👟', '💥', '⏸']
        sk = ['👊', '🗡', '📙', '🏆', '⏸']
        alt1 = base[0:4]
        r1 = base[4:6]
        if not data:
            await ctx.send("You have yet start your journey..")
        else:
            embed = self.page1(ctx, alt1, data)
            msg = await ctx.send(embed=embed, content="")
            try:
                for z in base:
                    await msg.add_reaction(emoji=z)
                r = None
                try:
                    r = await self.react_1(ctx, alt1, base, msg)
                except RecursionError:
                    await msg.edit(embed=None, content="Max action reached.")

                if r is not None:
                    if r.emoji == '⏸':
                        e = self.page1(ctx, base, self.lv_db.find_one({"user_id": ctx.author.id}), False)
                        e.set_footer(text="Static Skill Menu")
                        await msg.edit(content="", embed=e)
                    if r.emoji == '💥':
                        await msg.clear_reactions()
                        data = self.lv_db.find_one({"user_id": ctx.author.id})
                        embed = discord.Embed(
                            colour=ctx.author.colour,
                            timestamp=ctx.message.created_at,
                            title=f"{ctx.author}'s Skills"
                        )
                        embed.add_field(name="Basic Attack 👊", value=f"{data['basic']}", inline=False)
                        embed.add_field(name="Special 🏆", value=data['special'] if data['special'] else "None",
                                        inline=False)
                        embed.add_field(name="Power Attacks 🗡",
                                        value="\n".join(data['attack']) if not len(data['attack']) == 0
                                        else "None")
                        embed.add_field(name="Passives 📙",
                                        value="\n".join(data['passive']) if not len(data['passive']) == 0 else
                                        "None")
                        embed.set_footer(text="React to change the equipped skill or pause")
                        await msg.edit(content="", embed=embed)

                        for i in sk:
                            await msg.add_reaction(emoji=i)

                        def checking(reaction1, user1):
                            return reaction1.emoji in sk and user1.id == ctx.author.id

                        reaction, user = await self.bot.wait_for('reaction_add', check=checking, timeout=10)

                        if reaction.emoji == '⏸':
                            await msg.edit(embed=embed.set_footer(text="Skill menu paused."))
                        elif reaction.emoji == '👊':
                            await self.menu1(ctx, data, msg, 3, self.basic, 'basic', 'Basic Skills')
                        elif reaction.emoji == '🏆':
                            await self.menu1(ctx, data, msg, 2, self.special, 'special', 'Special Skills')
                        elif reaction.emoji == '🗡':
                            await self.menu2(ctx, data, msg, 0, self.active, 'attack', 'Power Skills')
                        elif reaction.emoji == '📙':
                            await self.menu2(ctx, data, msg, 1, self.passive, 'passive', 'Passive Skills')
            except asyncio.TimeoutError:
                await msg.edit(content="Skill menu timed out", embed=None)

            await msg.clear_reactions()

    async def react_1(self, ctx: commands.Context, base, accept, msg):
        data = self.lv_db.find_one({"user_id": ctx.author.id})

        await msg.edit(embed=self.page1(ctx, base, data))

        def check(reaction1, user1):
            return user1.id == ctx.author.id and reaction1.emoji in accept

        reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=check)

        if reaction.emoji in base:
            if data['sp'] > 0:
                table = {'💗': 0, '⚡': 1, '💪': 2, '👟': 3}
                temp = [0, 0, 0, 0]
                inc = random.randint(100, 200)
                temp[table[reaction.emoji]] += inc
                self.lv_db.update_one({"user_id": ctx.author.id},
                                      {"$set": {"hp": data['hp'] + temp[0], "mp": data['mp'] + temp[1]},
                                       "power": data['power'] + temp[2], "speed": data['speed'] + temp[3],
                                       "sp": data['sp'] - 1}
                                      )
            await reaction.remove(user)
            return await self.react_1(ctx, base, accept, msg)
        else:
            return reaction

    @staticmethod
    def page1(ctx: commands.Context, boos, data, instruct: bool = True):
        e = discord.Embed(
            colour=ctx.author.colour,
            timestamp=ctx.message.created_at
        )
        e.set_author(icon_url=ctx.author.avatar_url, name=f"{ctx.author}'s Skill Menu")
        e.add_field(name="Health 💗 ", value=f"{data['hp']}")
        e.add_field(name="Energy ⚡ ", value=f"{data['mp']}")
        e.add_field(name="Power 💪", value=f"{data['power']}")
        e.add_field(name="Speed 👟 ", value=f"{data['speed']}")
        e.set_footer(text=f"SP: {data['sp']}")
        if instruct:
            e.add_field(name="Boosts - Spend 1 SP to increase one of these points", value=" ".join(boos), inline=False)
            e.add_field(name="Other Action", value=f"💥 - Edit your skills\n ⏸ - Pause skill menu")
        return e

    async def menu1(self, ctx: commands.Context, data, msg, ty: int, par, ins: str, title: str):
        await msg.clear_reactions()
        d = []
        words = []
        for i in data['skills']:
            temp = Skill.find(i, par)
            if temp:
                d.append(temp)
                words.append(i)
        res = await self.form_data(ctx, 0xffeaa7, f"Available {title}", ty, d, True)
        res.set_footer(text=f"Enter the name of the new {ins} skill")
        await msg.edit(embed=res, Content=f"Please enter the name of the desired {ins} skill")

        def inc(mes):
            return mes.author.id == ctx.author.id

        m = await self.bot.wait_for('message', timeout=30, check=inc)

        if m.content in words:
            self.lv_db.update_one({"user_id": ctx.author.id}, {"$set": {ins: m.content}})
            await msg.edit(content=f"Updated your {ins} skill to **{m.content}**!", embed=None)
        else:
            await msg.edit(content="Unknown skill received, action cancelled.", embed=None)

    async def menu2(self, ctx, data, msg, ty: int, check_this, par: str, title: str):
        await msg.clear_reactions()
        labeling = {'1⃣': 0,
                    '2⃣': 1,
                    '3⃣': 2,
                    '4⃣': 3,
                    '5⃣': 4}
        current = data[par]
        fst = ""

        t = 0
        reacts = []
        for key in labeling:
            fst += f"{key} {current[t]}\n"
            reacts.append(key)
            t += 1

        embed = discord.Embed(
            title=f"Modify {title}",
            description=fst,
            colour=0x7ed6df
        ).set_footer(text="React to edit the skill in the slot")

        await msg.edit(content="", embed=embed)

        text = []
        ava = []
        for i in data['skills']:
            temp = Skill.find(i, check_this)
            if temp:
                if i not in current:
                    ava.append(temp)
                    text.append(i)

        if len(ava) == 0:
            await msg.edit(embed=embed.set_footer(text=f"No additional {title} available"))
            return

        for i in reacts:
            await msg.add_reaction(emoji=i)

        def checks(reaction1, user1):
            return user1.id == ctx.author.id and reaction1.emoji in reacts

        reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=checks)
        store = reaction.emoji

        def simple(m):
            return m.author.id == ctx.author.id and m.content in text

        table = await self.form_data(ctx, 0xffeaa7, f"Available {title}", ty, ava, True)
        table.set_footer(text="Enter the name you want to replace")
        await msg.edit(embed=table)
        await msg.clear_reactions()

        take = await self.bot.wait_for('message', timeout=30, check=simple)
        current[labeling[store]] = take.content
        self.lv_db.update_one({"user_id": user.id}, {"$set": {par: current}})
        await msg.edit(embed=None, content=f"{store} |=> {take.content}")

    async def form_data(self, ctx, colour, title: str, ty: int, data, ret_em: bool = False):
        if not self.ready:
            return
        if ic(self, ctx.channel):
            return

        if len(data) <= 0:
            return

        if ty == 0 or ty == 3:
            lab = {"⚔": 0,
                   "🏹": 1,
                   "✡": 2,
                   "✨": 3}
        elif ty == 1:
            lab = {"🛡": 0,
                   "⬆": 1,
                   "💖": 2,
                   "🍹": 3}
        elif ty == 2:
            lab = {
                '🔥': 0,
                '🤕': 1,
                '😇': 2,
                '🆙': 3,
                '🙅': 4
            }
        else:
            raise ValueError(f"Unsupported integer type of {ty}")

        strings = ["", "", "", "", "", "", "", "", "", ""]

        for i in data:
            strings[lab[i.mode]] += f"{i.name}\n"
        embed = discord.Embed(
            title=title,
            colour=colour
        ).set_footer(text=f"You can view more detail with {prefix(self, ctx)}skill <Skill Name>",
                     icon_url=self.bot.user.avatar_url_as(size=64))
        for key in lab:
            i = lab[key]
            if len(strings[i]):
                embed.add_field(name=key, value=strings[i])
        if ret_em:
            return embed
        else:
            await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Leveling(bot))
    print("Loaded Cog: Leveling")


def teardown(bot: commands.Bot):
    bot.remove_cog("Leveling")
    print("Unloaded Cog: Leveling")
