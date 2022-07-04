<p align="center">
  <h1 align="center">cnft-twitter-bot</h1>
  <p align="center">A simple Python script to run long-lived Twitter bots for CNFT listings and sales.</p>
  <p align="center">
    <img src="https://img.shields.io/github/commit-activity/m/thaddeusdiamond/cnft-twitter-bot?style=for-the-badge" />
    <img src="https://img.shields.io/github/license/thaddeusdiamond/cnft-twitter-bot?style=for-the-badge" />
    <a href="https://twitter.com/wildtangz">
      <img src="https://img.shields.io/twitter/follow/wildtangz?style=for-the-badge&logo=twitter" />
    </a>
  </p>
</p>

## Quickstart

This script is meant to be used in a server environment to scrape listings and sales and produce output via automated Twitter accounts.  To get started, log in to the [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard) for the account you have created to publish under.  You will be presented with several mechanisms for verification and, ultimately, a bearer token, a consumer key, and a client secret.

:warning: YOU MUST WRITE THESE DOWN IN A PRIVATE LOCATION!

### Generating the Bot Credentials File

To generate the bot file to a local directory that you will be using, run:
```bash
mkdir /path/to/listing/directory/desired/
python3 listing_bot.py gen-bot-file \
          --policy <POLICY> \
          --bot-file <BOT_FILE> \
          --consumer-key <CONSUMER_KEY> \
          --client-secret <CLIENT_SECRET>
```

Follow the prompts to the specified Twitter.com web URL and enter the one-time validation token.  If you want to run a sales bot as well, you have to repeat that process for a separate sales account.

### Basic Twitter Bot Usage

To run the Twitter bot:
```bash
python3 listing_bot.py listing-bot \
          --listing-tokens-dir /path/to/listing/directory/desired/ \
          --sales-tokens-dir /other/path/to/sales/directory/
```

This program is meant to run endlessly in a command line prompt.  Restarts may be required due to network connectivity issues.


## Installation

This is a single script with no build process to keep things simple.  Download from Github and have at it!

You may want to consider using a virtual environment to separate any dependencies this script requires.  For this, use:
```bash
python3 -m venv /path/to/virtual/environment
```

## Twitter Compatibility

Please note that this is built to be used according to the [Twitter Developer Agreement and Policy](https://developer.twitter.com/en/developer-terms/agreement-and-policy).  You are responsibility for validating that all usage of this script complies with those terms and the repository authors disclaim any liability for usage of this free and open source software.
