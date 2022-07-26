import os
import pickle, io
import json
import settings
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.models import ImageMessage, FlexSendMessage
from src.img_similar import calc_prob, calc_sim
import boto3
import urllib.request
import pandas as pd
from boto3.dynamodb.conditions import Key, Attr

app = Flask(__name__)

line_bot_api = LineBotApi(settings.YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(settings.YOUR_CHANNEL_SECRET)

# AWS S3にアクセスするためのキーの指定
AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY
BUCKET_NAME = settings.BUCKET_NAME

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

# テキストデータ
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    userid = event.source.user_id
    text = event.message.text
    client = boto3.client('dynamodb', 
        region_name='ap-northeast-1', 
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    if text == "男":
        text = "男性の洋服を推薦します。"
        client.put_item(
            TableName="line-bot-image",
            Item={
                "gender": "men",
            }
        )
    elif text == "女":
        text = "女性の洋服を推薦します。"
    else:
        return 0
    reply_message(event, message = TextSendMessage(text=text))


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
    
    client = boto3.client(
        's3', region_name='ap-northeast-1', 
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    # S3内のpickleを取得
    url = client.generate_presigned_url(ClientMethod='get_object', Params={'Bucket': BUCKET_NAME, 'Key': "men/men.pickle"}, ExpiresIn=60)
    with urllib.request.urlopen(url) as f:
        obj = pickle.load(f)
        centroids = obj["centroids"]
    
    # 入力画像の各クラスタの所属確率を算出する
    prob = calc_prob([img_binarystream], centroids)[0]
    
    # S3内のcsvファイルを取得
    url = client.generate_presigned_url(ClientMethod='get_object', Params={'Bucket': BUCKET_NAME, 'Key': "men/men_add_probs.csv"}, ExpiresIn=60)
    df = pd.read_csv(url, index_col=0)
    
    # 画像URLのListを取得
    df_image = df["画像URL"].to_list()
    
    # データセットの画像の各クラスタの所属確率
    probs = df["probs"].to_list()
    
    # 入力画像との類似度を計算して、類似度を降順に並び替え
    rank = []
    for img_url, p in zip(df_image, probs):
        # 確率が存在する画像だけランキングリストに追加する
        try:
            rank.append([img_url, calc_sim(eval(prob), eval(p))])
        except:
            continue
    rank = sorted(rank, key=lambda x: -x[1])
    
    # 上位5個の洋服を推薦して、FlexMessageを作成
    d_flex = {
        "type": "carousel",
        "contents": []
    }
    for img_url, _ in rank[:5]:
        # FlexMessageのjsonファイルを読み込む
        with open("json/FlexMessage/FlexMessage.json", "r") as f:
            flex_json_data = json.load(f)
        
        cloth_info = df[df["画像URL"]==img_url]
        flex_json_data["hero"]["url"] = img_url
        flex_json_data["body"]["contents"][0]["text"] = cloth_info["商品名"].values[0]
        flex_json_data["body"]["contents"][1]["contents"][0]["text"] = cloth_info["価格"].values[0]
        flex_json_data["footer"]["contents"][0]["action"]["uri"] = cloth_info["URL"].values[0]
        d_flex["contents"].append(flex_json_data)
    
    reply_message(event, FlexSendMessage(alt_text="Image Similar", contents=d_flex))

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
