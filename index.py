import requests
from bs4 import BeautifulSoup
import sqlite3
import os
import json
import re

color_map = {
    "赤": "red",
    "緑": "green",
    "青": "blue",
    "紫": "purple",
    "黄": "yellow",
    "黒": "black"
}

def translate_japanese_color(japanese_colors):
  # Split the input string into individual colors
  colors = japanese_colors.split('/')

  # Translate each color using the color map
  translated_colors = []
  for color in colors:
    translated_colors.append(color_map.get(color, color))

  # Join the translated colors back into a string
  return " ".join(translated_colors)

conn = sqlite3.connect('OPTCG.cdb')
cursor = conn.cursor()

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
  FOREIGN KEY (card_code) REFERENCES cards(code)
  UNIQUE (card_code, locale)
);
"""

# Execute the create table query
cursor.execute(card_schema)
cursor.execute(card_translations_schema)

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
print('Download Basic card info')
cards = []
for series in series_list: 
    form_data={"series": series}
    response = requests.post(url, data=form_data)
    soup = BeautifulSoup(response.content, "html.parser")
    card_divs = soup.find_all('dl', class_='modalCol')


    for card_div in card_divs:
        card_data = {
            "code": card_div.select('.infoCol span')[0].text.split('|')[0],
            "category": card_div.select('.infoCol span')[-1].text.lower(),
            "image": card_div.find_previous_sibling().select('img')[0]['src'].replace('../', 'https://onepiece-cardgame.com/'),
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

        cards.append(card_data)
        cursor.execute("INSERT OR IGNORE INTO cards (code, name, category, cost, attribute, power, counter, color, type, sets, effect, trigger, image) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (card_data['code'], card_data['name'], card_data['category'], card_data['cost'], card_data['attribute'], card_data['power'], card_data['counter'], card_data['color'], card_data['type'], card_data['sets'], card_data['effect'], card_data['trigger'], card_data['image']))

# get english translations
print('Download english translations')
url = "https://asia-en.onepiece-cardgame.com/cardlist/"
response = requests.get(url)
card_locales = []
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
            "image": card_div.find_previous_sibling().select('img')[0]['src'].replace('../', 'https://en.onepiece-cardgame.com/'),
            "name": card_div.select('.cardName')[0].text,
            "type": ";".join(card_div.select('.feature')[0].text[4:].split('/')),
            "effect": card_div.select('.text')[0].text[6:],
            "trigger":card_div.select('.trigger')[0].text[7:] if card_div.select('.trigger') else ''
        }
        card_locales.append(card_data)
        cursor.execute("INSERT OR IGNORE INTO card_translations (card_code, locale, name, type, effect, trigger, image) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (card_data['code'], 'en', card_data['name'], card_data['type'], card_data['effect'], card_data['trigger'], card_data['image']))
        # print(card_data)


# Generate json file
filename = "OPTCG.json"
if os.path.exists(filename):
    os.remove(filename)

with open(filename, "w") as f:
    json.dump({"card_locales": card_locales, "cards": cards}, f, indent=4)
  

conn.commit()
conn.close()