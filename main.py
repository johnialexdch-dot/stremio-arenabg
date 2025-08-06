from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from urllib.parse import unquote
from bs4 import BeautifulSoup

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ArenaBG:
    def __init__(self):
        self.session = requests.Session()
        self.login()

    def login(self):
        # Тук сложи правилния си логин, примерно:
        url_login = "https://arenabg.com/login"
        data = {"username": "uxada", "password": "P@rola123456"}
        r = self.session.post(url_login, data=data)
        if r.ok:
            print("✅ Успешен вход в ArenaBG")
        else:
            print("❌ Грешка при вход в ArenaBG")

    def search(self, query):
        # Тук примерно търсене (примерна имплементация)
        search_url = f"https://arenabg.com/search/{query}"
        r = self.session.get(search_url)
        soup = BeautifulSoup(r.text, "html.parser")
        # Парсване на резултати...
        # Върни списък от резултати с id като пълния URL към стрийм
        results = []
        for item in soup.select(".torrent-row"):  # примерен CSS селектор
            title = item.select_one(".torrent-title").text.strip()
            link = item.select_one("a")["href"]
            full_url = "https://arenabg.com" + link
            results.append({
                "id": full_url,
                "name": title,
                "poster": None,
            })
        return results

arenabg = ArenaBG()

@app.get("/manifest.json")
async def manifest():
    return {
        "id": "org.stremio.arenabg",
        "version": "1.0.0",
        "name": "ArenaBG",
        "description": "Addon за филми и сериали от arenabg.com",
        "resources": ["catalog", "stream"],
        "types": ["movie", "series"],
        "catalogs": [
            {
                "type": "movie",
                "id": "arenabg_movies",
                "name": "ArenaBG Филми"
            },
            {
                "type": "series",
                "id": "arenabg_series",
                "name": "ArenaBG Сериали"
            }
        ]
        # ВНИМАНИЕ: НЕ слагай "idPrefixes"
    }

@app.get("/catalog/{type}/{id}.json")
async def catalog(type: str, id: str, search: str = None):
    if search:
        results = arenabg.search(search)
    else:
        results = []  # може да добавиш избрани филми, ако искаш
    return {
        "metas": results
    }

@app.get("/stream/{type}/{id}.json")
async def stream(type: str, id: str):
    id_decoded = unquote(id)
    if not id_decoded.startswith("http"):
        # Ако не е валиден URL, върни празен отговор
        return {"streams": []}

    r = arenabg.session.get(id_decoded)
    if not r.ok:
        return {"streams": []}

    # Парсирай страницата, за да извлечеш magnet линкове
    soup = BeautifulSoup(r.text, "html.parser")
    streams = []

    # Примерно търсене на magnet линкове в страницата
    for a in soup.select('a[href^="magnet:"]'):
        magnet = a["href"]
        title = a.get_text(strip=True) or "Torrent"
        streams.append({
            "title": title,
            "url": magnet,
            "infoHash": "",  # Можеш да извлечеш infoHash от magnet ако искаш
        })

    return {"streams": streams}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
