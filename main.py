import os
import random
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events
import sqlite3
import logging
from datetime import datetime

# 加载环境变量
load_dotenv()

# 日志设置
os.makedirs('logs', exist_ok=True)
today_date = datetime.now().strftime("%Y%m%d")
log_filename = f'logs/learnbot_{today_date}.log'
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler(log_filename, 'a'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

# 环境变量检查
api_id = os.getenv('TELEGRAM_API_ID')
api_hash = os.getenv('TELEGRAM_API_HASH')
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

if not all([api_id, api_hash, bot_token]):
    logger.error("Missing configuration for API ID, API Hash, or Bot Token.")
    exit(1)

# 创建或连接到SQLite数据库
conn = sqlite3.connect('subjects.db')
c = conn.cursor()

# 创建数据表
c.execute('''CREATE TABLE IF NOT EXISTS subjects
             (id INTEGER PRIMARY KEY, subject TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS user_count
             (user_id INTEGER PRIMARY KEY, count INTEGER DEFAULT 0)''')
c.execute('''CREATE TABLE IF NOT EXISTS completed_subjects
             (user_id INTEGER, subject_id INTEGER,
             FOREIGN KEY(subject_id) REFERENCES subjects(id),
             PRIMARY KEY(user_id, subject_id))''')
conn.commit()

# 初始化Telethon客户端
client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

@client.on(events.NewMessage(pattern='/add (.+)'))
async def add_subject(event):
    subject = event.pattern_match.group(1)
    c.execute('INSERT INTO subjects (subject) VALUES (?)', (subject,))
    conn.commit()
    logger.info(f"Added subject: {subject}")
    await event.reply(f'已添加科目：{subject}')

@client.on(events.NewMessage(pattern='/done (.+)'))
async def mark_done(event):
    subject = event.pattern_match.group(1)
    user_id = event.sender_id
    c.execute('SELECT id FROM subjects WHERE subject = ?', (subject,))
    subject_id = c.fetchone()
    if subject_id:
        c.execute('INSERT INTO completed_subjects (user_id, subject_id) VALUES (?, ?)', (user_id, subject_id[0]))
        conn.commit()
        logger.info(f"User {user_id} marked as done: {subject}")
        await event.reply(f'已标记完成科目：{subject}')
    else:
        logger.warning(f"Subject not found: {subject}")
        await event.reply(f'科目 {subject} 不存在。')

@client.on(events.NewMessage(pattern='今天学什么'))
async def today_learn(event):
    user_id = event.sender_id
    c.execute('SELECT id FROM subjects WHERE id NOT IN (SELECT subject_id FROM completed_subjects WHERE user_id = ?)', (user_id,))
    available_subjects = c.fetchall()
    if available_subjects:
        subject_id = random.choice(available_subjects)[0]
        c.execute('SELECT subject FROM subjects WHERE id = ?', (subject_id,))
        subject = c.fetchone()[0]
        logger.info(f"Recommended to user {user_id}: {subject}")
        await event.reply(f'今天学习：{subject}')
        c.execute('INSERT OR IGNORE INTO user_count (user_id, count) VALUES (?, 0)', (user_id,))
        c.execute('UPDATE user_count SET count = count + 1 WHERE user_id = ?', (user_id,))
        conn.commit()
    else:
        logger.info(f"User {user_id} has completed all subjects.")
        await event.reply('你已完成所有科目的学习。')

@client.on(events.NewMessage(pattern='/howmanytimesdoilearn'))
async def how_many_times(event):
    user_id = event.sender_id
    c.execute('SELECT count FROM user_count WHERE user_id = ?', (user_id,))
    count = c.fetchone()
    if count:
        logger.info(f"User {user_id} learning count queried: {count[0]}")
        await event.reply(f'你已经学习了 {count[0]} 次')
    else:
        logger.info(f"User {user_id} has not started learning.")
        await event.reply('你还没有开始学习。')

# 运行客户端
logger.info("Bot is running...")
client.run_until_disconnected()
