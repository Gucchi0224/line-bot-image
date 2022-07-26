"""
settings.py: 環境変数の呼び出し
"""

import os
from os.path import dirname, join
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

YOUR_CHANNEL_SECRET = os.environ.get("YOUR_CHANNEL_SECRET")
YOUR_CHANNEL_ACCESS_TOKEN = os.environ.get("YOUR_CHANNEL_ACCESS_TOKEN")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
BUCKET_NAME = os.environ.get("BUCKET_NAME")
TABLE_NAME = os.environ.get("TABLE_NAME")