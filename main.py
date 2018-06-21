import discord
import sys
import os
from chatterbot import ChatBot
from discord.ext import commands
from discord import Game, Embed
import asyncio as asyncio

client = commands.Bot(command_prefix= '?')

#token = os.environ['AndroBotKey']
token1 = sys.argv[1]

chatbot = ChatBot(
  'AndroBot',
  trainer='chatterbot.trainers.ChatterBotCorpusTrainer'
)

#chatbot.train('chatterbot.corpus.english')

@client.event
async def on_ready():
  print('Logged in as: ' + client.user.name + ' ' + client.user.id)
  await client.change_presence(game=discord.Game(name='Use "?" as prefix | ?info | ' + str(len(client.servers)) + ' guilds'))


@client.command()
async def ping(): 
  await client.say('Pong!')

@client.command(pass_context=True)
async def ai(ctx, *, message):
  await client.say(chatbot.get_response(message))

@client.command(pass_context=True)
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

@client.command()
async def info():
  await client.say("AndroBot is a pet project by @AndroStudios#8686. The following commands are available: 'ai', 'ping', and 'info'")

client.run(token1)