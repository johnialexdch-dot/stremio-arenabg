from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
import requests
import urllib.parse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_URL = "https://zamunda.net"

def search_torrents(query):
    search_url = f"{BASE_URL}/search?q={urllib.parse.quote_plus(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": BASE_URL
    }
    resp = requests.get(search_url, headers=headers)
    return resp.text

def get_magnet_link(torrent_url):
    resp = requests.get(torrent_url)
    soup = BeautifulSoup(resp.text, "html.parser")
    a = soup.find("a", href=lambda h: h and h.startswith("magnet:"))
    return a["href"] if a else ""

@app.get("/catalog/{type}/{id}.json")
def catalog(type: str, id: str, search: str = ""):
    if id != "zamunda_catalog" or not search:
        return {"metas": []}

    html = search_torrents(search)
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("tr.torrent")  # коригирай според структурата на сайта

    metas = []
    for row in rows[:20]:
        a_tag = row.find("a", class_="torrentname")  # коригирай според html
        if not a_tag:
            continue
        title = a_tag.text.strip()
        href = a_tag["href"]
        full_url = urllib.parse.urljoin(BASE_URL, href)
        metas.append({
            "id": full_url,
            "name": title,
            "type": type,
            "poster": "https://zamunda.net/favicon.ico"
        })

    return {"metas": metas}

@app.get("/stream/{type}/{id}.json")
def stream(type: str, id: str):
    magnet = get_magnet_link(id)
    if not magnet:
        return {"streams": []}

    info_hash = ""  # можеш да ползваш същата функция за извличане

    return {
        "streams": [{
            "title": "Zamunda",
            "infoHash": info_hash,
            "fileIdx": 0,
            "url": magnet
        }]
    }
