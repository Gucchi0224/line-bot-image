"""
scraping.py: GUの服データをスクレイピングで収集
今回GUの服（トップス）のデータを収集したが、CSSのクラスが獲得できないものがある（原因不明）ため
tryとexceptを頻繁に使用している。（利用規約・robots.txtは確認済み）
"""

import os, sys
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from time import sleep

def main():
    args = sys.argv
    if not os.path.exists("../data/"):
        os.mkdir("../data/")
    try:
        file_name = args[1]
        file_path = f"../data/{file_name}"
        if not os.path.exists(file_path):
            os.mkdir(file_path)
    except:
        print("Not select the file name.")
        return 0
    # chromedriverのPath
    chrome_path = '../chromedriver_win32/chromedriver'
    options = Options()
    options.add_argument('--incognito')
    driver = webdriver.Chrome(executable_path=chrome_path, options=options)
    
    # 服情報の取得
    d_list = []
    
    for i in range(1,100):
        url = f'https://www.gu-global.com/jp/ja/category/{file_name}/tops?page={i}'
        driver.get(url)
        sleep(1)
        elements = driver.find_element(By.CLASS_NAME, 'sc-2695pe-0.fJifex').find_elements(By.CLASS_NAME, "sc-1kpyy02-0.ksxvFG")
        sleep(2)
        for j, elem in enumerate(elements):
            try:
                image_url = elem.find_element(By.CLASS_NAME, "sc-1dphr7g-4.jQfulw").get_attribute("src")
                url = elem.find_element(By.CLASS_NAME, "sc-1krsg8w-0.jQZwvY").get_attribute("href")
                name = elem.find_element(By.CLASS_NAME, "sc-150v5lj-0.bhnlib").text
                try:
                    price = elem.find_element(By.CLASS_NAME, "sc-150v5lj-0.yfgtrh-0.jhFnrv").text
                except:
                    price = elem.find_element(By.CLASS_NAME, "sc-150v5lj-0.yfgtrh-0.bNsGlD").text
                d = {
                    '画像URL': image_url, 
                    "URL": url,
                    '商品名': name, 
                    '価格': price, 
                }
                print(d)
                d_list.append(d)
            except:
                print(j+1)
                continue
            sleep(3)
            try:
                # 次のページに移動
                next_btn = driver.find_element(By.CLASS_NAME, 'pagination-next-link')
            except:
                break
    
    df = pd.DataFrame(d_list)
    df.to_csv("{}/{}.csv".format(file_path, file_name))
    
    # ブラウザを終了
    driver.quit()

if __name__ == '__main__':
    main()