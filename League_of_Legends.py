import discord
import sys
import os
import requests
from discord.ext import commands
from discord import Game, Embed
import asyncio as asyncio

riot_api_key = sys.argv[2]


def __init__(self, client):
    self.client = client

class League_Of_Legends:
    """Reports statistics of players and games in League of Legends."""
    def __init__(self, client):
        self.client = client     

    @commands.command(pass_context=True)
    async def lolplayerlevel(self, ctx, summoner_name):
        """Show the level of the summoner name that is entered"""
        await self.client.say("This feature has not yet been implemented")
    


def setup(client):
    client.add_cog(League_Of_Legends(client))
    print('League of Legends is loaded')