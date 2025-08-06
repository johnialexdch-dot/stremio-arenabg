from bs4 import BeautifulSoup
import re

def parse_arenabg_html(html: str) -> list:
    soup = BeautifulSoup(html, 'html.parser')
    metas = []

    # Вземи всички линкове към торенти (заглавия)
    for a in soup.find_all("a", class_="title"):
        try:
            title = a.get_text(strip=True)
            relative_url = a.get("href")
            if not relative_url:
                continue

            torrent_url = f"https://arenabg.com{relative_url}"

            # Извличане на постер URL от onmouseover JS атрибута
            onmouseover = a.get("onmouseover", "")
            poster_match = re.search(r"https:\\/\\/[^\\\"]+", onmouseover)
            poster_url = poster_match.group(0).replace("\\/", "/") if poster_match else ""

            metas.append({
                "id": torrent_url,
                "type": "movie",   # може да се адаптира според категорията
                "name": title,
                "poster": poster_url,
            })

        except Exception as e:
            print("Грешка при парсинг на елемент:", e)
            continue

    return metas
