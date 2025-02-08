import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class TournamentBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        """Load cogs and perform setup when the bot starts"""
        await self.load_extension('src.tournamentbot.cogs.tournament')
        print("Tournament cog loaded")

    async def on_ready(self):
        """Called when the bot is ready"""
        print(f'{self.user} has connected to Discord!')
        print(f"Bot is in {len(self.guilds)} guild(s)")
        print("Available commands:")
        for command in self.commands:
            print(f"- !{command.name}")

    async def on_command_error(self, ctx, error):
        """Global error handler"""
        if isinstance(error, commands.errors.CommandNotFound):
            return
        await ctx.send(f"An error occurred: {str(error)}")

async def main():
    """Start the bot"""
    bot = TournamentBot()
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
