from discord import Embed, utils
from discord.ext import commands

from .utils.checks import is_owner
from .utils.var import Sid, Cid


class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    ########################################################################
    # ######COLOUR ROLES####################################################
    ########################################################################

    def get_all_colour_roles(self):
        guild = self.bot.get_guild(Sid.alu)
        count_role = 0
        colour_array = []
        for item in guild.roles:
            if item.name == 'Colour: Black':
                count_role = 1

            if count_role == 1:
                colour_array.append(item)

            if item.name == 'Colour: LightPink':
                count_role = 0
        colour_array.reverse()
        return colour_array

    @is_owner()
    @commands.command(hidden=True)
    async def trigger(self, ctx, *, arg):
        # guild = self.bot.get_guild(Sid.alu)
        colour_array = self.get_all_colour_roles()

        arg = arg.split(' ')
        start = int(arg[0])
        amount = int(arg[1])
        emoji_array = arg[2:2 + amount]
        text = ''  # .join(arg[2+amount:]) + '\n\n'
        for i, (emoji, role) in enumerate(zip(emoji_array, colour_array[start:start + amount]), start=start+1):
            text += f'{i}. {emoji} - {role.mention}\n'

        embed = Embed(colour=0x9678b6)
        embed.title = f'Colour roles №{start + 1}-{start + amount}'
        msg = await ctx.reply(content=text, embed=embed)
        for emoji in emoji_array:
            await msg.add_reaction(emoji)

    @is_owner()
    @commands.command(hidden=True)
    async def edit_the_trigger(self, ctx):
        guild = self.bot.get_guild(Sid.alu)
        react_channel = guild.get_channel(Cid.roles)
        for msg_id in dict_reactions:
            if dict_reactions[msg_id] == 2:
                msg = await react_channel.fetch_message(msg_id)
                array = [f'{counter}. {item}' for counter, item in enumerate(msg.content.split('\n'), start=1)]
                answer = '\n'.join(array)
                #  print(answer)
                embed = msg.embeds[0]
                await msg.edit(content=answer, embed=embed)

    ########################################################################
    # ###### RANDOM ROLES###################################################
    ########################################################################
    def get_roles_by_mentions(self, roles_mentions):
        guild = self.bot.get_guild(Sid.alu)
        roles_array = []
        for item in guild.roles:
            if item.mention in roles_mentions:
                roles_array.append(item)
        roles_array.reverse()
        return roles_array

    @is_owner()
    @commands.command(hidden=True)
    async def trigger_non(self, ctx, *, arg):
        guild = self.bot.get_guild(Sid.alu)

        arg = arg.split(' ')
        start = int(arg[0])
        amount = int(arg[1])
        roles_names = arg[2:2 + amount]
        roles_array = self.get_roles_by_mentions(roles_names)
        emoji_array = arg[2 + amount:2 + amount + amount]

        text = ''
        for emoji, role in zip(emoji_array, roles_array[start:start + amount]):
            text += '{} - {}\n'.format(emoji, role.mention)

        embed = Embed(colour=0x9678b6)
        embed.title = ' '.join(arg[2 + 2 * amount:])
        msg = await ctx.reply(content=text, embed=embed)
        for emoji in emoji_array:
            await msg.add_reaction(emoji)

    ########################################################################
    ########################################################################
    ########################################################################
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        guild = self.bot.get_guild(Sid.alu)
        react_channel = guild.get_channel(Cid.roles)
        msg_id = payload.message_id
        if msg_id in dict_reactions.keys():
            unique = dict_reactions[msg_id]

            async def work_wtf(msg_id, payload, guild, react_channel, unique):
                msg = await react_channel.fetch_message(msg_id)
                member = guild.get_member(payload.user_id)

                for counter in range(len(msg.reactions)):
                    reaction = msg.reactions[counter]
                    reaction_role_id = msg.raw_role_mentions[counter]
                    reaction_role = utils.get(guild.roles, id=reaction_role_id)
                    # print(member.name, reaction_role, reaction.emoji, payload.emoji)
                    if str(reaction.emoji) == str(payload.emoji) and reaction_role not in member.roles:
                        await member.add_roles(reaction_role)

                    if unique > 0 and str(reaction.emoji) != str(payload.emoji) and reaction_role in member.roles:
                        await msg.remove_reaction(reaction, member)
                        await member.remove_roles(reaction_role)

            await work_wtf(msg_id, payload, guild, react_channel, unique)
            if unique > 1:
                for item in dict_reactions:
                    if dict_reactions[item] == unique:
                        await work_wtf(item, payload, guild, react_channel, unique)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        guild = self.bot.get_guild(Sid.alu)
        react_channel = guild.get_channel(Cid.roles)
        msg_id = payload.message_id
        if msg_id in dict_reactions.keys():
            msg = await react_channel.fetch_message(msg_id)
            member = guild.get_member(payload.user_id)

            for counter in range(len(msg.reactions)):
                reaction = msg.reactions[counter]
                reaction_role_id = msg.raw_role_mentions[counter]
                reaction_role = utils.get(guild.roles, id=reaction_role_id)
                # print(reaction.emoji, payload.emoji.name)
                if str(reaction.emoji) == str(payload.emoji) and reaction_role in member.roles:
                    await member.remove_roles(reaction_role)


# 0 - non unique, 1 - unique, 2+ means it is grouped msg reactions and the number corresponds to that group

# 2 = colour roles
dict_reactions = {
    796646234730266654: 2,  # 1-20
    796646679973068820: 2,  # 21
    796647694834728970: 2,  # 41
    796648135031390238: 2,  # 61
    796648708364173363: 2,  # 81
    796649034458071090: 2,  # 101-120
    796649424536731688: 2,  # 121-140
    796650517463695370: 0,  # games
    796651600126279721: 0,  # notifications
    851798601960259604: 0,  # pronoun roles
}  # msg_id: unique reactions


async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
