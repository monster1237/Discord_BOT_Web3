import os
import json
import re
import sqlite3
import requests
import discord
from discord.ext import commands
from datetime import datetime
import pytz
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

# 获取涨跌幅信息和社交信息
async def get_token_info(address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
    response = requests.get(url)
    data = response.json()

    # 获取第一个配对的数据
    pair_data = data['pairs'][0] if data['pairs'] else {}

    # 获取基本信息
    token_name = pair_data.get('baseToken', {}).get('name', '无')
    current_price = float(pair_data.get('priceUsd', '0'))  # 确保current_price是浮点数
    total_supply = float(pair_data.get('liquidity', {}).get('base', '0'))
    volume_24h = float(pair_data.get('volume', {}).get('h24', '0'))
    liquidity = float(pair_data.get('liquidity', {}).get('usd', '0'))

    # 初始化涨跌幅信息
    price_change_info = {
        'm5': pair_data.get('priceChange', {}).get('m5', '无'),
        'h1': pair_data.get('priceChange', {}).get('h1', '无'),
        'h6': pair_data.get('priceChange', {}).get('h6', '无'),
        'h24': pair_data.get('priceChange', {}).get('h24', '无')
    }

    # 初始化社交信息
    social_info = ""
    for social in pair_data.get('info', {}).get('socials', []):
        social_type = social.get('type', '').title()
        social_url = social.get('url', '无')
        social_info += f"{social_type}: {social_url}\n" if social_type and social_url else ""

    # 计算代币创建时间与当前日期的差异（转换为+8时区）
    tz_shanghai = pytz.timezone('Asia/Shanghai')
    pair_created_at = datetime.fromtimestamp(pair_data.get('pairCreatedAt', 0) / 1000, tz_shanghai)
    time_since_creation = datetime.now(tz_shanghai) - pair_created_at
    days_since_creation = time_since_creation.days
    hours_since_creation = time_since_creation.seconds // 3600
    minutes_since_creation = (time_since_creation.seconds // 60) % 60

    # 构建并返回消息内容
    message_content = f"**名称**: {token_name}\n" \
                      f"**现在价格**: ${current_price:,.8f}\n" \
                      f"**5分钟涨跌幅**: {price_change_info['m5']}%\n" \
                      f"**1小时涨跌幅**: {price_change_info['h1']}%\n" \
                      f"**6小时涨跌幅**: {price_change_info['h6']}%\n" \
                      f"**24小时涨跌幅**: {price_change_info['h24']}%\n" \
                      f"**创建时间**: {pair_created_at.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)\n" \
                      f"**距离时间**: {days_since_creation}天 {hours_since_creation}小时 {minutes_since_creation}分钟\n" \
                      f"**24小时交易量**: {volume_24h:,.2f}\n" \
                      f"**流动性**: ${liquidity:,.2f}\n" \
                      f"**代币总数量**: {total_supply:,.0f}\n\n" \
                      f"**社交**:\n{social_info}\n" \
                      f"**网址**: <{pair_data.get('url', '无')}>"
    token_image_url = pair_data.get('info', {}).get('imageUrl', '')
    return message_content, token_image_url

# 当机器人准备好时触发
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
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
            token_info_message, token_image_url = await get_token_info(solana_address)
            log_address(message.author.id, message.author.name, solana_address)
            await message.channel.send(token_info_message)
            if token_image_url != '无':
                await message.channel.send(token_image_url)  # 发送图片URL
            return

    # 处理Ethereum地址
    match_eth = re.search(eth_address_pattern, message.content)
    if match_eth:
        eth_address = match_eth.group()
        token_info_message, token_image_url = await get_token_info(eth_address)
        log_address(message.author.id, message.author.name, eth_address)
        await message.channel.send(token_info_message)
        if token_image_url != '无':
            await message.channel.send(token_image_url)  # 发送图片URL
        return

    # 处理查询命令
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
