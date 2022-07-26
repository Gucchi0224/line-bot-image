"""
img_similar.py: 画像の類似度をBag of Visual Wordsを用いて計算
このコードに関しては以下のURLに記載されているコードを用いている。
https://hazm.at/mox/machine-learning/computer-vision/recipes/similar-image-retrieval.html
"""

import pickle
from natsort import natsorted
import glob
import numpy as np
import cv2
from PIL import Image
import pandas as pd

################################################################################################
detector = cv2.KAZE_create()

################################################################################################
# 特徴量空間をクラスタに分け重心を求める（予め用意しておく）
def calc_cluster(files, cluster_num=5):    
    bowTrainer = cv2.BOWKMeansTrainer(cluster_num)
    for file in files:
        image = cv2.imread(file)
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if gray_image is not None:
            _, descriptors = detector.detectAndCompute(gray_image, None)
            if descriptors is not None:
                bowTrainer.add(descriptors.astype(np.float32))
    centroids = bowTrainer.cluster()
    return centroids

################################################################################################
# 画像がどのクラスタに属するかの確率を計算
def calc_prob(files, centroids):
    matcher = cv2.BFMatcher()
    extractor = cv2.BOWImgDescriptorExtractor(detector, matcher)
    extractor.setVocabulary(centroids)
    probs = []
    for file in files:
        descriptor = None
        img_pil = Image.open(file)
        img_numpy = np.asarray(img_pil)
        image = cv2.cvtColor(img_numpy, cv2.COLOR_RGB2GRAY)
        if image is not None:
            keypoints = detector.detect(image, None)
            if keypoints is not None:
                descriptor = extractor.compute(image, keypoints)[0]
        probs.append(str(descriptor.tolist()))
    return probs

################################################################################################
# 指定されたクラスタ所属確率の類似度を算出する
def calc_sim(prob1, prob2):
    return sum(map(lambda x: min(x[0], x[1]), zip(prob1, prob2)))

################################################################################################
def main():
    # index生成
    lists = ["men", "women"]
    for gender in lists:
        # csvファイルとマスクされた画像ファイルの取得
        df = pd.read_csv(f"../data/{gender}/{gender}_cut_face.csv", index_col=0)
        files = natsorted(glob.glob(f"../data/{gender}/image/mask/*.jpg"))
        # 画像の特徴ベクトルをクラスタリングして、各クラスタの重心を算出する
        centroids = calc_cluster(files)
        # どのクラスタに属するかの確率を計算して、DataFrameを作成
        probs = calc_prob(files, centroids)
        df_probs = pd.DataFrame(probs, columns=["probs"])
        # 元のDataframeとクラスタの所属確率が含まれるDataframeを結合して、CSVファイルを作成
        new_df = pd.concat([df, df_probs], axis=1)
        new_df.to_csv(f"../data/{gender}/{gender}_add_probs.csv")
        # LINE Botで使用するために各クラスタの重心を保存
        with open(f"../data/{gender}/{gender}.pickle", "wb") as f:
            pickle.dump({"centroids": centroids}, f)

#############################################################################
if __name__ == "__main__":
    main()