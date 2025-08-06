from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
import requests
import urllib.parse
from urllib.parse import parse_qs, urlparse, unquote

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # за тестове
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_URL = "https://arenabg.com"
LOGIN_URL = f"{BASE_URL}/bg/users/signin/"

ARENABG_USERNAME = "uxada"
ARENABG_PASSWORD = "P@rola123456"

TMDB_API_KEY = "5e812cae5bcf352dd5db9a0ca437fd17"  # <-- смени го с твоя ключ от TMDb

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

def imdb_to_title(imdb_id: str) -> str:
    url = f"https://api.themoviedb.org/3/find/{imdb_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "external_source": "imdb_id"
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        print(f"TMDb API error: {resp.status_code}")
        return ""
    data = resp.json()
    if data.get("movie_results"):
        return data["movie_results"][0]["title"]
    elif data.get("tv_results"):
        return data["tv_results"][0]["name"]
    else:
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
        "idPrefixes": ["https://arenabg.com/"],  # Важна част - използваме пълните URL-та като id
        "behaviorHints": {"configurationRequired": False}
    }

@app.get("/catalog/{type}/{id}.json")
def catalog(type: str, id: str, search: str = ""):
    print(f"catalog called with type={type}, id={id}, search={search}")
    if not logged_in:
        print("Not logged in")
        return {"metas": []}

    if id != "arenabg_catalog" or not search:
        print("Invalid id or empty search")
        return {"metas": []}

    html = arenabg.search_torrents(search)
    soup = BeautifulSoup(html, "html.parser")

    rows = soup.find_all("tr")
    print(f"Found {len(rows)} rows")

    metas = []
    for row in rows[:20]:
        a_tag = row.find("a", class_="title")
        if not a_tag:
            continue

        title = a_tag.text.strip()
        href = a_tag.get("href")
        full_url = BASE_URL + href if href else ""

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

    print(f"Returning {len(metas)} metas")
    return {"metas": metas}

@app.get("/stream/{type}/{id}.json")
def stream(type: str, id: str):
    if not logged_in:
        return {"streams": []}

    search_query = id
    # Ако ид започва с tt (IMDb ID), търсим заглавието от TMDb
    if id.startswith("tt"):
        search_query = imdb_to_title(id)
        if not search_query:
            print(f"Не можа да намери заглавие за IMDb ID {id}")
            return {"streams": []}
        print(f"TMDb title for {id}: {search_query}")

    # Търсим торентите по заглавието (или по самия id, ако не е tt)
    html = arenabg.search_torrents(search_query)
    soup = BeautifulSoup(html, "html.parser")

    first_url = None
    rows = soup.find_all("tr")
    for row in rows:
        a_tag = row.find("a", class_="title")
        if a_tag and a_tag.get("href"):
            first_url = BASE_URL + a_tag.get("href")
            break

    if not first_url:
        print("Няма намерен торент")
        return {"streams": []}

    r = arenabg.session.get(first_url)
    soup = BeautifulSoup(r.text, "html.parser")

    magnet = ""
    for a in soup.find_all("a", href=True):
        if a["href"].startswith("magnet:"):
            magnet = a["href"]
            break

    if not magnet:
        print("Няма намерен magnet линк")
        return {"streams": []}

    info_hash = extract_info_hash(magnet)

    return {
        "streams": [{
            "title": "ArenaBG",
            "infoHash": info_hash,
            "fileIdx": 0,
            "url": magnet
        }]
    }
