import discord
import sys
import os
import requests
from chatterbot import ChatBot
from discord.ext import commands
from discord import Game, Embed
import asyncio as asyncio

chatbot = ChatBot(
  'AndroBot',
  trainer='chatterbot.trainers.ChatterBotCorpusTrainer'
)

#chatbot.train('chatterbot.corpus.english')

def __init__(self, client):
    self.client = client

class General:
    def __init__(self,client):
        self.client=client

    @commands.command(self,pass_context=True)
    async def ping(self): 
        await client.say('Pong!')

    @commands.command(self, pass_context=True)
    async def ai(ctx, *, message):
        await client.say(chatbot.get_response(message))

    @commands.command(self, pass_context=True)
    async def clear(ctx, amount=0):
        channel = ctx.message.channel
        if (amount == 0):
            client.say("Please specify how many messages are to be deleted.")
        else:
            amount += 1
            messages = []
        async for message in client.logs_from(channel, limit=int(amount)):
            messages.append(message)
        await client.delete_messages(messages)
        await client.say("Messages Cleared")



def setup(client):
    client.add_cog(General(client))
    print('General is loaded')