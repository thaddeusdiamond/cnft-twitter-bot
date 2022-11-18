import argparse
import json
import logging
import requests

from bs4 import BeautifulSoup
from datetime import datetime, time
from time import sleep

from listing_bot import configure_request_logging, generate_oauth_token, post_tweet

# General constants and logging
DEBUG_REQUESTS = False
LOG_LEVEL = logging.INFO

TOP_COLLECTIONS_CACHE = {}
LOVELACE_TO_ADA = 1000000.0

def get_tweet_header(header):
    return f"#WWStats🎙️🗣\n{header}\n\n"

def get_tweet_footer(footer):
    return f"[{footer}]\nStats powered by @WildTangz"

def top_twentyfive_aths():
    tweets = []
    top_collections = requests.get(
        'https://api.opencnft.io/1/rank',
        {'window': 'all'}
    ).json()['ranking']
    logging.info(TOP_COLLECTIONS_CACHE)
    for idx in range(25):
        collection = top_collections[idx]
        for policy in collection['policies']:
            policy_txs = requests.get(
                f"https://api.opencnft.io/1/policy/{policy}/transactions",
                {'order': 'price', 'page': 1}
            ).json()
            alltimehigh = policy_txs['items'][0]
            if not policy in TOP_COLLECTIONS_CACHE:
                TOP_COLLECTIONS_CACHE[policy] = {
                    'unit': alltimehigh['unit'],
                    'price': alltimehigh['price']
                }
            elif alltimehigh['price'] > TOP_COLLECTIONS_CACHE[policy]['price']:
                price = alltimehigh['price'] / LOVELACE_TO_ADA
                tweets.append(f"{get_tweet_header('🎉 New Top 25 ATH Sale 🎊')}🎉HUGE CONGRATS TO THE BUYER & SELLER!🎉\n\n{alltimehigh['unit_name']} sold for {price:,.0f} $ADA 🤑\n┗ https://pool.pm/{alltimehigh['fingerprint']}\n\n#Cardano #NFTs\n\n{get_tweet_footer('Source: opencnft.io')}")
                TOP_COLLECTIONS_CACHE[policy]['price'] = alltimehigh['price']
    return tweets

def market_overview():
    MKT_NUM_CLASS = 'FigureMarket__Number'
    ADA_VOL_INDEX = 0
    NFTS_TRADED_INDEX = 2
    market_data = requests.get('https://opencnft.io/market-overview').text
    market_data_dom = BeautifulSoup(market_data)
    market_data_dom.find_all("div", class_=MKT_NUM_CLASS)

    return [f"{get_tweet_header()}1,054,474.33 $ADA traded in the Past 24 Hours\n┗ 3,777 #NFTs traded\n\n#Cardano #CNFTCommunity\n[source: opencnft.io]"]

def top_five_sales():
    # TODO: Implement This
    return []

def current_ada_price():
    coingecko_api = requests.get(
        'https://api.coingecko.com/api/v3/simple/price',
        {'ids': 'cardano', 'vs_currencies': 'usd', 'include_24hr_change': 'true'}
    ).json()
    current_ada_price = coingecko_api['cardano']['usd']
    usd_24h_change = coingecko_api['cardano']['usd_24h_change']
    if usd_24h_change > 0:
        leading_emoji = '📈 +'
        trailing_emoji = '🤩'
    else:
        leading_emoji = '📉 '
        trailing_emoji = '🥴'
    return [f"{get_tweet_header('🚨Daily Price Alert🚨')}📊 Cardano $ADA - ${current_ada_price:0.4f}USD 💵\n{leading_emoji}{usd_24h_change:0.2f}% 24Hr Change {trailing_emoji}\n\n{get_tweet_footer('Data from CoinGecko')}"]

def get_statistics_map():
    return {
        'wallet-wednesday': [
            {
                'name': 'Top 5 Sales',
                'enabled': False,
                'time_of_day': 10800,
                'do_not_repeat': True,
                'function': top_five_sales
            },
            {
                'name': 'Market Overview',
                'enabled': False,
                'time_of_day': 43200,
                'do_not_repeat': True,
                'function': market_overview
            },
            {
                'name': 'Current ADA Price',
                'enabled': True,
                'time_of_day': 55800,
                'do_not_repeat': True,
                'function': current_ada_price
            },
            {
                'name': 'Top 25 All-Time Highs',
                'enabled': True,
                'time_of_day': -1,
                'do_not_repeat': False,
                'function': top_twentyfive_aths
            },
        ]
    }

def iterate_over_statistics(mapping, time_of_day, exclusions):
    executed_statistics = []
    for statistic in mapping:
        if not statistic['enabled']:
            continue
        if statistic['do_not_repeat'] and statistic['name'] in exclusions:
            continue
        if statistic['time_of_day'] < time_of_day:
            try:
                tweets = statistic['function']()
                for tweet in tweets:
                    logging.info(f"Tweeting '{tweet}' for '{statistic['name']}' at {time_of_day}")
                    post_tweet(tweet, key, secrets)
                executed_statistics.append(statistic['name'])
            except:
                logging.exception(f"An error occurred retrieving {statistic['name']} at {time_of_day}... continuing...")
    return executed_statistics

def get_time_of_day():
    now = datetime.utcnow()
    midnight = datetime.combine(now.date(), time())
    return (now - midnight).seconds

def get_parser():
    parser = argparse.ArgumentParser(description='Twitter bot for NFT statistics.')
    subparsers = parser.add_subparsers(dest='command')

    resource_parser = subparsers.add_parser('gen-bot-file', help='Generate resource owner keys and write a bot file for future runs.')
    resource_parser.add_argument('--bot-file', required=True)
    resource_parser.add_argument('--consumer-key', required=True)
    resource_parser.add_argument('--client-secret', required=True)

    stats_parser = subparsers.add_parser('get-stats', help='Run the statistics bot.')
    stats_parser.add_argument('--acct-keys', required=True)
    stats_parser.add_argument('--stats-group', required=True)

    return parser

if __name__ == '__main__':
    configure_request_logging(LOG_LEVEL, DEBUG_REQUESTS)
    args = get_parser().parse_args()
    if args.command == 'gen-bot-file':
        oauth_token = generate_oauth_token(args.consumer_key, args.client_secret)
        logging.info(oauth_token)
        with open(args.bot_file, 'w') as bot_file:
            bot_file.write(json.dumps({
                "key": args.consumer_key,
                "secrets": {
                    "client_secret": args.client_secret,
                    "resource_owner_key": oauth_token['oauth_token'],
                    "resource_owner_secret": oauth_token['oauth_token_secret']
                }
            }))
    elif args.command == 'get-stats':
        with open(args.acct_keys, 'r') as keys_handle:
            keys_json = json.load(keys_handle)
            (key, secrets) = keys_json['key'], keys_json['secrets']
        stats_mapping = get_statistics_map()[args.stats_group]
        old_time_of_day = None
        exclusions = set()
        while True:
            time_of_day = get_time_of_day()
            if old_time_of_day and time_of_day < old_time_of_day:
                logging.info(f"Resetting statistics...")
                exclusions.clear()
            old_time_of_day = time_of_day
            logging.info(f"Beginning new run at {time_of_day}...")
            executed_statistics = iterate_over_statistics(stats_mapping, time_of_day, exclusions)
            exclusions.update(executed_statistics)
            logging.info(f"Have already tweeted out: {exclusions}")
            logging.info('...Completed the most recent statistics run')
            sleep(60)
    else:
        raise ValueError(f"Illegal state occured with '{args.command}' passed")
