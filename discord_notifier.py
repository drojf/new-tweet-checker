import json
import asyncio
import logging
import discord
from main import TweetScanner


class MyClient(discord.Client):
    POLL_INTERVAL = 60 * 60 / 2 # poll every 30 minutes

    def __init__(self, channel_id_to_ping, role_id_to_ping, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.role_id_to_ping = role_id_to_ping
        self.channel_id_to_ping = channel_id_to_ping

        self.bg_task = self.loop.create_task(self.my_background_task())

    async def on_ready(self):
        logging.info(f'Logged in as {self.user.name} ({self.user.id})')

    async def my_background_task(self):
        try:
            logging.info("Background task started")
            tweet_scanner = TweetScanner()
            await self.wait_until_ready()
            channel = self.get_channel(self.channel_id_to_ping)
            while not self.is_closed():
                tweet_scan_result = tweet_scanner.scan_for_tweets()
                if tweet_scan_result is not None:
                    # role id needs @& instead of just @
                    message = f'New Tweets for <@&{self.role_id_to_ping}>:\n{tweet_scan_result}\n'
                    logging.info(f'Sending {message}')
                    await channel.send(message)

                await asyncio.sleep(MyClient.POLL_INTERVAL)

            tweet_scanner.close()
        except Exception as e:
            logging.error("Error:", e)


logging.basicConfig(level=logging.INFO)

with open('discord_settings.json', 'rb') as json_settings:
    settings = json.load(json_settings)
    discord_bot_token = settings['discord_bot_token']
    channel_id_to_ping = settings['channel_id_to_ping']
    role_id_to_ping = settings['role_id_to_ping']

client = MyClient(channel_id_to_ping, role_id_to_ping)
client.run(discord_bot_token)
