from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
import requests
import urllib.parse
from urllib.parse import parse_qs, urlparse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_URL = "https://arenabg.com"
LOGIN_URL = f"{BASE_URL}/bg/users/signin/"

ARENABG_USERNAME = "uxada"
ARENABG_PASSWORD = "P@rola123456"

TMDB_API_KEY = "5e812cae5bcf352dd5db9a0ca437fd17"  # Смени с твоя ако искаш

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

    def get_page(self, url):
        return self.session.get(url).text

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
        "description": "Stremio адон за ArenaBG",
        "resources": ["catalog", "stream"],
        "types": ["movie", "series"],
        "catalogs": [{
            "type": "movie",
            "id": "arenabg_catalog",
            "name": "ArenaBG Search",
            "extra": [{"name": "search", "isRequired": True}]
        }],
        "idPrefixes": ["https://arenabg.com/"],
        "behaviorHints": {"configurationRequired": False}
    }

@app.get("/stream/{type}/{id}.json")
def stream(type: str, id: str, url: str = None):
    if not logged_in:
        return {"streams": []}

    torrent_url = url or id
    if not torrent_url.startswith(BASE_URL):
        return {"streams": []}

    print(f"⏬ Заявка за торент: {torrent_url}")

    try:
        html = arenabg.get_page(torrent_url)
        soup = BeautifulSoup(html, "html.parser")
        magnet = ""

        for a in soup.find_all("a", href=True):
            if a["href"].startswith("magnet:"):
                magnet = a["href"]
                break

        if not magnet:
            print("❌ Не е открит magnet линк")
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

    except Exception as e:
        print(f"⚠️ Грешка при стрийм обработка: {e}")
        return {"streams": []}
