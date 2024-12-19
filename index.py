import requests
from bs4 import BeautifulSoup
import sqlite3
import os
import json
import re
import sys
import pandas as pd

# Get the script name and arguments from sys.argv
should_download = True if len(sys.argv) > 1 and sys.argv[1] != 'skip' else False

color_map = {
    "赤": "red",
    "緑": "green",
    "青": "blue",
    "紫": "purple",
    "黄": "yellow",
    "黒": "black"
}

conn = sqlite3.connect('OPTCG.cdb')
cursor = conn.cursor()

def translate_japanese_color(japanese_colors):
  # Split the input string into individual colors
  colors = japanese_colors.split('/')

  # Translate each color using the color map
  translated_colors = []
  for color in colors:
    translated_colors.append(color_map.get(color, color))

  # Join the translated colors back into a string
  return " ".join(translated_colors)


def generate_tags():
    tag_map = {
        "[When Attacking]": "atk",
        "[DON!! x": "don",
        "[On Your Opponent's Attack]": "oatk",
        "[Once Per Turn]": "opt",
        "[On Play]": "opl",
        "[Rush]": "rsh",
        "[Blocker]": "blk",
        "[On Block]": "onblk",
        "[Activate: Main]": "main",
        "[Main]": "main",
        "[Trigger]": "trg",
        "[Counter]": "ctr",
        "[End of Your Turn]": "end",
        "[On K.O.]": "oko",
        "[Your Turn]": "trn",
        "[Banish]": "bsh",
        "[Double Attack]": "dbl"
    }

     # Fetch data and process it. Use parameterized query to prevent SQL injection
    cursor.execute(f"SELECT rowid, effect, trigger, card_code FROM card_translations")
    rows = cursor.fetchall()

    for rowid, effect, trigger, card_code in rows:
        card_tags = []
        search_source = effect + ' ' + trigger
        for keyword, value in tag_map.items():
            # Use re.escape to handle special characters in keywords
            escaped_keyword = re.escape(keyword)
            pattern = escaped_keyword
            if re.search(pattern, search_source):
                card_tags.append(value)

        cursor.execute(f"UPDATE cards SET tags = ? WHERE code = ?", (','.join(card_tags), card_code))



def create_database_tables():
    # Define your table schema with columns and data types
    card_schema = """
    CREATE TABLE IF NOT EXISTS cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT,
        image TEXT,
        name TEXT,
        category TEXT,
        type TEXT,
        cost INTEGER,
        attribute TEXT,
        power INTEGER,
        counter INTEGER,
        color TEXT,
        sets TEXT,
        effect TEXT,
        trigger TEXT,
        art_variant INTEGER,
        tags TEXT,
        UNIQUE (code, name, sets, art_variant)
    )   
    """

    card_translations_schema = """
    CREATE TABLE IF NOT EXISTS card_translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_code TEXT NOT NULL,
    locale TEXT NOT NULL,
    name TEXT,
    type TEXT,
    effect TEXT,
    trigger TEXT,
    image TEXT,
    art_variant INTEGER,
    FOREIGN KEY (card_code) REFERENCES cards(code)
    UNIQUE (card_code, locale, art_variant)
    );
    """

    # Execute the create table query
    cursor.execute(card_schema)
    cursor.execute(card_translations_schema)

def download_core_card_data():
    url = "https://onepiece-cardgame.com/cardlist/"
    response = requests.get(url)

    # get listed series
    soup = BeautifulSoup(response.content, "html.parser")
    series_div = soup.select('#series option')
    series_list = []
    for series_option in series_div:
        if series_option['value']:
            series_list.append(series_option['value'])

    # get cards of each series
    for series in series_list: 
        form_data={"series": series}
        response = requests.post(url, data=form_data)
        soup = BeautifulSoup(response.content, "html.parser")
        card_divs = soup.find_all('dl', class_='modalCol')


        for card_div in card_divs:
            card_data = {
                "code": card_div.select('.infoCol span')[0].text.split('|')[0],
                "category": card_div.select('.infoCol span')[-1].text.lower(),
                "image": card_div.select('img[data-src]')[0].attrs['data-src'].replace('../', 'https://onepiece-cardgame.com/'),
                "name": card_div.select('.cardName')[0].text,
                "cost": card_div.select('.cost')[0].text[3:],
                "attribute": card_div.select('.attribute h3')[0].text,
                "power": card_div.select('.power')[0].text[3:].replace('-', '0'),
                "counter": card_div.select('.counter')[0].text[5:].replace('-', '0'),
                "color": translate_japanese_color(card_div.select('.color')[0].text[1:]),
                "type": ";".join(card_div.select('.feature')[0].text[2:].split('/')),
                "sets": card_div.select('.getInfo')[0].text[11:],
                "effect": card_div.select('.text')[0].text[4:],
                "trigger":card_div.select('.trigger')[0].text[4:] if card_div.select('.trigger') else ''
            }
            if card_data['category'] == 'leader':
                card_data['cost'] = 0
            art_match = re.search(r'_p(\d+)', card_data['image'])
            card_data['art_variant'] = int(art_match.group(1)) if art_match else 0

            cursor.execute("INSERT OR IGNORE INTO cards (code, name, category, cost, attribute, power, counter, color, type, sets, effect, trigger, image, art_variant) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (card_data['code'], card_data['name'], card_data['category'], card_data['cost'], card_data['attribute'], card_data['power'], card_data['counter'], card_data['color'], card_data['type'], card_data['sets'], card_data['effect'], card_data['trigger'], card_data['image'], card_data['art_variant']))

def download_english_locales():
    url = "https://asia-en.onepiece-cardgame.com/cardlist/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    series_div = soup.select('#series option')
    series_list = []
    for series_option in series_div:
        if series_option['value']:
            series_list.append(series_option['value'])
    for series in series_list: 
        form_data={"series": series}
        response = requests.post(url, data=form_data)
        soup = BeautifulSoup(response.content, "html.parser")
        card_divs = soup.find_all('dl', class_='modalCol')


        for card_div in card_divs:
            card_data = {
                "code": card_div.select('.infoCol span')[0].text.split('|')[0],
                "image": card_div.select('img[data-src]')[0].attrs['data-src'].replace('../', 'https://en.onepiece-cardgame.com/'),
                "name": card_div.select('.cardName')[0].text,
                "type": ";".join(card_div.select('.feature')[0].text[4:].split('/')),
                "effect": card_div.select('.text')[0].text[6:],
                "trigger":card_div.select('.trigger')[0].text[7:] if card_div.select('.trigger') else ''
            }
            art_match = re.search(r'_p(\d+)', card_data['image'])
            card_data['art_variant'] = int(art_match.group(1)) if art_match else 0

            cursor.execute("INSERT OR IGNORE INTO card_translations (card_code, locale, name, type, effect, trigger, image, art_variant) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (card_data['code'], 'en', card_data['name'], card_data['type'], card_data['effect'], card_data['trigger'], card_data['image'], card_data['art_variant']))


print('Create Database Tables if not existing\n')
create_database_tables()

print('Download Basic card info\n')
if should_download:
    download_core_card_data()

print('Download english translations\n')
if should_download:
    download_english_locales()

print('Generate Tags\n')
generate_tags()

# Generate json file from SQLITE database
print('Generating JSON file\n')
df = pd.read_sql_query("SELECT * FROM cards", conn)
cards = json.loads(df.to_json(orient="records"))

df = pd.read_sql_query("SELECT * FROM card_translations", conn)
card_locales = json.loads(df.to_json(orient="records"))

filename = "OPTCG.json"
if os.path.exists(filename):
    os.remove(filename)

output = {}
output["card_locales"] = card_locales
output["cards"] = cards

with open(filename, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)


conn.commit()
conn.close()