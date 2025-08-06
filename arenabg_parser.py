from bs4 import BeautifulSoup
import re

def parse_arenabg_html(html: str) -> list:
    soup = BeautifulSoup(html, 'html.parser')
    metas = []

    for a in soup.find_all("a", class_="title"):
        try:
            title = a.get_text(strip=True)
            relative_url = a.get("href")
            if not relative_url:
                continue

            torrent_url = f"https://arenabg.com{relative_url}"

            # poster
            onmouseover = a.get("onmouseover", "")
            match = re.search(r"https:\\/\\/[^\\\"]+", onmouseover)
            poster_url = match.group(0).replace("\\/", "/") if match else ""

            metas.append({
                "id": torrent_url,
                "type": "movie",
                "name": title,
                "poster": poster_url,
            })
        except Exception as e:
            print("Грешка при парсинг:", e)
            continue

    return metas
