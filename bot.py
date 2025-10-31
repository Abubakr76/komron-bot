import os
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- НАСТРОЙКИ ---
# Эти переменные бот будет "читать" из секретного хранилища сервера (Render)
# НЕ ВСТАВЛЯЙ СЮДА СВОИ КЛЮЧИ!
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
BOT_USERNAME = os.environ.get('BOT_USERNAME')

# Проверка, что ключи нашлись на сервере
if not TELEGRAM_TOKEN or not GEMINI_API_KEY or not BOT_USERNAME:
    print("ОШИБКА: Один или несколько ключей (TELEGRAM_TOKEN, GEMINI_API_KEY, BOT_USERNAME) не найдены в Environment.")
    exit()

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
genai.configure(api_key=GEMINI_API_KEY)

# Модель для ТЕКСТА
model = genai.GenerativeModel('gemini-flash-latest') 

# --- ЛОГИКА БОТА ---

# Эта функция будет вызываться при старте бота (/start)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Здарова. Я Комрон. Пиши, че хотел.')
    # При старте сбрасываем историю
    context.user_data.clear()

# Эта функция будет вызываться на ЛЮБОЕ текстовое сообщение
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message 
    
    if not message.text or message.text.startswith('/'):
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
    
    # 1. Инициализируем "память", если ее нет
    if 'chat_history' not in context.user_data:
        context.user_data['chat_history'] = []

    # 2. Получаем текущие данные
    chat_history = context.user_data['chat_history']

    # 3. Добавляем новое сообщение пользователя в историю
    chat_history.append({'role': 'user', 'content': user_text})
    
    # 4. Обрезаем историю, если она слишком длинная (храним 100 последних сообщений)
    if len(chat_history) > 100:
        chat_history = chat_history[-100:]
        context.user_data['chat_history'] = chat_history

    # 5. Готовим историю для отправки в AI (превращаем список в строку)
    history_string = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
    # --- (КОНЕЦ ЛОГИКИ "ПАМЯTI") ---

    print(f"[Запрос от {update.message.from_user.username}]: {user_text}") 

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, 
        action="typing"
    )

    try:
        # Теперь мы передаем в промт ДВА параметра
        final_prompt = BOT_PERSONA_INSTRUCTIONS.format(
            chat_history_string=history_string,
            user_text=user_text
        )
        
        response = await model.generate_content_async(final_prompt)
        ai_response = response.text

        # 6. Добавляем ответ бота в историю
        chat_history.append({'role': 'bot', 'content': ai_response})
        context.user_data['chat_history'] = chat_history # Сохраняем

        # 7. Отправляем ответ
        await update.message.reply_text(ai_response)
        
    except Exception as e:
        print(f"Ошибка при обращении к Gemini: {e}")
        await update.message.reply_text("Бля, у меня AI сдох. Попробуй позже.")

# --- ЗАПУСК БОТА ---
def main() -> None:
    print("Бот запускается...")
    # Указываем, что хотим хранить user_data
    application = Application.builder().token(TELEGRAM_TOKEN).persistence(None).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    
    # Добавляем обработчик всех текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем бота
    print("Бот запущен и готов к работе.")
    application.run_polling()

if __name__ == "__main__":
    main()