from bs4 import BeautifulSoup
import requests
 
def getPlaylistLinks(url):
    id = url.split("&list=",1)[1] 
    r = requests.get("https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=1000&playlistId={}&key=AIzaSyBrRDCWV4Y3pAgqyA8fNTlp9mZIwbyz7vI".format(id))
    data = r.json()
    urls = []
    for item in data['items']:
        urls.append("https://youtube.com/watch?v={}".format(item['snippet']['resourceId']['videoId']))
    return urls

def isYTPlaylist(url: str):
    if url.find("&list="):
        return True
    return False