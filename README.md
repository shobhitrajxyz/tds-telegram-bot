# Data Analyst Telegram Bot (TDS Project 1 — Q5)

Automated Data Analyst Telegram Bot for IIT Madras Tools in Data Science (TDS) Project 1.

## Repository Details
* **GitHub Repository**: `https://github.com/shobhitrajxyz/tds-telegram-bot`
* **Public Log URL**: `https://raw.githubusercontent.com/shobhitrajxyz/tds-telegram-bot/main/run.jsonl`

## Architecture & Features
* **Live Telegram Polling**: Listens for incoming queries using `python-telegram-bot`.
* **LLM Data Analyst Engine**: Powered by `gpt-5-mini` via `https://aipipe.org/openai/v1`.
* **Strict JSON Response**: Strips markdown formatting and outputs only valid raw JSON objects matching requested schemas.
* **Audit Logging**: Every incoming and outgoing message is logged to `run.jsonl` with timestamps.
* **Mandatory Field Injection**: Injects `"log_url"` field pointing to the direct raw URL of `run.jsonl`.

## Environment Variables
* `TELEGRAM_BOT_TOKEN`: Token obtained from `@BotFather`
* `AIPIPE_TOKEN`: Token obtained from `aipipe.org/login`
* `LOG_URL`: Direct raw URL to `run.jsonl`

## Local Running
```bash
pip install -r requirements.txt
python bot.py
```
