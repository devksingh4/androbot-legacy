import discord
import sys
import os
import praw
import random
import requests
from chatterbot import ChatBot
from discord.ext import commands
from discord import Game, Embed
from discord.voice_client import VoiceClient
import asyncio as asyncio

client = commands.Bot(command_prefix= '?')
startup_extensions = ["Music"]

if __name__ == "__main__":
  for extension in startup_extensions:
    try:
      client.load_extension(extension)
    except Exception as e:
      exc = '{}: {}'.format(type(e).__name__, e)
      raise SystemExit('Failed to load extension {}\n{}'.format(extension, exc))
      

token = os.environ['DiscordKey']
reddit_token = os.environ['RedditKey']
chatbot = ChatBot(
  'AndroBot',
  trainer='chatterbot.trainers.ChatterBotCorpusTrainer'
)

reddit = praw.Reddit(client_id='g1XQ6v0haLlPqA', client_secret=reddit_token, user_agent='AndroBot by AndroStudios', username='PCLover1')

#chatbot.train('chatterbot.corpus.english')

@client.event
async def on_ready():
  print('Logged in as: ' + client.user.name + ' ' + client.user.id)
  await client.change_presence(game=discord.Game(name='?help | ' + str(len(client.servers)) + ' guilds'))

class Main_Commands():
  def __init__(self,client):
    self.client=client

@client.command()
async def ping(): 
  await client.say('Pong!')
  print(reddit.user.me())

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

@client.command(pass_context=True)
async def meme(ctx):
  meme_options = reddit.subreddit('memes').hot()
  selectedpostnum = random.randint(1,25)
  for i in range(0, selectedpostnum):
    selectedpost = next(x for x in meme_options if not x.stickied)
  await client.say("Here is a random meme: " + selectedpost.url)

client.run(token1)
  