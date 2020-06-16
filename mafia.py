import discord
from discord.ext import commands
from game import Game, Player, Phase
from roles import all_roles
import json
import typing
import random
import copy

def game_only():
    async def predicate(ctx):
        if ctx.guild.id not in ctx.bot.games:
            await ctx.send('No game is currently running in this server.')
            return False
        return True
    return commands.check(predicate)

def host_only():
    async def predicate(ctx):
        game = ctx.bot.games[ctx.guild.id]
        if not game.host_id == ctx.author.id:
            await ctx.send('Only hosts can use this command.')
            return False
        return True
    return commands.check(predicate)

def player_only():
    async def predicate(ctx):
        if not ctx.bot.games[ctx.guild.id].has_player(ctx.author):
            await ctx.send('Only players can use this command.')
            return False
        return True
    return commands.check(predicate)

def game_started_only():
    async def predicate(ctx):
        game = ctx.bot.games[ctx.guild.id]
        if not game.has_started:
            await ctx.send('The game hasn\'t started yet!')
            return False
        return True
    return commands.check(predicate)

class Mafia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['create', 'create-game'])
    async def creategame(self, ctx: commands.Context):
        if ctx.guild.id in self.bot.games:
            return await ctx.send('A game of mafia is already running in this server.')
        new_game = Game(ctx.channel)
        new_game.host_id = ctx.message.author.id
        new_game.players.append(Player(ctx.author))
        self.bot.games[ctx.guild.id] = new_game
        return await ctx.send(f'Started a game of mafia in {ctx.message.channel.mention}, hosted by **{ctx.message.author}**')

    @commands.command()
    @game_only()
    async def join(self, ctx: commands.Context):
        if self.bot.games[ctx.guild.id].has_started:
            return await ctx.send('Signup phase for the game has ended')
        elif self.bot.games[ctx.guild.id].has_player(ctx.author):
            return await ctx.send('You have already joined this game')

        rolesets = json.load(open('rolesets/rolesets.json'))
        rolesets.sort(key=lambda rl: len(rl['roles']), reverse=True)

        if len(self.bot.games[ctx.guild.id].players) >= len(rolesets[0].get('roles')):
            return await ctx.send(f'Maximum amount of players reached')
        else:
            self.bot.games[ctx.guild.id].players.append(Player(ctx.message.author))
            return await ctx.send('✅ Game joined successfully')

    @commands.command()
    @game_only()
    async def leave(self, ctx: commands.Context):
        if self.bot.games[ctx.guild.id].has_started:
            return await ctx.send('Cannot leave game after signup phase has ended')
        elif not self.bot.games[ctx.guild.id].has_player(ctx.author):
            return await ctx.send('You have not joined this game')
        elif self.bot.games[ctx.guild.id].host_id == ctx.author.id:
            return await ctx.send('The host cannot leave the game.')
        else:
            players = self.bot.games[ctx.guild.id].players
            players = [pl for pl in players if not (pl.user.id == ctx.author.id)]
            self.bot.games[ctx.guild.id].players = players
            return await ctx.send('✅ Game left successfully')

    @commands.command()
    @game_only()
    async def playerlist(self, ctx: commands.Context):
        if not self.bot.games[ctx.guild.id].has_started:
            return await ctx.send(f'**Players: {len(self.bot.games[ctx.guild.id].players)}**\n'
                    + ('\n'.join([f'{i+1}. {pl.user}' for (i, pl) in
                    enumerate(self.bot.games[ctx.guild.id].players)])))

    @commands.command()
    @game_only()
    @host_only()
    async def startgame(self, ctx: commands.Context, setup: typing.Optional[str] = None):
        game = self.bot.games[ctx.guild.id]
        try:
            setup = game.find_setup(setup)
        except Exception as err:
            return await ctx.send(err)
        await ctx.send(f'Chose the setup **{setup["name"]}**. Randing roles...')
        roles = copy.deepcopy(setup['roles'])
        # shuffle roles in place and assign the nth (shuffled) role to the nth player
        random.shuffle(roles)
        async with ctx.channel.typing():
            for n, player in enumerate(game.players):
                player_role = roles[n]
                # assign role and faction to the player
                player.role = all_roles.get(player_role['id'])()
                player.faction = player_role['faction']
                # send role PMs; wip: check if the message was successfully sent
                await player.user.send(player.role_pm)
        await ctx.send('Sent all role PMs!')
        await game.increment_phase()

    @commands.command()
    @game_only()
    @game_started_only()
    @player_only()
    async def vote(self, ctx: commands.Context, target: discord.Member):
        game = self.bot.games[ctx.guild.id]
        target = [*filter(lambda pl: pl.user.id == target.id, game.players)][0]
        if not self.bot.games[ctx.guild.id].has_player(target.user):
            return await ctx.send(f'Player {target.mention} not found.')
        if target.user == ctx.author:
            return await ctx.send(f'Self-voting is not allowed.')

        for player in game.players:
            if player.has_vote(ctx.author):
                player.votes = list(filter(lambda p: p.user.id != ctx.author.id, player.votes))
                break

        target.votes.append(list(filter(lambda p: p.user.id == ctx.author.id, game.players))[0])
        await ctx.send(f'Voted {target.user.name}')

        votes_on_target = len(target.votes)
        if votes_on_target >= game.majority_votes:
            target.alive = False
            await ctx.send(f'{target.user.name} was lynched. He was a *{target.full_role}*.')
            await target.role.on_lynch(game, target)
            game_ended, winning_faction = game.check_endgame()
            if game_ended:
                # wip: need a game.end() function
                await ctx.send(f'The game is over. {winning_faction} wins! 🎉')
                rolelist = '\n'.join([f'{n+1}. {player.user} ({player.full_role})' for n, player in enumerate(game.players)])
                await ctx.send(f'**Rolelist**: ```{rolelist}```')
                del self.bot.games[ctx.guild.id]
            # change phase after this.

def setup(bot):
    bot.add_cog(Mafia(bot))
