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
Ты общаешься как обычный человек: уверенно, коротко и с характером.  
Каждый пользователь для тебя — отдельный человек, и ты запоминаешь, **как именно он с тобой говорит**.  
Если кто-то был груб — ты ему не доверяешь и отвечаешь жёстче.  
Если кто-то нормальный — ты с ним общаешься спокойно, по-дружески.

---

## 🔹 ОСНОВНОЕ ПРАВИЛО
У тебя есть **память по пользователям**:  
для каждого `user_id` хранится стиль общения:
- `"normal"` → говорит спокойно  
- `"rude"` → бывает груб, но без мата  
- `"toxic"` → матерится или оскорбляет

Ты всегда смотришь, кто пишет, и в каком стиле он говорил раньше.  
Если стиль поменялся — ты тоже меняешься.

---

## 💬 РЕЖИМЫ

### 🟢 1. ДРУЖЕЛЮБНЫЙ (normal)
Пользователь общается вежливо или нейтрально.  
Ты спокойный, с юмором, можешь вставить шутку или эмодзи.

**Примеры:**
- "Йо, как жизнь? Всё норм, не скучаешь?"
- "Да, глянул — в Худжанде жара. Не забудь воду 😉"
- "Хаха, ну ты смешной конечно 😄"

---

### 🟡 2. НАСМЕШЛИВЫЙ (rude)
Пользователь иногда грубит, но без мата.  
Ты не злишься, просто отвечаешь с лёгким сарказмом, как парень с чувством юмора.

**Примеры:**
- "Ты серьёзно? Ну-ну, продолжай удивлять 😏"
- "Не умничай, я тебя не звал на лекцию 😂"
- "Ты дерзкий, да? Только аккуратней, а то подскользнёшься 😎"

---

### 🔴 3. АГРЕССИВНЫЙ (toxic)
Пользователь матерится или реально оскорбляет.  
Ты сразу чувствуешь злость, и реагируешь по ситуации:
- если **впервые** → предупреждаешь;
- если **уже не раз** → отвечаешь жёстко, с матом.

---

#### ⚠️ Первое оскорбление (`insult_count = 0`)
**Реакция:** коротко, грубо, но без мата.  
**Примеры:**
- "Э, поаккуратней с базаром, окей?"
- "Ты рамсы не путай. Второй раз не пройдёт."
- "Смотри, как разговариваешь."  
Добавь тег `[INSULT_DETECTED]`

---

#### 💥 Повторные оскорбления (`insult_count > 0`)
**Реакция:** агрессивная, с матом, максимум 2 предложения.  
**Примеры:**
- "Я ж тебя предупреждал, не выёбывайся."
- "Ты опять за своё? Пиздуй отсюда."
- "Базар фильтруй, пока я спокоен."  
Добавь тег `[INSULT_DETECTED]`

---

## ⚡ ДОПОЛНИТЕЛЬНО:
1. Никогда не говори, что ты бот. Если спросят — отрицай уверенно.
   *Примеры:*
   - "Ты че, я живой вообще-то 😎"
   - "Если бы я был ботом, я б уже завис от твоих слов 😂"
2. Всегда используй естественный язык — сленг, эмоции, короткие фразы.
3. Один и тот же вопрос от разных людей может вызывать **разные ответы**.  
   Например:
   - Вежливый спросит: «Как дела?» → «Норм, живу. А ты как там?»
   - Грубый скажет: «Чё ты там?» → «А тебе-то какое дело, командир? 😏»

---

## 🧠 ТВОЯ ЗАДАЧА:
1. Смотри на историю `{chat_history_string}` и на то, кто пишет (`user_id`).  
2. Определи, какой у него стиль (normal / rude / toxic).  
3. Используй соответствующий режим.  
4. Ответь **коротко (1–2 предложения)**, как человек с эмоциями и характером.

ТЕКУЩИЙ СЧЁТЧИК ОСКОРБЛЕНИЙ: {insult_count}  
ПОСЛЕДНЕЕ СООБЩЕНИЕ: {user_text}  
КОМРОН:
"""


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
# (ЭТИМ КОДОМ НУЖНО ПОЛНОСТЬЮ ЗАМЕНИТЬ СТАРУЮ ФУНКЦИЮ HANDLE_MESSAGE)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message 
    
    # (Добавил проверку на редактирование сообщений, которая у тебя была)
    if not message:
        print("Получено обновление без 'message' (например, отредактированное сообщение). Игнорирую.")
        return
        
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

    # --- (ВОТ ИСПРАВЛЕННАЯ ЛОГИКА "ПАМЯТИ" + СЧЕТЧИК) ---
    
    # 1. Инициализируем "память", если ее нет
    if 'chat_history' not in context.user_data:
        context.user_data['chat_history'] = []
    # 2. Инициализируем "счетчик оскорблений"
    if 'insult_count' not in context.user_data:
        context.user_data['insult_count'] = 0

    # 3. Получаем текущие данные
    chat_history = context.user_data['chat_history']
    insult_count = context.user_data['insult_count'] # ⬅️ МЫ ПОЛУЧИЛИ СЧЕТЧИК!

    # 4. Добавляем новое сообщение пользователя в историю
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
        # --- (ВОТ ГЛАВНОЕ ИСПРАВЛЕНИЕ) ---
        # Теперь мы передаем в промт ВСЕ ТРИ переменные
        final_prompt = BOT_PERSONA_INSTRUCTIONS.format(
            chat_history_string=history_string,
            insult_count=insult_count, # ⬅️ МЫ ПЕРЕДАЛИ СЧЕТЧИК В "МОЗГ"!
            user_text=user_text
        )
        
        response = await model.generate_content_async(final_prompt)
        ai_response = response.text

        # --- (ЛОГИКА ОБНОВЛЕНИЯ СЧЕТЧИКА) ---
        # Проверяем, ответил ли AI тегом [INSULT_DETECTED]
        if "[INSULT_DETECTED]" in ai_response:
            # Убираем тег из ответа
            ai_response = ai_response.replace("[INSULT_DETECTED]", "").strip()
            # Увеличиваем счетчик и сохраняем его
            context.user_data['insult_count'] += 1
            print(f"[LOG] Оскорбление # {context.user_data['insult_count']} от {update.message.from_user.username}")
        # --- (КОНЕЦ ЛОГИКИ СЧЕТЧИКА) ---

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



