import discord
import sys
import os
import requests
from chatterbot import ChatBot
from discord.ext import commands
from discord import Game, Embed
from discord.voice_client import VoiceClient
import asyncio as asyncio
if not discord.opus.is_loaded():
    # the 'opus' library here is opus.dll on windows
    # or libopus.so on linux in the current directory
    # you should replace this with the location the
    # opus library is located in and with the proper filename.
    # note that on windows this DLL is automatically provided for you
    discord.opus.load_opus('opus')

riot_api_key = sys.argv[2]


def __init__(self, client):
    self.client = client

class League_Of_Legends:
    """Reports statistics of players and games in League of Legends."""
    def __init__(self, client):
        self.client = client      


def setup(client):
    client.add_cog(League_Of_Legends(client))
    print('League of Legends is loaded')
