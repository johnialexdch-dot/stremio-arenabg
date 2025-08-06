from bs4 import BeautifulSoup

def parse_arenabg_html(html: str) -> list:
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.select('table > tbody > tr')
    metas = []

    for row in rows:
        try:
            title_cell = row.select_one('td.filename a.title')
            if not title_cell:
                continue

            title = title_cell.text.strip()
            relative_url = title_cell['href']
            torrent_url = f"https://arenabg.com{relative_url}"

            poster_url = ""
            if "onmouseover" in title_cell.attrs:
                hover = title_cell['onmouseover']
                if 'https://' in hover:
                    poster_url = hover.split('"')[1]

            metas.append({
                "id": torrent_url,
                "type": "movie",
                "name": title,
                "poster": poster_url,
            })
        except Exception as e:
            print("Грешка при парсинг на ред:", e)
            continue

    return metas
