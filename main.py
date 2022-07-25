import os
import pickle, io
import json
from pydoc import cli
import settings
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.models import ImageMessage
from PIL import Image
import numpy as np
from src.img_similar import calc_cluster, calc_prob, calc_sim
import cv2
import boto3
import urllib.request
import pandas as pd

app = Flask(__name__)

line_bot_api = LineBotApi(settings.YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(settings.YOUR_CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# テキストデータ→オウム返し
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    userid = event.source.user_id
    text = event.message.text
    reply_message(event, TextSendMessage(text=text))


# 画像データ→類似検索
@handler.add(MessageEvent, message=ImageMessage)
def handle_message(event):
    # メッセージID
    message_id = event.message.id
    userid = event.source.user_id
    
    # 画像のバイナリデータの取得
    content = line_bot_api.get_message_content(message_id)
    image_binary = b""
    for data in content.iter_content():
        image_binary += data
    img_binarystream = io.BytesIO(image_binary)
    
    # AWS S3にアクセスするためのキーの指定
    AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY
    BUCKET_NAME = settings.BUCKET_NAME
    
    # 
    client = boto3.client(
        's3', region_name='ap-northeast-1', 
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    url = client.generate_presigned_url(
        ClientMethod='get_object',
        Params={'Bucket':  BUCKET_NAME, 'Key': "men/men.pickle"},
        ExpiresIn=60
    )
    # S3内のpickleを取得
    with urllib.request.urlopen(url) as f:
        obj = pickle.load(f)
        centroids = obj["centroids"]
    
    # 類似画像検索
    prob = calc_prob([img_binarystream], centroids)[0]
    
    url = client.generate_presigned_url(
        ClientMethod='get_object',
        Params={'Bucket':  BUCKET_NAME, 'Key': "men/men.csv"},
        ExpiresIn=60
    )
    
    df = pd.read_csv(url)
    df_image = df["画像URL"].to_list()
    img_bin_list = []
    for image_url in df_image:
        img = Image.open(urllib.request.urlopen(image_url))
        img_bin = img.tobytes()
        img_bin_list.append(io.BytesIO((img_bin)))
    
    # データセットの画像の各クラスタの
    probs = calc_prob(img_bin_list, centroids)
    rank = []
    for f, p in zip(df_image, probs):
        if p is not None:
            sim = calc_sim(prob, p)
            rank.append([f, sim])
    # ランキングを降順に並び替え
    rank = sorted(rank, key=lambda x: -x[1])
    string = ""
    for f, sim in rank:
        string += "%.3f %s \n" % (sim, f)
    #img_pil = Image.open(img_binarystream)
    #img_numpy = np.asarray(img_pil)
    #img_numpy_bgr = cv2.cvtColor(img_numpy, cv2.COLOR_RGBA2BGR)
    
    # FlexMessageのjsonファイルを読み込む
    with open("json/FlexMessage/FlexMessage.json", "r") as f:
        flex_json_data = json.load(f)
    
    reply_message(event, TextSendMessage(text=string))


# メッセージを送信
def reply_message(event, messages):
    line_bot_api.reply_message(
        event.reply_token,
        messages=messages,
    )


if __name__ == "__main__":
    port = os.environ.get('PORT', 3333)
    app.run(
        host='0.0.0.0',
        port=port,
    )
