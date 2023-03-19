import telegram
import schedule
import time
import sys
import io
from bs4 import BeautifulSoup
import requests

import pytz
import datetime

import pandas as pd

from dotenv import dotenv_values
from notion_client import Client
from pprint import pprint



def kwd_load():

    config = dotenv_values(".env")
    notion_secret = config.get('NOTION_TOKEN')
    keyword_list = []
    stock_list = []
    emer_keyword_list = []


    notion = Client(auth=notion_secret)
    database_id = 'b65f2ab6-54de-475f-9932-0f1a3f867484'
    
    #1차로 읽어오기
    db_pages = notion.databases.query(database_id=database_id)
    
    for page in db_pages['results']:
        if page['properties']['표시여부']['checkbox'] == True:
            try:    
                keyword_list.append(page['properties']['키워드']['title'][0]['plain_text'])
            except:
                continue
            
            try:
                stock_list.append(page['properties']['관련주']['rich_text'][0]['plain_text'])
            except:
                stock_list.append('없음')   

        if page['properties']['긴급방']['checkbox'] == True:
            try:    
                emer_keyword_list.append(page['properties']['키워드']['title'][0]['plain_text'])
            except:
                continue
            
    
    has_more = db_pages['has_more']
    
    if has_more:
        next_cursor = db_pages['next_cursor']

    while db_pages['has_more']:
        db_pages = notion.databases.query(database_id=database_id,start_cursor=next_cursor)
        
        for page in db_pages['results']:
            if page['properties']['표시여부']['checkbox'] == True:
                try:    
                    keyword_list.append(page['properties']['키워드']['title'][0]['plain_text'])
                except:
                    continue
                try:
                    stock_list.append(page['properties']['관련주']['rich_text'][0]['plain_text'])
                except:
                    stock_list.append('없음')
            if page['properties']['긴급방']['checkbox'] == True:
                try:    
                    emer_keyword_list.append(page['properties']['키워드']['title'][0]['plain_text'])
                except:
                    continue   

        has_more = db_pages['has_more']
        if has_more:
            next_cursor = db_pages['next_cursor']
    
    return (keyword_list,stock_list,emer_keyword_list)

recentSubject = []
emer_recentSubject = []
token = "5876483553:AAF77ZUF-F72eEWy8NaUx8ax6VBP5fTDIYU"
bot = telegram.Bot(token=token)
chat_id = "-1001557650956"
chat_id_emer = "-625367041"
tmp_msg = "실시간 뉴스 감지를 시작합니다."
bot.sendMessage(chat_id=chat_id,text=tmp_msg)
bot.sendMessage(chat_id=chat_id_emer,text=tmp_msg)


code_df = pd.read_html('http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13', header=0)[0]
code_df.종목코드 = code_df.종목코드.map('{:06d}'.format)
code_df = code_df[['회사명', '종목코드']]
code_df = code_df.rename(columns={'회사명': 'name', '종목코드': 'code'})
#print(code_df)

news_df = pd.DataFrame(columns=['기사','링크','언론사'])

def job():
    global recentSubject
    global emer_recentSubject
    global news_df

    (newsFilter,stockFilter,emer_newsFilter) = kwd_load()
    
    now = datetime.datetime.now(pytz.timezone('Asia/Seoul'))
    if now.hour >= 22 or now.hour <= 7:
        return

    sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')

    BASE_URL = "https://news.naver.com/main/list.naver?mode=LSD&mid=sec&listType=title&sid1=001"

    with requests.Session() as s:
        res = s.get(BASE_URL, headers={'User-Agent': 'Mozilla/5.0'})
        if res.status_code == requests.codes.ok:
            soup = BeautifulSoup(res.text, 'html.parser')
            for cnt in range(5):
                tmp_loc = f"#main_content > div.list_body.newsflash_body > ul:nth-child(1) > li:nth-child({cnt+1}) > a"
                tmp_loc2 = f"#main_content > div.list_body.newsflash_body > ul:nth-child(1) > li:nth-child({cnt+1}) > span.writing"
                article = soup.select_one(tmp_loc)
                media = soup.select_one(tmp_loc2)
                articleText = article.text
                articleHref = article.attrs['href']
                mediaName = media.text
                for i in range(0, len(newsFilter)):
                    if (newsFilter[i] in articleText) and (articleText not in recentSubject):
                        bot.sendMessage(chat_id=chat_id,text=articleText + articleHref)
                        if stockFilter[i] != "없음":
                            instance_msg = "*관련주 : "+stockFilter[i]
                            bot.sendMessage(chat_id=chat_id,text=instance_msg)
                        recentSubject.append(articleText)
                        tmp_news = {'기사': articleText,'링크':articleHref,'언론사':mediaName}
                        news_df.append(tmp_news, ignore_index=True)
                        print(articleText)
                        print(news_df)
                for i in range(0, len(emer_newsFilter)):
                        if (emer_newsFilter[i] in articleText) and (articleText not in emer_recentSubject):
                            bot.sendMessage(chat_id=chat_id_emer,text=articleText + articleHref)
                            emer_recentSubject.append(articleText)
                        
#main_content > div.list_body.newsflash_body > ul:nth-child(1) > li:nth-child(1) > span.writing    

def save():
    now = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M")
    news_df.to_excel('기사모음'+now+'.xlsx')

# 0.5초 마다 실행
schedule.every(1).seconds.do(job)
try:
    schedule.every(3600).seconds.do(save)
except:
    print('파일저장이 되지 않았습니다.')
#newsin = '키워드 목록 : '

#for i in newsFilter:
#    newsin = newsin + i + ','
        
#bot.sendMessage(chat_id=chat_id, text=newsin)

# 파이썬 스케줄러
while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except:
        continue

