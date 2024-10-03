import os
import discord
from discord.ext import commands, tasks
import requests
import datetime
import openai
from dotenv import load_dotenv
import random

# Load environment variables
load_dotenv()

# Use environment variables for sensitive information
TOKEN = os.getenv('DISCORD_TOKEN')
CMC_API_KEY = os.getenv('CMC_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize OpenAI
openai.api_key = OPENAI_API_KEY

# Set up the bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Function to fetch global market data
def get_global_market_data():
    try:
        url = 'https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest'
        headers = {'X-CMC_PRO_API_KEY': CMC_API_KEY}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()['data']
    except requests.RequestException as e:
        print(f"Error fetching global market data: {e}")
        return None

# Function to fetch specific cryptocurrency data
def get_crypto_data(coin_symbol):
    try:
        url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
        params = {'symbol': coin_symbol, 'convert': 'USD'}
        headers = {'X-CMC_PRO_API_KEY': CMC_API_KEY}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()['data'][coin_symbol]
    except requests.RequestException as e:
        print(f"Error fetching data for {coin_symbol}: {e}")
        return None

# Function to get top movers and volume changes
def get_top_movers_and_volumes(limit=5):
    try:
        url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
        params = {'start': '1', 'limit': '100', 'convert': 'USD'}
        headers = {'X-CMC_PRO_API_KEY': CMC_API_KEY}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()['data']
        
        # Sort by percent change
        sorted_by_change = sorted(data, key=lambda x: x['quote']['USD']['percent_change_24h'], reverse=True)
        top_gainers = sorted_by_change[:limit]
        top_losers = sorted_by_change[-limit:]
        
        # Sort by volume change
        sorted_by_volume = sorted(data, key=lambda x: x['quote']['USD']['volume_change_24h'], reverse=True)
        high_volume_increase = sorted_by_volume[:limit]
        high_volume_decrease = sorted_by_volume[-limit:]
        
        return top_gainers, top_losers, high_volume_increase, high_volume_decrease
    except requests.RequestException as e:
        print(f"Error fetching top movers and volumes: {e}")
        return [], [], [], []

# Function to split long messages
def split_message(message, max_length=1900):
    if len(message) <= max_length:
        return [message]
    parts = []
    while len(message) > max_length:
        split_index = message.rfind('\n', 0, max_length)
        if split_index == -1:
            split_index = max_length
        parts.append(message[:split_index])
        message = message[split_index:].lstrip()
    if message:
        parts.append(message)
    return parts

# Function to generate multiple tweet-sized insights
def generate_tweets(report, num_tweets=5):
    try:
        messages = [
            {"role": "system", "content": "You are a friendly crypto market expert who provides clear, engaging, and valuable insights. Your tweets should be easy to understand, informative, and occasionally witty. Use $TICKER format for cryptocurrencies and include relevant emojis."},
            {"role": "user", "content": f"Based on this market report, generate {num_tweets} unique, engaging tweets (max 280 characters each) that provide different insights or perspectives on the current crypto market situation. Focus on key trends, significant price or volume changes, and potential impacts. Each tweet should be followed by a relevant news link (use 'https://example.com' as a placeholder):\n\n{report}"}
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=400 * num_tweets
        )
        tweets = response['choices'][0]['message']['content'].strip().split('\n\n')
        return [tweet.strip() for tweet in tweets if tweet.strip()]
    except Exception as e:
        print(f"Error generating tweets: {e}")
        return ["Unable to generate tweet insights at this time. We'll be back with more crypto updates soon!"]

# Function to get a random crypto fact
def get_crypto_fact():
    facts = [
        "Did you know? The first real-world Bitcoin transaction was for two pizzas, costing 10,000 BTC in 2010!",
        "Fun fact: 'HODL' originated from a typo of 'HOLD' in a Bitcoin forum, now meaning 'Hold On for Dear Life'!",
        "Crypto trivia: Ethereum's creator, Vitalik Buterin, was inspired by World of Warcraft to create a decentralized system!",
        "Believe it or not, there's a cryptocurrency named after Dogecoin's mascot's nemesis - it's called Catcoin!",
        "The term 'Altcoin' simply means 'alternative to Bitcoin'. There are thousands of them now!",
    ]
    return random.choice(facts)

# Function to generate market report
async def generate_market_report():
    global_data = get_global_market_data()
    if not global_data:
        return "Error: Unable to fetch global market data. We'll try again soon!"

    total_market_cap = global_data['quote']['USD']['total_market_cap']
    total_market_cap_yesterday = global_data['quote']['USD']['total_market_cap_yesterday']
    market_change_24h = ((total_market_cap - total_market_cap_yesterday) / total_market_cap_yesterday) * 100

    coins = ['BTC', 'ETH', 'BNB', 'ADA', 'XRP']
    coin_data = {}
    for coin in coins:
        data = get_crypto_data(coin)
        if data:
            coin_data[coin] = {
                'price_change': data['quote']['USD']['percent_change_24h'],
                'volume': data['quote']['USD']['volume_24h'],
                'volume_change': data['quote']['USD']['volume_change_24h']
            }

    top_gainers, top_losers, high_volume_increase, high_volume_decrease = get_top_movers_and_volumes()

    report = f"🚀 **Crypto Market Insights - {datetime.date.today()}** 🚀\n\n"
    report += f"💹 Overall Market: {market_change_24h:.2f}% in 24h\n\n"
    
    report += "🏆 **Top Performers:**\n"
    for coin in top_gainers[:3]:
        report += f"${coin['symbol']}: +{coin['quote']['USD']['percent_change_24h']:.2f}% (https://coinmarketcap.com/currencies/{coin['slug']})\n"
    
    report += "\n😰 **Struggling Coins:**\n"
    for coin in top_losers[:3]:
        report += f"${coin['symbol']}: {coin['quote']['USD']['percent_change_24h']:.2f}% (https://coinmarketcap.com/currencies/{coin['slug']})\n"

    report += f"\n🔑 **Key Coins:**\n"
    for coin, data in coin_data.items():
        report += f"${coin}: Price: {data['price_change']:.2f}%, Volume: ${data['volume']:,.0f} ({data['volume_change']:.2f}% change)\n"
        report += f"https://coinmarketcap.com/currencies/{coin.lower()}\n"

    report += f"\n📊 **Volume Movers:**\n"
    report += "Highest Volume Increase:\n"
    for coin in high_volume_increase[:3]:
        report += f"${coin['symbol']}: {coin['quote']['USD']['volume_change_24h']:.2f}% increase\n"
    report += "\nHighest Volume Decrease:\n"
    for coin in high_volume_decrease[:3]:
        report += f"${coin['symbol']}: {coin['quote']['USD']['volume_change_24h']:.2f}% decrease\n"

    report += f"\n💡 **Crypto Fact of the Day:**\n{get_crypto_fact()}\n"

    tweets = generate_tweets(report)
    report += f"\n🐦 **Today's Market Insights:**\n"
    for tweet in tweets:
        report += f"{tweet}\n\n"

    return report

# A task to send daily market reports
@tasks.loop(hours=24)
async def send_daily_market_report():
    channel = bot.get_channel(1290650499779133501)  # Your actual Discord channel ID
    report = await generate_market_report()
    for part in split_message(report):
        await channel.send(part)

# Command to get on-demand report
@bot.command(name='report')
async def get_report(ctx):
    await ctx.send("Generating market insights... Stay tuned!")
    report = await generate_market_report()
    for part in split_message(report):
        await ctx.send(part)

# Start the daily report task when the bot is ready
@bot.event
async def on_ready():
    send_daily_market_report.start()
    print(f'{bot.user} has connected to Discord!')

# Run the bot
bot.run(TOKEN)