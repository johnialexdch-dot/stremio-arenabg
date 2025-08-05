from fastapi import FastAPI
from fastapi.responses import JSONResponse
from bs4 import BeautifulSoup
import requests
import urllib.parse

app = FastAPI()

BASE_URL = "https://arenabg.com"

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
    if id != "arenabg_catalog" or not search:
        return JSONResponse(content={"metas": []})

    query = urllib.parse.quote_plus(search)
    url = f"{BASE_URL}/torrents?q={query}"

    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    metas = []
    rows = soup.select("table.table-hover tbody tr")

    for row in rows[:20]:  # лимит до 20 резултата
        cols = row.find_all("td")
        if len(cols) < 2:
            continue

        title_tag = cols[1].find("a")
        title = title_tag.text.strip()
        link = title_tag.get("href")
        full_link = BASE_URL + link

        # използваме href като unique id
        metas.append({
            "id": full_link,
            "name": title,
            "type": type,
            "poster": "https://arenabg.com/favicon.ico"
        })

    return JSONResponse(content={"metas": metas})


@app.get("/stream/{type}/{id}.json")
def stream(type: str, id: str):
    url = urllib.parse.unquote(id)

    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
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
            "infoHash": "",
            "fileIdx": 0,
            "url": magnet
        })

    return JSONResponse(content={"streams": streams})
