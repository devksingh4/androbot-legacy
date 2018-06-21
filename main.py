import discord
import sys
import os
from chatterbot import ChatBot
from discord.ext import commands

client = commands.Bot(command_prefix= '?')

token = os.environ['AndroBotKey']

chatbot = ChatBot(
  'AndroBot',
  trainer='chatterbot.trainers.ChatterBotCorpusTrainer'
)
#chatbot.train('chatterbot.corpus.english')

@client.event
async def on_ready():
  print('Logged in as: ' + client.user.name + ' ' + client.user.id)
  await client.change_presence(game=discord.Game(name='AndroBot | Use ?(command)(message) | ' + str(len(client.servers)) + ' guilds'))

@client.command()
async def ping(): 
  await client.say('Pong!')

@client.command(pass_context=True)
async def ai(ctx, *, message):
  await client.say(chatbot.get_response(message))

client.run(token)
