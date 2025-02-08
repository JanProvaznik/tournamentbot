import asyncio
import os
from aiohttp import web
from .bot import TournamentBot, TOKEN

async def healthcheck(request):
    """Health check endpoint for Azure"""
    return web.Response(text="Bot is running!")

async def run_bot():
    """Run the Discord bot"""
    bot = TournamentBot()
    try:
        async with bot:
            await bot.start(TOKEN)
    except Exception as e:
        print(f"Bot error: {e}")
        raise

async def run_webserver():
    """Run the web server for Azure health checks"""
    app = web.Application()
    app.router.add_get('/', healthcheck)
    app.router.add_get('/health', healthcheck)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 80)))
    
    try:
        await site.start()
        print(f"Web server running on port {os.environ.get('PORT', 80)}")
        # Keep the server running
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour
    except Exception as e:
        print(f"Web server error: {e}")
        raise

async def main():
    """Run both the bot and web server"""
    tasks = [
        asyncio.create_task(run_webserver()),
        asyncio.create_task(run_bot())
    ]
    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        print(f"Fatal error: {e}")
        for task in tasks:
            if not task.done():
                task.cancel()
        raise

if __name__ == '__main__':
    asyncio.run(main())