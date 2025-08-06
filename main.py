from fastapi import FastAPI
from fastapi.responses import JSONResponse
from bs4 import BeautifulSoup
import requests
import urllib.parse
from urllib.parse import parse_qs, urlparse

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
        print("Search HTML preview:", resp.text[:500])
        return resp.text

arenabg = ArenaBGSession(ARENABG_USERNAME, ARENABG_PASSWORD)
logged_in = arenabg.login()

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
    soup = BeautifulSoup(html, "html.parser")

    rows = soup.find_all("tr")
    metas = []

    for row in rows[:20]:
        a_tag = row.find("a", class_="title")
        if not a_tag:
            continue

        title = a_tag.text.strip()
        href = a_tag.get("href")
        full_url = BASE_URL + href if href else ""

        # Постер от onmouseover
        onmouseover = a_tag.get("onmouseover", "")
        poster = ""
        if "https://" in onmouseover:
            try:
                poster = onmouseover.split('"')[1]
            except:
                pass

        metas.append({
            "id": full_url,
            "name": title,
            "type": type,
            "poster": poster or "https://arenabg.com/favicon.ico"
        })

    return {"metas": metas}


@app.get("/stream/{type}/{id}.json")
def stream(type: str, id: str):
    url = urllib.parse.unquote(id)

    if not logged_in:
        return {"streams": []}

    r = arenabg.session.get(url)
    html = r.text

    print("Stream page HTML preview:", html[:2000])  # показва първите 2000 символа

    soup = BeautifulSoup(html, "html.parser")

    magnet = ""
    for a in soup.find_all("a", href=True):
        if a["href"].startswith("magnet:"):
            magnet = a["href"]
            break

    if magnet:
        print("Magnet link found:", magnet)
    else:
        print("No magnet link found.")

    streams = []
    if magnet:
        info_hash = extract_info_hash(magnet)
        streams.append({
            "title": "ArenaBG",
            "infoHash": info_hash,
            "fileIdx": 0,
            "url": magnet
        })

    return {"streams": streams}

