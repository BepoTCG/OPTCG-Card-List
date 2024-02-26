import requests
from bs4 import BeautifulSoup
import sqlite3
import os
import json

conn = sqlite3.connect('OPTCG.cdb')
cursor = conn.cursor()

# Define your table schema with columns and data types
table_schema = """
CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,
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
    UNIQUE (code, name, sets)
)   
"""

# Execute the create table query
cursor.execute(table_schema)



url = "https://asia-en.onepiece-cardgame.com/cardlist/"

response = requests.get(url)

# get listed series
soup = BeautifulSoup(response.content, "html.parser")
series_div = soup.select('#series option')
series_list = []
for series_option in series_div:
    if series_option['value']:
        series_list.append(series_option['value'])


# get cards of each series
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
            "name": card_div.select('.cardName')[0].text,
            "cost": card_div.select('.cost')[0].text[4:],
            "attribute": card_div.select('.attribute i')[0].text,
            "power": card_div.select('.power')[0].text[5:].replace('-', '0'),
            "counter": card_div.select('.counter')[0].text[7:].replace('-', '0'),
            "color": card_div.select('.color')[0].text[5:],
            "type": ";".join(card_div.select('.feature')[0].text[4:].split('/')),
            "sets": card_div.select('.getInfo')[0].text[11:],
            "effect": card_div.select('.text')[0].text[6:],
            "trigger":card_div.select('.trigger')[0].text[7:] if card_div.select('.trigger') else ''
        }
        cards.append(card_data)
        cursor.execute("INSERT OR IGNORE INTO cards (code, name, category, cost, attribute, power, counter, color, type, sets, effect, trigger) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (card_data['code'], card_data['name'], card_data['category'], card_data['cost'], card_data['attribute'], card_data['power'], card_data['counter'], card_data['color'], card_data['type'], card_data['sets'], card_data['effect'], card_data['trigger']))
        print(card_data)

# Generate json file
filename = "OPTCG.json"
if os.path.exists(filename):
    os.remove(filename)

with open(filename, "w") as f:
    json.dump(cards, f, indent=4)        

conn.commit()
conn.close()