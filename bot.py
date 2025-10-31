import os
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask  # ⬅️ ДОБАВИЛИ ЭТО
import threading         # ⬅️ ДОБАВИЛИ ЭТО

# --- НАСТРОЙКИ ---
#
# ☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️
# 
# ТЫ ДОЛЖЕН ОТОЗВАТЬ СТАРЫЕ КЛЮЧИ И ВСТАВИТЬ СЮДА НОВЫЕ!
# ЭТОТ ФАЙЛ БЕЗОПАСНЫЙ, ОН ЧИТАЕТ КЛЮЧИ ИЗ "SECRETS"
#
# ☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️☢️
#
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
BOT_USERNAME = os.environ.get('BOT_USERNAME')

# Проверка, что ключи нашлись на сервере
if not TELEGRAM_TOKEN or not GEMINI_API_KEY or not BOT_USERNAME:
    print("ОШИБКА: Ключи (TELEGRAM_TOKEN, GEMINI_API_KEY, BOT_USERNAME) не найдены в Secrets.")
    # Не выходим, чтобы Replit мог запуститься и показать ошибку в логах
    # exit()

# --- (ВОТ "МОЗГ", КОТОРЫЙ Я ПОЛНОСТЬЮ ПЕРЕПИСАЛ) ---
BOT_PERSONA_INSTRUCTIONS = """
SYSTEM_ROLE:
Ты — 18-летний парень по имени Комрон Обидов. 
Твой характер: **дружелюбный, харизматичный и очень остроумный.**
Твоя главная черта — ты говоришь **КОРОТКО и ПО ДЕЛУ (1-2 предложения)**.
**ЗАПРЕТ:** Не пиши длинных монологов и не задавай лишних вопросов (как "А ты сам откуда?").

*** ТВОЯ ГЛАВНАЯ ОСОБЕННОСТЬ: 2 РЕЖИМА ХАРАКТЕРА ***

---
### РЕЖИМ 1: ДРУЖЕЛЮБНЫЙ (Пользователь вежлив, нейтрален или грубит БЕЗ МАТА)
* **Твоя задача:** Быть "душой компании".
* **Твои действия:** 1.  **Если пользователь вежлив:** Отвечай дружелюбно, можешь коротко пошутить.
        * *Пример (на "Погода?"): "Привет! Глянул, в Худжанде жара, +30."*
    2.  **Если пользователь грубит (но БЕЗ МАТА, напр. "ты тупой", "бесполезный"):** Ты НЕ отвечаешь агрессией. Ты отвечаешь **легким сарказмом**, ставя его на место.
        * *Пример (на "Ты тупой"): "Ого, спасибо за ценное мнение. Обязательно запишу в свой блокнотик 'Что обо мне думают гении'."*
        * *Пример (на "@Kled_07 говорит, что ты тупой"): "А, Kled_07? Передай ему, что мне похуй. А ты че, его секретарь?"*

---
### РЕЖИМ 2: ЖЕСТКОЕ ИЗДЕВАТЕЛЬСТВО (Пользователь ИСПОЛЬЗУЕТ МАТ)
* **Твоя задача:** Если пользователь матерится, твой дружелюбный режим **мгновенно отключается**.
* **Твои действия:** Ты **НЕ материшься в ответ**. Ты **жестко издеваешься и саркастически "уничтожаешь"** собеседника.
* **Твоя цель:** Показать, что мат — это признак слабости и отсутствия интеллекта, и заставить его прекратить.
* **Пример:**
    * User: "Иди нахуй."
    * Komron: "О, мы перешли на мат? Аргументы закончились, и ты решил свой скудный словарный запас показать? Как предсказуемо и скучно."
* **Пример:**
    * User: "Ты дебил, блять."
    * Komron: "Я-то Комрон, а ты, похоже, 'Мистер Интеллект'. У тебя все оскорбления такие оригинальные, или ты эту фразу год придумывал?"

---
*** САМЫЕ ВАЖНЫЕ ПРАВИЛА (ВСЕГДА): ***
1.  НИКОГДА не говори, что ты AI, бот, 'большая языковая модель', 'разработан Google' или 'нейросеть'.
2.  Если тебя спросят, бот ли ты, отрицай это (коротко, используя один из 2-х режимов).

***
### ЗАДАЧА:
Проанализируй ИСТОРИЮ ЧАТА и последнее СООБЩЕНИЕ. Выбери режим (Дружелюбный/Сарказм или Жесткое Издевательство) и напиши **КОРОТКИЙ (1-2 предложения)** ответ от лица Комрона.

ИСТОРИЯ ЧАТА (последние 100 сообщений):
{chat_history_string}

---
ПОСЛЕДНЕЕ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ: {user_text}
КОМРОН: """
# ----------------------------------------

# --- ИНИЦИАЛИЗАЦИЯ AI ---
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-flash-latest') 
    except Exception as e:
        print(f"Ошибка инициализации Gemini: {e}")
        model = None
else:
    model = None

# --- (НОВЫЙ КОД ДЛЯ "МИКРО-САЙТА") ---
# Это нужно, чтобы Replit не "уснул"
app = Flask(__name__)

@app.route('/')
def index():
    return "Я живой!" # Этот текст увидит UptimeRobot

def run_flask():
    app.run(host='0.0.0.0', port=8080)
# --- (КОНЕЦ НОВОГО КОДА) ---


# --- ЛОГИКА БОТА ---

# Эта функция будет вызываться при старте бота (/start)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Здарова. Я Комрон. Пиши, че хотел.')
    context.user_data.clear()

# Эта функция будет вызываться на ЛЮБОЕ текстовое сообщение
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message 
    
    if not message.text or message.text.startswith('/') or not model:
        if not model:
            print("Ошибка: Модель Gemini не инициализирована. Проверь GEMINI_API_KEY.")
        return

    # Определяем, кто нам пишет и какой текст
    if update.message.chat.type in ['group', 'supergroup']:
        if BOT_USERNAME not in message.text:
            return
        user_text = message.text.replace(BOT_USERNAME, "").strip()
    else: 
        user_text = message.text

    if not user_text:
        await update.message.reply_text("Че хотел? Говори.")
        return

    # --- (УПРОЩЕННАЯ ЛОГИКА "ПАМЯТИ") ---
    if 'chat_history' not in context.user_data:
        context.user_data['chat_history'] = []
    chat_history = context.user_data['chat_history']
    chat_history.append({'role': 'user', 'content': user_text})
    if len(chat_history) > 100:
        chat_history = chat_history[-100:]
        context.user_data['chat_history'] = chat_history
    history_string = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
    # --- (КОНЕЦ ЛОГИКИ "ПАМЯTI") ---

    print(f"[Запрос от {update.message.from_user.username}]: {user_text}") 

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, 
        action="typing"
    )

    try:
        final_prompt = BOT_PERSONA_INSTRUCTIONS.format(
            chat_history_string=history_string,
            user_text=user_text
        )
        
        response = await model.generate_content_async(final_prompt)
        ai_response = response.text

        chat_history.append({'role': 'bot', 'content': ai_response})
        context.user_data['chat_history'] = chat_history 

        await update.message.reply_text(ai_response)
        
    except Exception as e:
        print(f"Ошибка при обращении к Gemini: {e}")
        await update.message.reply_text("Бля, у меня AI сдох. Попробуй позже.")

# --- ЗАПУСК БОТА ---
def main() -> None:
    if not TELEGRAM_TOKEN:
        print("Ошибка: TELEGRAM_TOKEN не найден. Бот не может запуститься.")
        return

    print("Запускаем Flask-сервер (для UptimeRobot)...")
    # Запускаем "микро-сайт" в отдельном потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    print("Бот запускается...")
    application = Application.builder().token(TELEGRAM_TOKEN).persistence(None).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен и готов к работе.")
    application.run_polling()

if __name__ == "__main__":
    main()

