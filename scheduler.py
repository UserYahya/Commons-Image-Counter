import os
import json
import telegram
from bot import get_file_counts_by_category, load_config

async def send_daily_counts():
    bot = telegram.Bot(token=os.environ["BOT_TOKEN"])
    cfg = load_config()
    for cid, category in cfg.items():
        counts = get_file_counts_by_category(category)
        total = sum(counts.values())
        lines = "\n".join([f"• {k} – {v} file(s)" for k, v in counts.items()])
        msg = f"📊 Daily update:\n'{category}' has {total} files.\n\n{lines}"
        await bot.send_message(chat_id=cid, text=msg)

if __name__ == "__main__":
    import asyncio
    asyncio.run(send_daily_counts())
