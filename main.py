import discord
import os
import praw
import random
import asyncio
from discord.ext import commands
from discord.ext.tasks import loop

client = commands.AutoShardedBot(command_prefix= '?')
startup_extensions = ["Music"]
debug_users = []
if __name__ == "__main__":
  for extension in startup_extensions:
    try:
      client.load_extension(extension)
    except Exception as e:
      exc = '{}: {}'.format(type(e).__name__, e)
      raise SystemExit('Failed to load extension {}\n{}'.format(extension, exc))


token = os.environ['DiscordKey']
reddit_token = os.environ['RedditKey']


reddit = praw.Reddit(client_id='ZOkK-ZCFJpcWCQ', client_secret=reddit_token, user_agent='CardNightBot by AsyncSGD', username='androstudios', check_for_async=False)
def createRandomSortedList(num, start = 1, end = 50):
    arr = []
    tmp = random.randint(start, end)

    for x in range(num):

        while tmp in arr:
            tmp = random.randint(start, end)

        arr.append(tmp)

    arr.sort()

    return arr


@client.event
async def on_ready():
  print('Logged in as: ' + str(client.user.name) + ' ' + str(client.user.id))
  global cache
  global cache_funny
  cache = [i for i in reddit.subreddit('memes').new() if not i.stickied]
  cache_funny = [i for i in reddit.subreddit('funny').new() if not i.stickied]
  activity = discord.Game(name='?help | ' + str(len(client.guilds)) + ' guilds')
  await client.change_presence(activity=activity)

@client.event
async def on_message(message):
  await client.process_commands(message)
  if str(message.author) in debug_users and str(message.author) != "andro#8686":
    await message.delete()

class Main_Commands():
  def __init__(self,client):
    self.client=client

@loop(seconds=150)
async def refreshCache():
  global cache
  global cache_funny
  cache = [i for i in reddit.subreddit('memes').new() if not i.stickied]
  cache_funny = [i for i in reddit.subreddit('funny').new() if not i.stickied]

@client.command()
async def ping(ctx):
  await ctx.send('Pong!')

@client.command()
async def clear(ctx, amount=0):
  if (amount == 0):
    await ctx.send("Please specify how many messages are to be deleted.")
  else:
    try:
      realNum = amount + 1
      await ctx.channel.purge(limit=realNum)
    except discord.errors.Forbidden:
      await ctx.send("Bot does not have neccessary permissions to delete messages.")

@client.command()
async def debuguser(ctx, user):
  author = ctx.author
  if str(author) == "andro#8686":
    if user in debug_users:
      debug_users.remove(user)
    else:
      debug_users.append(user)

@client.command()
async def meme(ctx, numMemes=1):
  """Sends a number of memes to a channel."""
  try:
    if (int(numMemes) > 20 or int(numMemes) < 1):
      await ctx.send("Please provide a reasonable number of memes")
      return
  except:
    await ctx.send("Please provide a reasonable number of memes")
    return
  x = int(numMemes)
  if len(cache) < x:
    await refreshCache()
  randomlist = createRandomSortedList(x)
  for i in randomlist:
    selectedpost = cache[i]
    if "i.redd.it" in selectedpost.url or 'imgur' in selectedpost.url:
      await ctx.send("Here is a meme from r/memes: https://reddit.com{}".format(selectedpost.permalink), embed=discord.Embed(title=selectedpost.title).set_image(url=selectedpost.url))
    else:
      await ctx.send("Here is a meme from r/memes: {} \n\n*This post is a video. Please click on the link to see the full video*".format(selectedpost.url))
    del cache[i]

@client.command()
async def poll(ctx, *args):
  """Creates a poll"""
  emojis = ['🇦', '🇧', '🇨', '🇩', '🇪', '🇫', '🇬', '🇭', '🇮', '🇯', '🇰', '🇱', '🇲', '🇳', '🇴', '🇵', '🇶', '🇷']
  if len(args) < 1:
    await ctx.send("Please provide a poll question!")
    return
  if len(args) - 1 > len(emojis):
    await ctx.send("Too many options provided! Please provide a maximum of {} options.".format(len(emojis)))
    return
  else:
    pfp = ctx.message.author.avatar_url
    if len(args) == 1:
      embed=discord.Embed(title=args[0], color=0xff0000)
      embed.set_author(name=ctx.author, icon_url=pfp)
      message = await ctx.send(embed=embed)
      reactsToAdd = ['👍', '👎']
      asyncio.gather(*map(lambda x: message.add_reaction(x), reactsToAdd))
    else:
      embed=discord.Embed(title=args[0], description="Select the emoji that corresponds with the option that you wish to vote for", color=0xff0000)
      embed.set_author(name=ctx.author, icon_url=pfp)
      opts = args[1:]
      reactsToAdd = emojis[slice(0, len(args) - 1)]
      for opt, emoji in zip(opts, reactsToAdd):
        embed.add_field(name='"{}"'.format(opt), value=emoji, inline=True)
      message = await ctx.send(embed=embed)
      asyncio.gather(*map(lambda x: message.add_reaction(x), reactsToAdd))
    return

@client.command()
async def funny(ctx, numMemes=1):
  """Sends a number of memes to a channel."""
  try:
    if (int(numMemes) > 20 or int(numMemes) < 1):
      await ctx.send("Please provide a reasonable number of posts to retrieve from r/funny")
      return
  except:
    await ctx.send("Please provide a reasonable number of posts to retrieve from r/funny")
    return
  x = int(numMemes)
  if len(cache_funny) < x:
    await refreshCache()
  randomlist = createRandomSortedList(x)
  for i in randomlist:
    selectedpost = cache_funny[i]
    if "i.redd.it" in selectedpost.url or 'imgur' in selectedpost.url:
      await ctx.send("Here is a post from r/funny: https://reddit.com{}".format(selectedpost.permalink), embed=discord.Embed(title=selectedpost.title).set_image(url=selectedpost.url))
    else:
      await ctx.send("Here is a post from r/funny: https://reddit.com{} \n\n *This post is a video. Please click on the link to see the full video*".format(selectedpost.permalink))
    del cache_funny[i]
refreshCache.start()
client.run(token)
