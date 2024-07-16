import os
import random
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events, sync
import sqlite3

# 加载环境变量
load_dotenv()
api_id = os.getenv('TELEGRAM_API_ID')
api_hash = os.getenv('TELEGRAM_API_HASH')
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

# 创建或连接到SQLite数据库
conn = sqlite3.connect('subjects.db')
c = conn.cursor()

# 创建数据表
c.execute('''CREATE TABLE IF NOT EXISTS subjects
             (id INTEGER PRIMARY KEY, subject TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS user_count
             (user_id INTEGER PRIMARY KEY, count INTEGER DEFAULT 0)''')
conn.commit()

# 初始化Telethon客户端
client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

@client.on(events.NewMessage(pattern='/add (.+)'))
async def add_subject(event):
    subject = event.pattern_match.group(1)
    c.execute('INSERT INTO subjects (subject) VALUES (?)', (subject,))
    conn.commit()
    await event.reply(f'已添加科目：{subject}')

@client.on(events.NewMessage(pattern='今天学什么'))
async def today_learn(event):
    c.execute('SELECT subject FROM subjects')
    subjects = c.fetchall()
    if subjects:
        subject = random.choice(subjects)[0]
        await event.reply(f'今天学习：{subject}')
        user_id = event.sender_id
        c.execute('INSERT OR IGNORE INTO user_count (user_id, count) VALUES (?, 0)', (user_id,))
        c.execute('UPDATE user_count SET count = count + 1 WHERE user_id = ?', (user_id,))
        conn.commit()
    else:
        await event.reply('没有可学习的科目，请先添加。')

@client.on(events.NewMessage(pattern='/howmanytimesdoilearn'))
async def how_many_times(event):
    user_id = event.sender_id
    c.execute('SELECT count FROM user_count WHERE user_id = ?', (user_id,))
    count = c.fetchone()
    if count:
        await event.reply(f'你已经学习了 {count[0]} 次')
    else:
        await event.reply('你还没有开始学习。')

# 运行客户端
print("Bot is running...")
client.run_until_disconnected()
