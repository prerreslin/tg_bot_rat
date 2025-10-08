# Telegram PC Screenshot Bot

Минимальный бот, который работает на том ПК, где запущен, и по кнопке присылает скриншот.

## Установка (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Настройка
- Создайте `.env` рядом с `bot.py` (смотрите `.env.example`) и вставьте `BOT_TOKEN`.

## Запуск
```powershell
python .\bot.py
```

В Telegram отправьте `/start` и нажмите «📸 Скриншот». 
