import discord
from discord import TextChannel
import sys
import os
import praw
import random
import requests
from discord.ext import commands
from discord import Game, Embed
from discord.voice_client import VoiceClient
import asyncio as asyncio

client = commands.AutoShardedBot(command_prefix= '?')
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


reddit = praw.Reddit(client_id='ZOkK-ZCFJpcWCQ', client_secret=reddit_token, user_agent='CardNightBot by AsyncSGD', username='androstudios')


@client.event
async def on_ready():
  print('Logged in as: ' + str(client.user.name) + ' ' + str(client.user.id))
  activity = discord.Game(name='?help | ' + str(len(client.guilds)) + ' guilds')
  await client.change_presence(activity=activity)
class Main_Commands():
  def __init__(self,client):
    self.client=client

@client.command()
async def ping(ctx): 
  await ctx.send('Pong!')

@client.command()
async def clear(ctx, amount=0):
  if (amount == 0):
    await ctx.send("Please specify how many messages are to be deleted.")
  else:
    await ctx.channel.purge(limit=amount)
    await ctx.send("Messages Cleared")

@client.command()
async def meme(ctx, numMemes=None):
  if (numMemes > 10 or numMemes < 0):
        await ctx.send("Please ask for a reasonable number of memes.")
        return
  if numMemes == None:
    meme_options = reddit.subreddit('memes').new()
    selectedpostnum = random.randint(1,25)
    for i in range(0, selectedpostnum):
      selectedpost = next(x for x in meme_options if not x.stickied)
    e = discord.Embed(title="Random meme").set_image(url=selectedpost.url)
    await ctx.send("Here is a random meme: ", embed=e)
  else:
    x = int(numMemes)
    used = []
    while x > 0: 
      meme_options = reddit.subreddit('memes').new()
      selectedpostnum = random.randint(1,25)
      while selectedpostnum in used:
        selectedpostnum = random.randint(1,25)
      used.append(selectedpostnum)
      for i in range(0, selectedpostnum):
        selectedpost = next(x for x in meme_options if not x.stickied)
      e = discord.Embed(title="Random meme").set_image(url=selectedpost.url)
      await ctx.send("Here is meme #{}: ".format(str(x-numMemes)), embed=e)
      x -= 1

client.run(token)
