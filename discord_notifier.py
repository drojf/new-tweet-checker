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
                logging.info("Checking for new tweets...")
                tweet_scan_result = tweet_scanner.scan_for_tweets_as_url()
                if tweet_scan_result:
                    # Ensure message stay below 2000 character limit by sending max 3 URLs at a time
                    # Discord will only preview 5 urls at a time, so send 3 at a time to be safe.
                    # Also add a delay as sending too quickly may make previews fail to appear.
                    urls_to_send = []
                    first_message = True
                    for i, tweet_id in enumerate(tweet_scan_result):
                        urls_to_send.append(tweet_id)
                        if len(urls_to_send) >= 3:
                            await self.send_urls(channel, urls_to_send, notify=first_message, delay=3)
                            urls_to_send = []
                            first_message = False

                    if urls_to_send:
                        await self.send_urls(channel, urls_to_send, notify=first_message, delay=3)

                    # Only save if all tweets were successfully sent
                    tweet_scanner.save()
                else:
                    logging.info("No new tweets.")

                await asyncio.sleep(MyClient.POLL_INTERVAL)

            tweet_scanner.close()
        except Exception as e:
            logging.error("Error:", e)

    async def send_urls(self, channel, urls, notify=False, delay=None):
        # role id needs @& instead of just @
        tweet_urls_string = "\n".join(urls)

        header = ''
        if notify:
            header = f'New Tweets for <@&{self.role_id_to_ping}>:\n'

        message = f'{header}{tweet_urls_string}\n'
        logging.info(f'Sending {message}')
        await channel.send(message)

        if delay:
            await asyncio.sleep(delay)



logging.basicConfig(
    format='%(asctime)s %(levelname)-8s: %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

with open('discord_settings.json', 'rb') as json_settings:
    settings = json.load(json_settings)
    discord_bot_token = settings['discord_bot_token']
    channel_id_to_ping = settings['channel_id_to_ping']
    role_id_to_ping = settings['role_id_to_ping']

client = MyClient(channel_id_to_ping, role_id_to_ping)
client.run(discord_bot_token)
