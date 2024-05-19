# -*- coding: utf-8 -*-
import os
import json
import re
import sqlite3
import requests
import discord
from discord.ext import commands
from solders.pubkey import Pubkey

# 设置Discord机器人的意图
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# 创建机器人实例
bot = commands.Bot(command_prefix='!', intents=intents)

# 从环境变量中获取API密钥
coinmarketcap_key = os.environ.get('COINMARKETCAP_API')
discordtoken = os.environ.get('DISCORD_BOT')

# 定义Solana和Ethereum地址的正则表达式模式
solana_address_pattern = r'[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]{32,44}'
eth_address_pattern = r'0x[a-fA-F0-9]{40}'

# Solana地址验证函数
def validate_solana_address(address):
    try:
        pubkey = Pubkey.from_string(address)
        return pubkey.is_on_curve()
    except ValueError:
        return False

# 初始化数据库
def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            username TEXT,
            address TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# 记录地址到数据库
def log_address(user_id, username, address):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT INTO addresses (user_id, username, address) VALUES (?, ?, ?)', (user_id, username, address))
    conn.commit()
    conn.close()

# 当机器人准备好时触发
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    init_db()

# 监听消息事件
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # 处理Solana地址
    match_solana = re.search(solana_address_pattern, message.content)
    if match_solana:
        solana_address = match_solana.group()
        if validate_solana_address(solana_address):
            sol_url = f"<https://dexscreener.com/Solana/{solana_address}>"
            log_address(message.author.id, message.author.name, solana_address)
            await message.channel.send(sol_url)  # 发送网址
        return

    # 处理Ethereum地址
    match_eth = re.search(eth_address_pattern, message.content)
    if match_eth:
        eth_address = match_eth.group()
        eth_url = f"<https://dexscreener.com/Ethereum/eth_address>"
        log_address(message.author.id, message.author.name, eth_address)
        await message.channel.send(eth_url)  # 发送网址
        return

    if '查询' in message.content:
        symbol = message.content.split('查询')[-1].strip()
        try:
            url_info = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol={symbol.upper()}"
            headers = {'X-CMC_PRO_API_KEY': coinmarketcap_key}
            response_info = requests.get(url_info, headers=headers)
            data_info = json.loads(response_info.text)['data'][symbol.upper()]

            url_links = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/info?symbol={symbol.upper()}"
            response_links = requests.get(url_links, headers=headers)
            data_links = json.loads(response_links.text)['data'][symbol.upper()]

            name = data_info['name']
            symbol = data_info['symbol']
            price = data_info['quote']['USD']['price']
            percent_change_1h = data_info['quote']['USD']['percent_change_1h']
            percent_change_24h = data_info['quote']['USD']['percent_change_24h']
            percent_change_7d = data_info['quote']['USD']['percent_change_7d']
            market_cap_rank = data_info['cmc_rank']
            total_supply = data_info['total_supply']
            circulating_supply = data_info['circulating_supply']
            website = data_links['urls']['website'][0] if data_links['urls']['website'] else '无'
            twitter = data_links['urls']['twitter'][0] if data_links['urls']['twitter'] else '无'
            discord = data_links['urls']['chat'][0] if data_links['urls']['chat'] else '无'

            response_message = f"**{name} ({symbol})**\n\n" \
                               f"价格: `${price:.8f}`\n" \
                               f"1小时涨跌幅: `{percent_change_1h:.1f}%`\n" \
                               f"24小时涨跌幅: `{percent_change_24h:.1f}%`\n" \
                               f"7天涨跌幅: `{percent_change_7d:.1f}%`\n" \
                               f"市值排名: `{market_cap_rank}`\n" \
                               f"发行总量: `{total_supply}`\n" \
                               f"流通数量: `{circulating_supply}`\n" \
                               f"项目方网站: <{website}>\n" \
                               f"Twitter: <{twitter}>\n" \
                               f"Discord: <{discord}>"

            await message.channel.send(response_message)
        except Exception as e:
            error_message = f"输入的代币 `{symbol}` 不存在或数据获取失败。"
            sent_message = await message.channel.send(error_message)
            print(f"Failed to fetch token data: {e}")
            await sent_message.delete(delay=60)

# 运行机器人
bot.run(discordtoken)
