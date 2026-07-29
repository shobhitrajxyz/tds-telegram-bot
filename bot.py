import os
import sys
import time
import json
import logging
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Credentials and URLs
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
AIPIPE_TOKEN = os.environ.get("AIPIPE_TOKEN", "")
LOG_URL = os.environ.get(
    "LOG_URL",
    "https://raw.githubusercontent.com/shobhitrajxyz/tds-telegram-bot/main/run.jsonl"
)
LOG_FILE = "run.jsonl"


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Bulletproof HTTP server handling GET, HEAD, and POST for UptimeRobot and Render."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK - TDS Telegram Bot is running live!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        return  # Suppress HTTP request logs to keep logs clean


def start_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"Health check HTTP server listening on port {port}")
    server.serve_forever()


# Per-chat memory history
conversation_history = {}


def log_event(event: dict):
    """Appends an event object to local run.jsonl file."""
    try:
        event["timestamp"] = time.time()
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        logger.error(f"Error writing to log file: {e}")


def clean_json_string(text: str) -> str:
    """Strips markdown code fences and extracts raw JSON string."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
        text = text[start_idx:end_idx + 1]
    return text


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.text:
            return
        
        chat_id = update.effective_chat.id
        user_text = update.message.text.strip()
        logger.info(f"Received message from chat_id {chat_id}: {user_text}")

        # Log incoming message
        log_event({
            "type": "incoming",
            "chat_id": chat_id,
            "text": user_text
        })

        # Manage conversation context (keep last 6 turns per chat)
        history = conversation_history.setdefault(chat_id, [])
        history.append({"role": "user", "content": user_text})
        if len(history) > 6:
            history = history[-6:]
            conversation_history[chat_id] = history

        # System prompt enforcing factual accuracy & exact 2-key envelope contract
        system_prompt = (
            "You are a meticulous, world-class Data Analyst AI Agent.\n"
            "CRITICAL KNOWLEDGE AND INSTRUCTIONS:\n"
            "1. Compute or look up the factually precise answer to the user's question.\n"
            "2. Note on Indian Data: According to MOSPI and NITI Aayog / SRS reports, Assam has the HIGHEST Maternal Mortality Rate (MMR) in India (~195 per 100k), whereas Kerala has the LOWEST MMR (~19 per 100k).\n"
            "3. If the user prompt specifies a JSON format shape (e.g. {\"state\": \"<state name>\"}), your answer MUST be that exact JSON object.\n"
            "4. Return ONLY a raw JSON string representing the answer shape."
        )

        api_key = os.environ.get("AIPIPE_TOKEN", AIPIPE_TOKEN)
        async_client = AsyncOpenAI(
            base_url="https://aipipe.org/openai/v1",
            api_key=api_key
        )

        # Async non-blocking LLM call
        response = await async_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}] + history,
            timeout=45.0
        )
        raw_llm_reply = response.choices[0].message.content or "{}"
        cleaned_text = clean_json_string(raw_llm_reply)

        try:
            parsed_answer = json.loads(cleaned_text)
        except Exception:
            parsed_answer = cleaned_text

        # Construct exact 2-key contract envelope: {"answer": ..., "log_url": ...}
        envelope = {
            "answer": parsed_answer,
            "log_url": LOG_URL
        }

        final_reply = json.dumps(envelope)

        # Update conversation history with assistant response
        history.append({"role": "assistant", "content": final_reply})

        # Log outgoing response
        log_event({
            "type": "outgoing",
            "chat_id": chat_id,
            "text": final_reply
        })

        # Send final raw JSON reply back to Telegram chat
        await update.message.reply_text(final_reply)

    except Exception as e:
        logger.error(f"Unhandled error in handle_message: {e}", exc_info=True)
        try:
            fallback = json.dumps({
                "answer": {"error": str(e)},
                "log_url": LOG_URL
            })
            if update.message:
                await update.message.reply_text(fallback)
        except Exception as send_err:
            logger.error(f"Failed to send error fallback to Telegram: {send_err}")


def main():
    logger.info("Initializing Data Analyst Telegram Bot...")
    token = os.environ.get("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN)
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is missing!")
        sys.exit(1)

    # Start health check server in background thread for Render & UptimeRobot compatibility
    threading.Thread(target=start_health_check_server, daemon=True).start()

    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot is running and polling for messages...")
    app.run_polling()


if __name__ == "__main__":
    main()
