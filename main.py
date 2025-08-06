from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
import requests
import urllib.parse
from urllib.parse import parse_qs, urlparse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # за тестове, после смени на нужните домейни
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_URL = "https://zamunda.net"
LOGIN_URL = f"{BASE_URL}/login.php"

ZAMUNDA_USERNAME = "coyec75395"        # смени с твоя потребител
ZAMUNDA_PASSWORD = "rxM6N.h2N4aYe7_"  # смени с твоята парола

class ZamundaSession:
    def __init__(self, username, password):
        self.session = requests.Session()
        self.username = username
        self.password = password
        self.login_url = LOGIN_URL

    def login(self):
        payload = {
            "username": self.username,
            "password": self.password,
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": self.login_url
        }
        resp = self.session.post(self.login_url, data=payload, headers=headers)
        print(f"Login response status: {resp.status_code}")
        print(f"Login response URL: {resp.url}")
        print(f"Login response text snippet: {resp.text[:500]}")

        if self.username.lower() in resp.text.lower():
            print("✅ Успешен вход в Zamunda")
            return True
        else:
            print("❌ Неуспешен вход в Zamunda")
            return False

    def search_torrents(self, query):
        search_url = f"{BASE_URL}/search.php?szukaj={urllib.parse.quote_plus(query)}"
        resp = self.session.get(search_url)
        return resp.text

zamunda = ZamundaSession(ZAMUNDA_USERNAME, ZAMUNDA_PASSWORD)
logged_in = zamunda.login()

def extract_info_hash(magnet_link):
    try:
        xt = parse_qs(urlparse(magnet_link).query).get("xt", [None])[0]
        if xt and "urn:btih:" in xt:
            return xt.split("urn:btih:")[1]
    except:
        pass
    return ""

@app.get("/")
def root():
    return {"status": "Zamunda addon is running"}

@app.get("/manifest.json")
def manifest():
    return {
        "id": "org.stremio.zamunda",
        "version": "1.0.0",
        "name": "Zamunda",
        "description": "Stremio addon за търсене на торенти от Zamunda.net",
        "resources": ["catalog", "stream"],
        "types": ["movie", "series"],
        "catalogs": [{
            "type": "movie",
            "id": "zamunda_catalog",
            "name": "Zamunda Search",
            "extra": [{"name": "search", "isRequired": True}]
        }],
        "idPrefixes": ["https://zamunda.net/torrents/"],
        "behaviorHints": {"configurationRequired": False}
    }

@app.get("/catalog/{type}/{id}.json")
def catalog(type: str, id: str, search: str = ""):
    if not logged_in:
        return {"metas": []}
    if id != "zamunda_catalog" or not search:
        return {"metas": []}

    html = zamunda.search_torrents(search)
    soup = BeautifulSoup(html, "html.parser")

    metas = []

    # Замунда резултатите са в таблица с клас "lista"
    table = soup.find("table", class_="lista")
    if not table:
        return {"metas": []}

    rows = table.find_all("tr")[1:]  # прескачаме header row

    for row in rows[:20]:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue
        a_tag = cols[1].find("a", href=True)
        if not a_tag:
            continue

        title = a_tag.text.strip()
        href = a_tag["href"]
        full_url = urllib.parse.urljoin(BASE_URL, href)

        metas.append({
            "id": full_url,
            "type": type,
            "name": title,
            "poster": "https://zamunda.net/images/favicon.ico"
        })

    return {"metas": metas}

@app.get("/stream/{type}/{id}.json")
def stream(type: str, id: str):
    if not logged_in:
        return {"streams": []}

    if not id.startswith(BASE_URL):
        return {"streams": []}

    resp = zamunda.session.get(id)
    soup = BeautifulSoup(resp.text, "html.parser")

    magnet = ""
    for a in soup.find_all("a", href=True):
        if a["href"].startswith("magnet:"):
            magnet = a["href"]
            break

    if not magnet:
        return {"streams": []}

    info_hash = extract_info_hash(magnet)

    return {
        "streams": [{
            "title": "Zamunda",
            "infoHash": info_hash,
            "fileIdx": 0,
            "url": magnet
        }]
    }
