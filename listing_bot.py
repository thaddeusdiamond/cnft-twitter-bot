#!/usr/bin/env python3

import argparse
import datetime
import json
import logging
import os
import pytz
import requests
import sys
import time

from http import client as http_client
from requests_oauthlib import OAuth1Session
from selenium import webdriver

# General constants and logging
DEBUG_REQUESTS = False
LOG_LEVEL = logging.INFO

# Selenium/WebDriver Constants
SELENIUM_DELAY = 5

# Cardano constants
LOVELACE_TO_ADA = 1000000.0

# jpg.store API Information
JPGSTORE_ASSET = 'https://www.jpg.store/asset'
JPGSTOREAPI_SEARCH = 'https://server.jpgstoreapis.com/search/tokens'
JPGSTOREAPI_COLLECTION = 'https://server.jpgstoreapis.com/collection'
JPGSTOREAPI_DELAY = 60
JPGSTOREAPI_TIMESTR = '%Y-%m-%dT%H:%M:%S.%f%z'
JPGSTOREAPI_TIMESTR_FALLBACK = '%Y-%m-%dT%H:%M:%S%z'

class Token(object):
    """
    Representation of a Token on the jpg.store
    """
    def __init__(self, policy, traits, key, secrets):
        self.policy = policy
        self.traits = traits
        self.key = key
        self.secrets = secrets

def search_and_buy(policy, last_checked_time, limit_lovelace):
    new_tokens = search_for_new(policy, last_checked_time)
    for token in new_tokens:
        if float(token['listing_lovelace']) <= limit_lovelace:
            driver = webdriver.Firefox()
            driver.get(f"{JPGSTORE_ASSET}{token['asset_id']}")
            time.sleep(SELENIUM_DELAY)
            driver.find_element_by_xpath('//button[normalize-space()="Buy NFT"]').click()
            time.sleep(SELENIUM_DELAY)
            driver.close()

def generate_oauth_token(consumer_key, consumer_secret):
    """
    Note that this function has to be called manually.  Future iterations of this program should provide a CLI to launch.
    """
    request_token_url = "https://api.twitter.com/oauth/request_token?oauth_callback=oob&x_auth_access_type=write"
    oauth = OAuth1Session(consumer_key, client_secret=consumer_secret)
    try:
        fetch_response = oauth.fetch_request_token(request_token_url)
    except ValueError as e:
        logging.error("There may have been an issue with the consumer_key or consumer_secret you entered.")
        raise e
    # Get an OAuth token
    resource_owner_key = fetch_response.get("oauth_token")
    resource_owner_secret = fetch_response.get("oauth_token_secret")
    logging.debug("Got OAuth token: %s" % resource_owner_key)
    # Get authorization
    base_authorization_url = "https://api.twitter.com/oauth/authorize"
    authorization_url = oauth.authorization_url(base_authorization_url)
    print("Please go here and authorize: %s" % authorization_url)
    verifier = input("Paste the PIN here: ")
    # Get the access token
    access_token_url = "https://api.twitter.com/oauth/access_token"
    oauth = OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=resource_owner_key,
        resource_owner_secret=resource_owner_secret,
        verifier=verifier,
    )
    return oauth.fetch_access_token(access_token_url)

def post_tweet(msg, consumer_key, secret_parameters):
    logging.info(f'Posting: {msg}')
    oauth = OAuth1Session(consumer_key, **secret_parameters)
    tweet_response = oauth.post('https://api.twitter.com/2/tweets', json={'text': msg})
    logging.info(tweet_response.text)

def stringify_token(token, price, traits):
    traits_str = ''
    for trait in traits:
        if 'traits' in token and trait in token['traits']:
            if traits_str:
                traits_str += ', '
            traits_str += token['traits'][trait]
    return f"{price:,.2f}₳. {token['display_name']}\n{traits_str}\n{JPGSTORE_ASSET}/{token['asset_id']}"

def get_datetime_for(token_timestr):
    try:
        return datetime.datetime.strptime(token_timestr, JPGSTOREAPI_TIMESTR)
    except ValueError:
        return datetime.datetime.strptime(token_timestr, JPGSTOREAPI_TIMESTR_FALLBACK)

def get_listing_price(token):
    return int(token['listing_lovelace']) / LOVELACE_TO_ADA

def search_for_new_listing(policy, last_timestamp):
    params = {'policyIds': f'["{policy}"]', 'saleType': 'buy-now', 'sortBy': 'recently-listed', 'traits': str({}), 'nameQuery': '', 'verified': 'default', 'pagination': str({}), 'size': 20}
    jpgstore_search = requests.get(JPGSTOREAPI_SEARCH, params=params).json()
    logging.debug(jpgstore_search)
    if not 'tokens' in jpgstore_search:
        return []
    new_tokens = []
    for token in jpgstore_search['tokens']:
        token_timestamp = get_datetime_for(token['listed_at'])
        if token_timestamp > last_timestamp:
            token['token_timestamp'] = token_timestamp
            new_tokens.append(token)
    return new_tokens

def get_sale_price(token):
    return int(token['amount_lovelace']) / LOVELACE_TO_ADA

def search_for_new_sale(policy, last_timestamp):
    recent_txs = f"{JPGSTOREAPI_COLLECTION}/{policy}/transactions?page=1&count=20"
    jpgstore_search = requests.get(recent_txs)
    logging.debug(jpgstore_search.text)
    new_tokens = []
    for token in jpgstore_search.json()['transactions']:
        token_timestamp = get_datetime_for(token['confirmed_at'])
        if token_timestamp > last_timestamp:
            token['token_timestamp'] = token_timestamp
            new_tokens.append(token)
    return new_tokens

def search_and_post(policy, traits, key, secrets, timekeeper, type, search_func, price_func):
    logging.info(f'{policy}: Last {type} timestamp of {timekeeper[policy]}')
    new_tokens = search_func(policy, timekeeper[policy])
    for token in reversed(new_tokens):
        logging.debug(token)
        post_tweet(stringify_token(token, price_func(token), traits), key, secrets)
        timekeeper[policy] = datetime.datetime.fromtimestamp(time.time(), tz=pytz.utc)

def gen_token(filename):
    with open(filename, 'r') as filehandle:
        token_json = json.load(filehandle)
        return Token(token_json['policy'], token_json['traits'], token_json['key'], token_json['secrets'])

def get_parser():
    parser = argparse.ArgumentParser(description='Twitter bot for NFT listings.')
    subparsers = parser.add_subparsers(dest='command')

    resource_parser = subparsers.add_parser('gen-bot-file', help='Generate resource owner keys and write a bot file for future runs.')
    resource_parser.add_argument('--policy', required=True)
    resource_parser.add_argument('--bot-file', required=True)
    resource_parser.add_argument('--consumer-key', required=True)
    resource_parser.add_argument('--client-secret', required=True)

    listing_parser = subparsers.add_parser('listing-sales-bot', help='Fire up the listing and sales bots for the service.')
    listing_parser.add_argument('--listing-tokens-dir', required=False)
    listing_parser.add_argument('--sales-tokens-dir', required=False)

    sniper_parser = subparsers.add_parser('purchase-bot', help='Fire up the listing bots for the service.')
    sniper_parser.add_argument('--policies_prices', required=True, nargs='+')

    return parser

def configure_request_logging(log_level, debug_requests):
    # These two lines enable debugging at httplib level (requests->urllib3->http.client)
    # You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
    # The only thing missing will be the response.body which is not logged.
    if debug_requests:
        http_client.HTTPConnection.debuglevel = 1

    # You must initialize logging, otherwise you'll not see debug output.
    logging.basicConfig(level=log_level)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(log_level)
    requests_log.propagate = True

if __name__ == '__main__':
    configure_request_logging(LOG_LEVEL, DEBUG_REQUESTS)
    args = get_parser().parse_args()
    if args.command == 'gen-bot-file':
        oauth_token = generate_oauth_token(args.consumer_key, args.client_secret)
        logging.info(oauth_token)
        with open(args.bot_file, 'w') as bot_file:
            bot_file.write(json.dumps({
                "policy": args.policy,
                "traits": [],
                "key": args.consumer_key,
                "secrets": {
                    "client_secret": args.client_secret,
                    "resource_owner_key": oauth_token['oauth_token'],
                    "resource_owner_secret": oauth_token['oauth_token_secret']
                }
            }))
    elif args.command == 'listing-sales-bot':
        listing_tokens = []
        if args.listing_tokens_dir:
            listing_tokens = [gen_token(os.path.join(args.listing_tokens_dir, filename)) for filename in os.listdir(args.listing_tokens_dir)]
            listing_timekeeper = { token.policy:datetime.datetime.fromtimestamp(time.time(), tz=pytz.utc) for token in listing_tokens }
        sales_tokens = []
        if args.sales_tokens_dir:
            sales_tokens = [gen_token(os.path.join(args.sales_tokens_dir, filename)) for filename in os.listdir(args.sales_tokens_dir)]
            sales_timekeeper = { token.policy:datetime.datetime.fromtimestamp(time.time(), tz=pytz.utc) for token in sales_tokens }
        if not listing_tokens and not sales_tokens:
            logging.info('Please specify at least one of "--listing-tokens-dir" or "--sales-tokens-dir"')
        else:
            while True:
                for token in listing_tokens:
                    search_and_post(token.policy, token.traits, token.key, token.secrets, listing_timekeeper, 'listing', search_for_new_listing, get_listing_price)
                for token in sales_tokens:
                    search_and_post(token.policy, token.traits, token.key, token.secrets, sales_timekeeper, 'sales', search_for_new_sale, get_sale_price)
                time.sleep(JPGSTOREAPI_DELAY)
    elif args.command == 'purchase-bot':
        policies_prices = [arg.split('=') for arg in args.policies_prices]
        timekeeper = { policy_price[0]:datetime.datetime.fromtimestamp(time.time() - 1000000, tz=pytz.utc) for policy_price in policies_prices }
        while True:
            for (policy, price) in policies_prices:
                search_and_buy(policy, timekeeper[policy], int(price) * LOVELACE_TO_ADA)
            time.sleep(JPGSTOREAPI_DELAY)
    else:
        raise ValueError(f"Illegal state occured with '{args.command}' passed")
