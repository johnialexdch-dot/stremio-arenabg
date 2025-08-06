from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from bs4 import BeautifulSoup
from arenabg_parser import parse_arenabg_html  # ако имаш тази функция
import requests
import urllib.parse

app = FastAPI()

BASE_URL = "https://arenabg.com"
LOGIN_URL = f"{BASE_URL}/bg/users/signin/"

ARENABG_USERNAME = "uxada"
ARENABG_PASSWORD = "P@rola123456"

class ArenaBGSession:
    def __init__(self, username, password):
        self.session = requests.Session()
        self.username = username
        self.password = password

    def login(self):
        resp = self.session.get(LOGIN_URL)
        soup = BeautifulSoup(resp.text, "html.parser")
        csrf_input = soup.find("input", {"name": "csrf_token"})
        csrf_token = csrf_input["value"] if csrf_input else ""

        payload = {
            "username_or_email": self.username,
            "password": self.password,
        }
        if csrf_token:
            payload["csrf_token"] = csrf_token

        login_resp = self.session.post(LOGIN_URL, data=payload)

        if "Вход" in login_resp.text or "signin" in login_resp.url:
            print("❌ НЕуспешен вход в ArenaBG")
            return False
        else:
            print("✅ Успешен вход в ArenaBG")
            return True

    def search_torrents(self, query):
        search_url = f"{BASE_URL}/bg/torrents/?text={urllib.parse.quote_plus(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": BASE_URL
        }
        resp = self.session.get(search_url, headers=headers)
        print("Search status:", resp.status_code)
        print("Search HTML preview:", resp.text[:500])  # по-малко, за четимост
        return resp.text

arenabg = ArenaBGSession(ARENABG_USERNAME, ARENABG_PASSWORD)
logged_in = arenabg.login()

@app.get("/")
def root():
    return {"status": "ArenaBG addon is running"}

@app.get("/manifest.json")
def manifest():
    return {
        "id": "org.stremio.arenabg",
        "version": "1.0.0",
        "name": "ArenaBG",
        "description": "Stremio адон за търсене на торенти от ArenaBG",
        "resources": ["catalog", "stream"],
        "types": ["movie", "series"],
        "catalogs": [{
            "type": "movie",
            "id": "arenabg_catalog",
            "name": "ArenaBG Search",
            "extra": [{"name": "search", "isRequired": True}]
        }],
        "idPrefixes": ["tt"],
        "behaviorHints": {"configurationRequired": False}
    }

@app.get("/catalog/{type}/{id}.json")
def catalog(type: str, id: str, search: str = ""):
    if not logged_in:
        return {"metas": []}

    if id != "arenabg_catalog" or not search:
        return {"metas": []}

    html = arenabg.search_torrents(search)

    # Ако имаш функция parse_arenabg_html, използвай я:
    # metas = parse_arenabg_html(html)

    # Ако нямаш, използвай този парсинг:
    soup = BeautifulSoup(html, "html.parser")

    metas = []
    rows = soup.select("table.table-hover tbody tr")
    for row in rows[:20]:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue

        title_tag = cols[1].find("a")
        if not title_tag:
            continue

        title = title_tag.text.strip()
        link = title_tag.get("href")
        full_link = BASE_URL + link

        metas.append({
            "id": full_link,
            "name": title,
            "type": type,
            "poster": "https://arenabg.com/favicon.ico"
        })

    return {"metas": metas}

@app.get("/stream/{type}/{id}.json")
def stream(type: str, id: str):
    url = urllib.parse.unquote(id)

    if not logged_in:
        return {"streams": []}

    r = arenabg.session.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    magnet = ""
    for a in soup.find_all("a", href=True):
        if a["href"].startswith("magnet:"):
            magnet = a["href"]
            break

    streams = []
    if magnet:
        streams.append({
            "title": "ArenaBG",
            "infoHash": "",  # Можеш да извадиш infoHash от магнит линка, ако искаш
            "fileIdx": 0,
            "url": magnet
        })

    return {"streams": streams}
