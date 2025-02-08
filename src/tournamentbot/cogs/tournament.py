import discord
from discord.ext import commands, tasks
from typing import List, Dict, Set
import asyncio
import random
from datetime import datetime, timedelta
from ..utils.visualizer import create_bracket_view, format_for_discord

class Tournament(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_tournaments: Dict[int, Dict] = {}
        self.check_tournaments.start()
        self.voters: Dict[int, Dict[int, Set[int]]] = {}  # guild_id -> {message_id -> set(user_ids)}

    def cog_unload(self):
        self.check_tournaments.cancel()
        # Clean up active tournaments
        for guild_id in list(self.active_tournaments.keys()):
            asyncio.create_task(
                self.active_tournaments[guild_id]["thread"].send("Bot restarting, tournament cancelled.")
            )
        self.active_tournaments.clear()

    @commands.command(name="tournament")
    @commands.has_permissions(manage_channels=True)
    async def create_tournament(self, ctx):
        """Start a new channel tournament"""
        if ctx.guild.id in self.active_tournaments:
            await ctx.send("A tournament is already running in this server!")
            return

        # Create tournament thread
        thread = await ctx.channel.create_thread(
            name=f"Channel Tournament {datetime.now().strftime('%Y-%m-%d')}",
            type=discord.ChannelType.public_thread
        )

        # Get eligible channels (text channels only)
        channels = [ch for ch in ctx.guild.channels 
                    if isinstance(ch, discord.TextChannel) and ch.permissions_for(ctx.guild.me).view_channel]
        
        if len(channels) < 2:
            await ctx.send("Not enough channels to create a tournament!")
            return

        # Randomize order and create initial match-ups only.
        random.shuffle(channels)
        initial_round = self._create_initial_bracket(channels)

        tournament_data = {
            "thread": thread,
            "rounds": [initial_round],  # Only the first round is pre-generated.
            "current_round": 0,
            "current_matches": [],
            "start_time": datetime.now(),
        }
        
        self.active_tournaments[ctx.guild.id] = tournament_data
        
        # Start first round
        await self._start_round(ctx.guild.id)
        await ctx.send(f"Tournament started! Follow the progress in {thread.mention}")

    @commands.command(name="status")
    async def tournament_status(self, ctx):
        """Show current tournament status"""
        if ctx.guild.id not in self.active_tournaments:
            await ctx.send("No active tournament in this server.")
            return
            
        tournament = self.active_tournaments[ctx.guild.id]
        await ctx.send(
            f"Round {tournament['current_round'] + 1}\n"
            f"Time remaining: {timedelta(days=1) - (datetime.now() - tournament['start_time'])}\n"
            f"Active matches: {len(tournament['current_matches'])}"
        )

    @commands.command(name="cancel")
    @commands.has_permissions(manage_channels=True)
    async def cancel_tournament(self, ctx):
        """Cancel the current tournament"""
        if ctx.guild.id not in self.active_tournaments:
            await ctx.send("No active tournament to cancel.")
            return
            
        await self.active_tournaments[ctx.guild.id]["thread"].send("Tournament cancelled by administrator.")
        del self.active_tournaments[ctx.guild.id]
        await ctx.send("Tournament cancelled.")

    @commands.command(name="bracket")
    async def show_bracket(self, ctx):
        """Show the current tournament bracket"""
        if ctx.guild.id not in self.active_tournaments:
            await ctx.send("No active tournament in this server.")
            return

        # Generate bracket visualization using your custom visualizer.
        bracket_lines = create_bracket_view(self.active_tournaments[ctx.guild.id])
        messages = format_for_discord(bracket_lines)
        
        await ctx.send(messages[0])
        if len(messages) > 1:
            for msg in messages[1:]:
                await ctx.channel.send(msg)

    @commands.command(name="testbot")
    async def test_bot_permissions(self, ctx):
        """Test if the bot can properly handle reactions"""
        try:
            # Send test message
            test_msg = await ctx.send("🔄 Testing bot permissions... React with ✅ to test")
            await test_msg.add_reaction("✅")
            
            # Wait 5 seconds
            await asyncio.sleep(5)
            
            # Fetch fresh message to get reactions
            test_msg = await ctx.channel.fetch_message(test_msg.id)
            reaction_count = next((r.count for r in test_msg.reactions if str(r.emoji) == "✅"), 0)
            
            # Report results
            await ctx.send(
                f"📊 Test Results:\n"
                f"- Can add reactions: ✅\n"
                f"- Can read reactions: ✅ ({reaction_count} reactions found)\n"
                f"- Bot is working correctly: {'✅' if reaction_count > 0 else '❌'}"
            )

        except discord.HTTPException as e:
            await ctx.send(f"❌ Test failed: {str(e)}")
        except Exception as e:
            await ctx.send(f"❌ Unexpected error: {str(e)}")

    async def _start_round(self, guild_id: int):
        """Start a new round of matches"""
        tournament = self.active_tournaments[guild_id]
        current_round = tournament["rounds"][tournament["current_round"]]
        
        await tournament["thread"].send(f"📢 Round {tournament['current_round'] + 1} starting!")
        
        self.voters[guild_id] = {}
        
        for match in current_round:
            # If an opponent is missing, automatically advance the channel.
            if match[1] is None:
                tournament["current_matches"].append({"message": None, "channels": match})
                await tournament["thread"].send(f"Auto-advance {match[0].mention} (no opponent)")
                continue
                
            try:
                poll_msg = await tournament["thread"].send(
                    f"🏆 **Match:** {match[0].mention} VS {match[1].mention}\n"
                    f"React with 1️⃣ for {match[0].name} or 2️⃣ for {match[1].name}"
                )
                await poll_msg.add_reaction("1️⃣")
                await poll_msg.add_reaction("2️⃣")
                tournament["current_matches"].append({"message": poll_msg, "channels": match})
                self.voters[guild_id][poll_msg.id] = set()
            except discord.HTTPException as e:
                await tournament["thread"].send(f"Error creating match: {e}")
                continue

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # Ignore the bot's own reactions.
        if payload.user_id == self.bot.user.id:
            return

        if payload.guild_id not in self.voters:
            return
            
        guild_voters = self.voters[payload.guild_id]
        if payload.message_id not in guild_voters:
            return
            
        # If the user has already voted on this poll, remove the extra reaction.
        if payload.user_id in guild_voters[payload.message_id]:
            try:
                channel = self.bot.get_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
                await message.remove_reaction(payload.emoji, payload.member)
            except discord.HTTPException:
                pass
            return
            
        guild_voters[payload.message_id].add(payload.user_id)

    @tasks.loop(minutes=5)
    async def check_tournaments(self):
        """Periodically check if the current round should end and process its results"""
        for guild_id, tournament in list(self.active_tournaments.items()):
            # For testing purposes, we use a 10-second round duration.
            if datetime.now() - tournament["start_time"] >= timedelta(days=1):
                await self._end_round(guild_id)

    async def _end_round(self, guild_id: int):
        tournament = self.active_tournaments[guild_id]
        winners = []
        min_votes = 1  # For testing; adjust this threshold for production use.

        # Process all matches in the current round.
        for match in tournament["current_matches"]:
            try:
                # If there was no poll (i.e., no opponent), the channel advances automatically.
                if match["message"] is None:
                    winners.append(match["channels"][0])
                    continue

                msg = await match["message"].channel.fetch_message(match["message"].id)
                votes_1 = 0
                votes_2 = 0

                for reaction in msg.reactions:
                    if str(reaction.emoji) == "1️⃣":
                        # Subtract the bot's initial reaction.
                        votes_1 = reaction.count - 1
                    elif str(reaction.emoji) == "2️⃣":
                        votes_2 = reaction.count - 1

                await tournament["thread"].send(
                    f"📊 Results for {match['channels'][0].name} vs {match['channels'][1].name}:\n"
                    f"{match['channels'][0].name}: {votes_1} votes\n"
                    f"{match['channels'][1].name}: {votes_2} votes"
                )

                if votes_1 >= min_votes or votes_2 >= min_votes:
                    if votes_1 > votes_2:
                        winners.append(match["channels"][0])
                    elif votes_2 > votes_1:
                        winners.append(match["channels"][1])
                    else:
                        # Tie-breaker: randomly select a winner.
                        winner = random.choice([match["channels"][0], match["channels"][1]])
                        winners.append(winner)
                        await tournament["thread"].send(
                            f"⚖ Tie detected. Randomly selected {winner.mention} as the winner of this match."
                        )
                else:
                    winner = random.choice([match["channels"][0], match["channels"][1]])
                    winners.append(winner)
                    await tournament["thread"].send(
                        f"⏱ Neither channel received the minimum votes. Randomly selected {winner.mention} as the winner."
                    )

            except discord.HTTPException as e:
                await tournament["thread"].send(f"Error processing match: {e}")
                winners.append(random.choice([match["channels"][0], match["channels"][1]]))

        await tournament["thread"].send("\n🏁 Round Complete! Winners:")
        for winner in winners:
            if winner is not None:
                await tournament["thread"].send(f"✨ {winner.mention}")
            else:
                await tournament["thread"].send("✨ No winner (invalid match)")

        # Check if the tournament is over.
        if len(winners) == 1:
            await tournament["thread"].send(f"🎉 Tournament Winner: {winners[0].mention}! 🎉")
            del self.active_tournaments[guild_id]
        else:
            # Generate the next round from current winners.
            winners_copy = winners.copy()
            random.shuffle(winners_copy)  # Shuffle winners to prevent fixed bracket ordering
            next_round = []
            while winners_copy:
                if len(winners_copy) >= 2:
                    next_round.append((winners_copy.pop(0), winners_copy.pop(0)))
                else:
                    next_round.append((winners_copy.pop(0), None))
            tournament["rounds"].append(next_round)
            tournament["current_round"] += 1
            tournament["start_time"] = datetime.now()
            tournament["current_matches"] = []
            await self._start_round(guild_id)

    def _create_initial_bracket(self, channels: List[discord.TextChannel]) -> List[tuple]:
        """
        Create match-ups for the initial round.
        Pairs channels and auto-advances the last channel if the count is odd.
        """
        matches = []
        for i in range(0, len(channels), 2):
            if i + 1 < len(channels):
                matches.append((channels[i], channels[i + 1]))
            else:
                matches.append((channels[i], None))
        return matches

    @check_tournaments.before_loop
    async def before_check_tournaments(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Tournament(bot))