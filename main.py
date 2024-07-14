import os
import json
import re
import sqlite3
import requests
import discord
from discord.ext import commands
import discord as discord_module
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
    # 添加 queries 表的创建语句
    c.execute('''
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            username TEXT,
            query TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


# 记录地址到数据库
def log_address(user_id, username, address):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    try:
        c.execute(
            'INSERT INTO addresses (user_id, username, address) VALUES (?, ?, ?)',
            (user_id, username, address))
        conn.commit()
    except Exception as e:
        print(f"Error logging address: {e}")
    finally:
        conn.close()


# 记录查询到数据库
def log_query(user_id, username, query):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    try:
        c.execute(
            'INSERT INTO queries (user_id, username, query) VALUES (?, ?, ?)',
            (user_id, username, query))
        conn.commit()
    except Exception as e:
        print(f"Error logging query: {e}")
    finally:
        conn.close()

# 获取当日所有用户的查询记录
def get_today_queries():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        # 查询 addresses 表中的记录
        c.execute(
            'SELECT username, address FROM addresses WHERE timestamp >= date(?)',
            (today,))
        addresses = c.fetchall()
        # 查询 queries 表中的记录
        c.execute(
            'SELECT username, query FROM queries WHERE timestamp >= date(?)',
            (today,))
        queries = c.fetchall()
        # 合并所有记录
        all_records = addresses + queries
        return all_records
    except Exception as e:
        print(f"Error fetching today's queries: {e}")
        return []
    finally:
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
    current_price = float(pair_data.get('priceUsd',
                                        '0'))  # 确保current_price是浮点数
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
        social_info += f"{social_type}: <{social_url}>\n" if social_type and social_url else ""

    # 计算代币创建时间与当前日期的差异（转换为+8时区）
    tz_shanghai = pytz.timezone('Asia/Shanghai')
    pair_created_at = datetime.fromtimestamp(
        pair_data.get('pairCreatedAt', 0) / 1000, tz_shanghai)
    time_since_creation = datetime.now(tz_shanghai) - pair_created_at
    days_since_creation = time_since_creation.days
    hours_since_creation = time_since_creation.seconds // 3600
    minutes_since_creation = (time_since_creation.seconds // 60) % 60

    # 构建并返回消息内容
    message_content = f"**名称**: {token_name}\n" \
                      f"**地址**: {address}\n" \
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
            token_info_message, token_image_url = await get_token_info(
                solana_address)
            log_address(message.author.id, message.author.name, solana_address)  # 记录地址
            embed = discord_module.Embed(description=token_info_message)
            if token_image_url != '无':
                embed.set_image(url=token_image_url)
            await message.channel.send(embed=embed)
            return

    # 处理Ethereum地址
    match_eth = re.search(eth_address_pattern, message.content)
    if match_eth:
        eth_address = match_eth.group()
        token_info_message, token_image_url = await get_token_info(eth_address)
        log_address(message.author.id, message.author.name, eth_address)  # 记录地址
        embed = discord_module.Embed(description=token_info_message)
        if token_image_url != '无':
            embed.set_image(url=token_image_url)
        await message.channel.send(embed=embed)
        return

    # 处理查看记录命令
    if '查看记录' in message.content:
        all_records = get_today_queries()
        if all_records:
            records_str = "\n".join(
                f"{record[0]}: {record[1]}" for record in all_records)
            embed = discord_module.Embed(
                title="今日所有用户的查询记录",
                description=records_str)
            await message.channel.send(embed=embed)
        else:
            await message.channel.send("今天没有查询记录。")

    # 处理查询命令
    if '查询' in message.content:
        symbol = message.content.split('查询')[-1].strip()
        log_query(message.author.id, message.author.name, symbol)  # 记录查询
        try:
            # 首先尝试使用CoinMarketCap的API查询代币信息
            url_info = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/info?symbol={symbol.upper()}"
            headers = {'X-CMC_PRO_API_KEY': coinmarketcap_key}
            response_info = requests.get(url_info, headers=headers)
            if response_info.status_code == 200:
                data_info = response_info.json().get('data', {}).get(symbol.upper(), {})
                if data_info:
                    # 如果CoinMarketCap有结果，发送格式化的信息
                    name = data_info.get('name', '无')
                    symbol = data_info.get('symbol', '无')
                    urls = data_info.get('urls', {})
                    website = urls.get('website', [])[0] if urls.get('website') else '无'
                    twitter = urls.get('twitter', [])[0] if urls.get('twitter') else '无'
                    discord3 = urls.get('chat', [])[0] if urls.get('chat') and urls.get('chat') != [] else '无'
                    logo_url = data_info.get('logo')

                    # 现在获取财务信息
                    url_quotes = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol={symbol.upper()}"
                    response_quotes = requests.get(url_quotes, headers=headers)
                    if response_quotes.status_code == 200:
                        data_quotes = response_quotes.json().get('data', {}).get(symbol.upper(), {})
                        price = data_quotes.get('quote', {}).get('USD', {}).get('price')
                        percent_change_1h = data_quotes.get('quote', {}).get('USD', {}).get('percent_change_1h')
                        percent_change_24h = data_quotes.get('quote', {}).get('USD', {}).get('percent_change_24h')
                        percent_change_7d = data_quotes.get('quote', {}).get('USD', {}).get('percent_change_7d')
                        market_cap_rank = data_quotes.get('cmc_rank')
                        total_supply = data_quotes.get('total_supply')
                        circulating_supply = data_quotes.get('circulating_supply')

                        # 在尝试格式化之前检查价格是否为None
                        formatted_price = f"${price:.8f}" if price is not None else "无"
                        formatted_percent_change_1h = f"{percent_change_1h:.1f}%" if percent_change_1h is not None else "无"
                        formatted_percent_change_24h = f"{percent_change_24h:.1f}%" if percent_change_24h is not None else "无"
                        formatted_percent_change_7d = f"{percent_change_7d:.1f}%" if percent_change_7d is not None else "无"

                        embed = discord.Embed(title=f"{name} ({symbol})", color=0x1ABC9C)  # 颜色可以自定义
                        embed.set_thumbnail(url=logo_url)
                        embed.add_field(name="价格", value=formatted_price, inline=False)
                        embed.add_field(name="1小时涨跌幅", value=formatted_percent_change_1h, inline=True)
                        embed.add_field(name="24小时涨跌幅", value=formatted_percent_change_24h, inline=True)
                        embed.add_field(name="7天涨跌幅", value=formatted_percent_change_7d, inline=True)
                        embed.add_field(name="市值排名",
                                        value=f"{market_cap_rank}" if market_cap_rank is not None else "无",
                                        inline=True)
                        embed.add_field(name="发行总量", value=f"{total_supply:,.0f}" if total_supply is not None else "无",
                                        inline=True)
                        embed.add_field(name="流通数量",
                                        value=f"{circulating_supply:,.0f}" if circulating_supply is not None else "无",
                                        inline=True)
                        embed.add_field(name="项目方网站", value=website, inline=False)
                        embed.add_field(name="推特", value=twitter, inline=True)
                        embed.add_field(name="Discord", value=discord3, inline=True)

                        # 发送嵌入式消息
                        await message.channel.send(embed=embed)
                    else:
                        # 如果没有找到财务信息，只发送社交链接
                        embed = discord.Embed(title=f"{name} ({symbol})", color=0x1ABC9C)
                        embed.add_field(name="项目方网站", value=website, inline=False)
                        embed.add_field(name="推特", value=twitter, inline=True)
                        embed.add_field(name="Discord", value=discord3, inline=True)
                        await message.channel.send(embed=embed)
                else:
          # 如果CoinMarketCap API没有返回有效的代币信息，则使用DexScreener API
                    raise ValueError("CoinMarketCap API没有返回有效的代币信息。")
            else:
                raise ValueError("CoinMarketCap API请求失败。")
        except ValueError as ve:
            # CoinMarketCap API请求失败或没有返回有效信息，使用DexScreener API
            url_search = f"https://api.dexscreener.com/latest/dex/search/?q={symbol}"
            response_search = requests.get(url_search)
            search_results = json.loads(response_search.text)

            # 确保搜索结果不为空
            if search_results['pairs']:
                baseToken_address = search_results['pairs'][0]['baseToken']['address']
                # 调用get_token_info函数获取代币信息
                token_info_message, token_image_url = await get_token_info(baseToken_address)
                # 创建embed消息
                embed = discord.Embed(description=token_info_message)
                if token_image_url != '无':
                    embed.set_image(url=token_image_url)
                await message.channel.send(embed=embed)
            else:
                error_message = f"没有找到匹配的代币 `{symbol}`。"
                await message.channel.send(error_message)
        except Exception as e:
            # 处理其他异常
            error_message = f"输入的代币 `{symbol}` 不存在或数据获取失败。"
            await message.channel.send(error_message)
            print(f"Failed to fetch token data: {e}")

 # 运行机器人
bot.run(discordtoken)

