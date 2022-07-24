"""
cut_face.py: 元々の画像にグレー画像でマスクをする。
関数「imread_web」に関しては以下のURLに記載されているコードを用いている。
https://qiita.com/lt900ed/items/891e162a5a1091bae912
"""

import os
import requests
import tempfile
import pandas as pd
import cv2
from tqdm import tqdm

def imread_web(url):
    # 画像をリクエストする
    res = requests.get(url)
    img = None
    # Tempfileを作成して即読み込む
    fp = tempfile.NamedTemporaryFile(dir='./', delete=False)
    fp.write(res.content)
    fp.close()
    img = cv2.imread(fp.name)
    os.remove(fp.name)
    return img

def main():
    # カスケードファイルを用いて顔画像の切り抜きを行う
    cascade_path = "../haarcascade_frontalface_alt.xml"
    lists = ["men", "women"]
    
    # 各性別ごとに実行
    for gender in tqdm(lists):
        # 画像Pathの設定
        img_save_path = f"../data/{gender}/image/"
        if not os.path.exists(img_save_path):
            os.mkdir(img_save_path)
        origin_path = img_save_path + "origin"
        if not os.path.exists(origin_path):
            os.mkdir(origin_path)
        mask_path = img_save_path + "mask"
        if not os.path.exists(mask_path):
            os.mkdir(mask_path)
        
        # csvファイルの読み込み
        file_path = f"../data/{gender}/{gender}.csv"
        df = pd.read_csv(file_path, index_col=0)
        
        # 画像URL -> 画像 -> 顔部分をグレー画像でマスク
        for i, img_url in enumerate(df["画像URL"]):
            # 画像URLから画像を読み込む
            img = imread_web(img_url)
            # 元画像を保存
            cv2.imwrite("{}/{}.jpg".format(origin_path, i), img)
            
            # グレースケールに変換
            gray_img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            
            # 最小で(16,16)のサイズの顔画像を検出
            cascade = cv2.CascadeClassifier(cascade_path) 
            facerect = cascade.detectMultiScale(gray_img, scaleFactor=1.1, minNeighbors=1, minSize=(16,16))
            if len(facerect) > 0:
                for rect in facerect:
                    # 顔部分をマスク
                    x = rect[0]
                    y = rect[1]
                    w = rect[2]
                    h = rect[3]
                    add_gray_rect = cv2.rectangle(img, (x,y), (x+w,y+h), color=(121,121,121), thickness=-1)
                    cv2.imwrite("{}/{}.jpg".format(mask_path, i), add_gray_rect)
                    break # 1つのファイルにつき1つだけマスクをかける

if __name__ == "__main__":
    main()