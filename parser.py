import requests
from bs4 import BeautifulSoup
import random
import re
from db import ad_exists, add_ad

import requests
import random
import re
from bs4 import BeautifulSoup
from db import get_custom_link

def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())

def get_random_cars(
    min_price=500,
    max_price=3000,
    count=1,
    max_photos=10,
    max_pages=20,
    base_url: str | None = None
):
    headers = {"User-Agent": "Mozilla/5.0"}

    # если передан кастомный линк — используем его
    if base_url:
        urls = [base_url]
    else:
        urls = [
            f"https://cars.av.by/filter?price_usd[min]={min_price}&price_usd[max]={max_price}&page={random.randint(1, 10)}"
            for _ in range(max_pages)
        ]

    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=10)
        except requests.RequestException:
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.find_all("div", class_="listing-item")
        if not items:
            continue

        random.shuffle(items)
        results = []

        for random_item in items:
            if len(results) >= count:
                break

            title_tag = random_item.find("a", class_="listing-item__link")
            link = "https://cars.av.by" + title_tag["href"] if title_tag else ""
            if not link or ad_exists(link):
                continue

            title = title_tag.text.strip() if title_tag else "Без названия"

            price_tag = random_item.find("div", class_="listing-item__price-secondary")
            price_text = price_tag.text.strip().replace("≈", "").replace(" ", "") if price_tag else "—"

            location_tag = random_item.find("div", class_="listing-item__location")
            location_text = location_tag.text.strip() if location_tag else "Неизвестно"

            params_tag = random_item.find("div", class_="listing-item__params")
            params_text = params_tag.get_text(", ", strip=True) if params_tag else ""
            params_text = re.sub(r"(,\s*){2,}", ", ", params_text).strip(", ")

            # извлекаем описание из карточки или полной страницы
            desc_tag = random_item.find("div", class_="listing-item__message")
            description = desc_tag.text.strip() if desc_tag else ""

            adv_soup = None
            try:
                adv_resp = requests.get(link, headers=headers, timeout=10)
                adv_soup = BeautifulSoup(adv_resp.text, "html.parser")
            except requests.RequestException:
                pass

            # если краткого описания нет — пробуем из полной страницы
            if not description and adv_soup:
                desc_full = adv_soup.select_one(".card__comment p")
                if desc_full:
                    description = desc_full.text.strip()

            if not description:
                description = "Нет описания"

            # --- модификация авто ---
            mod_block = adv_soup.find("div", class_="card__modification") if adv_soup else None
            mod_text = clean_text(mod_block.get_text(" ", strip=True)) if mod_block else "—"

            # --- собираем фото ---
            photos = []
            if adv_soup:
                gallery = adv_soup.select(".gallery__stage .gallery__frame img")
                for img in gallery:
                    url_img = img.get("data-src") or img.get("src")
                    if url_img and not url_img.startswith("data:image"):
                        photos.append(url_img)
                    if len(photos) >= max_photos:
                        break

            # --- форматирование полей ---
            parts = [p.strip() for p in params_text.split(",") if p.strip()]
            year = next((p for p in parts if re.match(r"\d{4}", p)), "—").replace("г.", "").strip()
            engine = next((p for p in parts if "л" in p), "—")
            fuel = next((p for p in parts if any(f in p.lower() for f in ["бензин", "дизель", "газ"])), "—")
            transmission = next((p for p in parts if any(t in p.lower() for t in ["механика", "автомат"])), "—")
            mileage = next((p for p in parts if "км" in p), "—")

            formatted_message = (
                f"🚗 {title}  📅 {year}\n"
                f"🛣 {mileage}  |⛽️ {fuel.title()}, {engine}\n"
                f"📦 {transmission.title()} |⚙️ {mod_text}\n"
                f"📍 {location_text}\n"
                f"💰 {price_text}\n\n"
                f"{description.strip()}\n\n"
            )

            results.append({
                "title": title,
                "price": price_text,
                "location": location_text,
                "params": params_text,
                "description": description,
                "link": link,
                "photos": photos,
                "modification": mod_text,
                "message": formatted_message
            })

            add_ad(link)

        if results:
            return results

    return []

def clean_text(text: str) -> str:
    """Убирает лишние пробелы, двойные запятые и неразрывные пробелы."""
    if not text:
        return ""
    text = text.replace("\xa0", " ").replace(" ", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(,\s*){2,}", ", ", text)
    text = text.strip(",. \n\t")
    return text.strip()


def parse_single_car(url, max_photos=10):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # 🏷 Заголовок — убираем слово "Продажа"
    title_block = soup.find("h1")
    title = clean_text(title_block.text) if title_block else "Без названия"
    title = re.sub(r"(?i)^Продажа\s+", "", title).strip()  # убираем "Продажа" в начале

    # 🧩 Основные параметры
    params_block = soup.find("div", class_="card__params")
    params_text = clean_text(params_block.get_text(" ", strip=True)) if params_block else ""
    parts = [p.strip() for p in re.split(r"[,\|]", params_text) if p.strip()]

    year = gearbox = engine = fuel = mileage = "—"
    for p in parts:
        if re.search(r"\d{4}\s*г", p):
            year = clean_text(p.replace("г.", "").replace("г", ""))
        elif any(x in p.lower() for x in ["механика", "автомат", "вариатор"]):
            gearbox = clean_text(p)
        elif re.search(r"\d+[,\.]?\d*\s*л", p):
            engine = clean_text(p)
        elif any(x in p.lower() for x in ["бензин", "дизель", "газ", "электро"]):
            fuel = clean_text(p)
        elif "км" in p:
            mileage = clean_text(p)

    # 🚗 Кузов / привод / цвет
    desc_block = soup.find("div", class_="card__description")
    desc_text = clean_text(desc_block.get_text(", ", strip=True)) if desc_block else "—"

    # ⚙️ Модификация
    mod_block = soup.find("div", class_="card__modification")
    mod_text = clean_text(mod_block.get_text(" ", strip=True)) if mod_block else "—"

    # 📍 Локация
    loc_block = soup.find("div", class_="card__location")
    location = clean_text(loc_block.text) if loc_block else "Неизвестно"

    # 💰 Цена
    price_block = soup.find("div", class_="card__price-primary")
    price = clean_text(price_block.text) if price_block else "—"

    # 📝 Описание — убираем "Описание" в начале
    comment_block = soup.find("div", class_="card__comment")
    if comment_block:
        description = clean_text(comment_block.text)
        description = re.sub(r"(?i)^Описание", "", description).strip()
    else:
        description = "Нет описания"

    # 🖼 Фото
    gallery = soup.select(".gallery__stage .gallery__frame img")
    photos = []
    for img in gallery:
        src = img.get("data-src") or img.get("src")
        if src and not src.startswith("data:image"):
            photos.append(src)
        if len(photos) >= max_photos:
            break

    return {
        "title": title,
        "year": year,
        "gearbox": gearbox,
        "engine": engine,
        "fuel": fuel,
        "mileage": mileage,
        "desc_text": desc_text,
        "mod_text": mod_text,
        "price": price,
        "location": location,
        "description": description,
        "photos": photos,
        "link": url,
    }
