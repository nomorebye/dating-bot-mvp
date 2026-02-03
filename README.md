# Telegram DM Dating Bot MVP

## Setup
1. `python -m venv .venv`
2. `pip install -r requirements.txt`
3. `.env` 파일을 만들고 `TELEGRAM_BOT_TOKEN` 값을 설정합니다.

```
TELEGRAM_BOT_TOKEN=YOUR_TOKEN
```

## Run
`python -m adapters.telegram_bot`

## Test
`pytest -q`
