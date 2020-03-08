import json
import asyncio
import logging
import discord


class MyClient(discord.Client):
    def __init__(self, channel_id_to_ping, role_id_to_ping, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.role_id_to_ping = role_id_to_ping
        self.channel_id_to_ping = channel_id_to_ping

        self.bg_task = self.loop.create_task(self.my_background_task())

    async def on_ready(self):
        logging.info(f'Logged in as {self.user.name} ({self.user.id})')

    async def my_background_task(self):
        await self.wait_until_ready()
        channel = self.get_channel(self.channel_id_to_ping)
        while not self.is_closed():
            message = f'Hello, <@&{self.role_id_to_ping}>'  # role id needs @& instead of just @
            logging.info(f'Sending {message}')
            await channel.send(message)
            await asyncio.sleep(60)

        logging.info("Background task terminated")


logging.basicConfig(level=logging.INFO)

with open('discord_settings.json', 'rb') as json_settings:
    settings = json.load(json_settings)
    discord_bot_token = settings['discord_bot_token']
    channel_id_to_ping = settings['channel_id_to_ping']
    role_id_to_ping = settings['role_id_to_ping']

client = MyClient(channel_id_to_ping, role_id_to_ping)
client.run(discord_bot_token)
