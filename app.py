from flask import Flask, render_template, request
import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import re
from bs4 import BeautifulSoup

app = Flask(__name__)   

# === Инициализация базы данных ===
def init_db():
    """Создает таблицу, если её нет."""
    conn = sqlite3.connect('data.db')  
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS skins (id INTEGER PRIMARY KEY, name TEXT, price TEXT)')
    conn.commit()
    conn.close()

# === Парсер данных ===
import re

def parse_data(weapon):
    data = []
    url = f'https://steamcommunity.com/market/search?q={weapon}'  # Используем параметр поиска
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch data for {weapon}. Status code: {response.status_code}")
        return data
    soup = BeautifulSoup(response.text, 'html.parser')

    items = soup.select('.market_listing_row')
    for item in items:
        name = item.select_one('.market_listing_item_name')
        price = item.select_one('.market_table_value .normal_price')
        if name and price:
            name_text = name.get_text(strip=True)
            price_text = price.get_text(strip=True)
            
            price_value = re.sub(r'[^\d.]', '', price_text)
            
            data.append((name_text, price_value))
        else:
            print(f"Failed to parse item: {item}") 

    return data





# === Сохранение данных ===
def save_to_db(data):
    try:
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM skins')  # Очистка таблицы перед обновлением
        data = [(name, float(price.replace('$', '').strip())) for name, price in data]
        cursor.executemany('INSERT INTO skins (name, price) VALUES (?, ?)', data)
        conn.commit()
        print(f"Saved {len(data)} items to the database.")
    except sqlite3.Error as e:
        print("Ошибка базы данных:", e)
    finally:
        conn.close()





# === Автообновление данных ===
def update_data():
    data = parse_data()
    if data:  
        save_to_db(data)

# === Маршруты Flask ===
@app.route('/', methods=['GET'])
def index():
    sort_by = request.args.get('sort', 'name')  
    order = request.args.get('order', 'asc')   
    weapon = request.args.get('weapon', 'AWP')  

    # Проверяем допустимые параметры сортировки
    VALID_SORT_COLUMNS = {'name', 'price'}
    if sort_by not in VALID_SORT_COLUMNS:
        sort_by = 'name'

    order = 'ASC' if order == 'asc' else 'DESC'

    # Парсим данные с учетом поискового запроса
    data = parse_data(weapon) 

    if sort_by == 'price':
        data = sorted(data, key=lambda x: float(x[1]), reverse=(order == 'DESC'))
    else:
        data = sorted(data, key=lambda x: x[0].lower(), reverse=(order == 'DESC'))

    # Возвращаем данные в шаблон с текущими параметрами
    return render_template('index.html', items=data, sort=sort_by, order=order, weapon=weapon)





# === Запуск приложения ===
if __name__ == '__main__':
    init_db()  # Инициализация базы данных при запуске
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=update_data, trigger="interval", minutes=10)  # Обновление каждые 10 минут
    scheduler.start()
    app.run(debug=True)
