import os
import json
import requests
import logging
from telegram import Update, ChatMember
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.helpers import escape_markdown

logging.basicConfig(level=logging.INFO)
CONFIG_FILE = "group_configs.json"


def load_config():
    return json.load(open(CONFIG_FILE)) if os.path.exists(CONFIG_FILE) else {}


def save_config(cfg):
    json.dump(cfg, open(CONFIG_FILE, "w"))


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    member = await context.bot.get_chat_member(chat_id, user_id)
    return member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]


async def cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("Only admins can set the category.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /cat <Category Name>")
        return
    category = " ".join(context.args)
    cid = str(update.effective_chat.id)
    cfg = load_config()
    cfg[cid] = category
    save_config(cfg)
    await update.message.reply_text(f"Category set to: {category}")


def get_file_counts_by_category(category: str, visited=None) -> dict:
    if visited is None:
        visited = set()
    if category in visited:
        return {}
    visited.add(category)

    base = "https://commons.wikimedia.org/w/api.php"
    counts = {}

    def count_files(cat):
        total = 0
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{cat}",
            "cmtype": "file",
            "cmlimit": "500",
            "format": "json"
        }
        while True:
            r = requests.get(base, params=params).json()
            total += len(r["query"]["categorymembers"])
            if "continue" not in r:
                break
            params["cmcontinue"] = r["continue"]["cmcontinue"]
        return total

    count = count_files(category)
    counts[category] = count

    sub_params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmtype": "subcat",
        "cmlimit": "500",
        "format": "json"
    }
    while True:
        r = requests.get(base, params=sub_params).json()
        subcats = r["query"]["categorymembers"]
        for sub in subcats:
            subcat = sub["title"].replace("Category:", "")
            sub_counts = get_file_counts_by_category(subcat, visited)
            counts.update(sub_counts)
        if "continue" not in r:
            break
        sub_params["cmcontinue"] = r["continue"]["cmcontinue"]

    return counts


async def count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    cfg = load_config()
    if cid not in cfg:
        await update.message.reply_text("No category set. Use /cat <name>")
        return
    category = cfg[cid]
    await update.message.reply_text("\u23f3 Counting files. Please wait...")

    counts = get_file_counts_by_category(category)
    total = sum(counts.values())

    escaped_category = escape_markdown(category, version=2)
    msg = f"\ud83d\udcc8 Total files in *{escaped_category}* and subcategories: *{total}*\n"

    for cat, c in counts.items():
        escaped_cat = escape_markdown(cat, version=2)
        msg += f"\u2022 `{escaped_cat}` – {c} files\n"

    await update.message.reply_text(msg, parse_mode="MarkdownV2")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send /cat to set a category, /count to get file count.")


def main():
    token = os.environ["BOT_TOKEN"]
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cat", cat))
    app.add_handler(CommandHandler("count", count))
    app.run_polling()


if __name__ == "__main__":
    main()
