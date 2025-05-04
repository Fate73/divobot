import os
import csv
from datetime import datetime
import pytz
import requests
from telegram import Bot

# Получаем переменные из окружения
TOKEN = os.getenv('TOKEN')
USER_ID = os.getenv('USER_ID')
HF_TOKEN = os.getenv('HF_TOKEN')

# Настройки
CSV_FILE = "topic.csv"
TIMEZONE = pytz.timezone('Europe/Moscow')

def get_next_topic():
    topics = []
    next_row = None
    next_idx = None

    # Читаем CSV с разделителем ;
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=';')
        for idx, row in enumerate(reader):
            topics.append(row)
            if not next_row and (row.get("Статус", "").strip() == "" or row.get("Статус", "").strip().lower() == "новая"):
                next_row = row
                next_idx = idx

    if next_row is None:
        return None, topics, None

    return next_row, topics, next_idx

def mark_topic_used(topics, idx):
    now = datetime.now(TIMEZONE).strftime("%d.%m.%Y %H:%M")
    topics[idx]["Статус"] = "использована"
    topics[idx]["Дата публикации"] = now

    # Сохраняем обратно в CSV
    with open(CSV_FILE, "w", encoding="utf-8", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=topics[0].keys(), delimiter=';')
        writer.writeheader()
        writer.writerows(topics)

def generate_post(topic, category):
    # Примеры вашего стиля (можно добавить свои)
    examples = [
        "Знаете ли вы, что у осьминога три сердца, и два из них перестают биться, когда он плывёт?",
        "В глубинах океана встречаются рыбы, которые светятся собственным светом — это биолюминесценция.",
    ]
    prompt = (
        f"{examples[0]}\n"
        f"{examples[1]}\n"
        f"Сгенерируй короткий, интересный и необычный факт на тему: '{topic}' (категория: {category}). "
        "Пиши в стиле познавательной заметки для Telegram-канала, избегай банальностей. Ещё один факт:"
    )

    url = "https://api-inference.huggingface.co/models/sberbank-ai/rugpt3large_based_on_gpt2"
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 120,
            "do_sample": True,
            "temperature": 1.0,
            "top_p": 0.9,
            "repetition_penalty": 1.2,
        }
    }
    response = requests.post(url, headers=headers, json=data, timeout=60)
    response.raise_for_status()
    result = response.json()
    # HuggingFace может возвращать результат по-разному, обработаем оба варианта:
    if isinstance(result, list) and "generated_text" in result[0]:
        return result[0]["generated_text"].strip()
    elif isinstance(result, dict) and "generated_text" in result:
        return result["generated_text"].strip()
    else:
        return str(result)

def main():
    next_row, topics, idx = get_next_topic()
    if not next_row:
        print("Темы для публикаций закончились! Пожалуйста, пополните файл topic.csv.")
        return

    topic = next_row["Тема"]
    category = next_row.get("Категория", "")
    post = generate_post(topic, category)

    # Отправляем сообщение в Telegram
    bot = Bot(token=TOKEN)
    now = datetime.now(TIMEZONE).strftime("%d.%m.%Y %H:%M")
    text = (
        f"🌟 Новая публикация для проверки:\n\n"
        f"Тема: {topic}\nКатегория: {category}\n\n"
        f"{post}\n\n"
        f"Время: {now} (МСК)"
    )
    bot.send_message(chat_id=USER_ID, text=text)

    # Отмечаем тему как использованную
    mark_topic_used(topics, idx)
    print(f"Публикация отправлена и тема отмечена как использованная: {topic}")

if __name__ == "__main__":
    main()
