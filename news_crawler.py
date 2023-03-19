# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
import requests
import pandas as pd
import re
import openpyxl
from openpyxl.styles import Alignment, PatternFill, Font, Border, Side
import shutil
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''
< naver 뉴스 검색시 리스트 크롤링하는 프로그램 > _select사용
- 크롤링 해오는 것 : 링크,제목,신문사,날짜,내용요약본
- 날짜,내용요약본  -> 정제 작업 필요
- 리스트 -> 딕셔너리 -> df -> 엑셀로 저장 
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''

#각 크롤링 결과 저장하기 위한 리스트 선언 
title_text=[]
link_text=[]
source_text=[]
date_text=[]
contents_text=[]
contents_full=[]
result={}
queries=[]

#엑셀로 저장하기 위한 변수
RESULT_PATH ='C:/Temp/'  #결과 저장할 경로
now = datetime.now() #파일이름 현 시간으로 저장하기

code_df = pd.read_html('http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13', header=0)[0]
code_df.종목코드 = code_df.종목코드.map('{:06d}'.format)
code_df = code_df[['회사명', '종목코드']]
code_df = code_df.rename(columns={'회사명': 'name', '종목코드': 'code'})
code_df.to_excel(RESULT_PATH+'최신종목코드.xlsx')

df_list = pd.read_csv(RESULT_PATH+'list.csv',encoding='cp949')

df_list = df_list[df_list['종목명'].isna()==False]
df_list = df_list[df_list['종목명']!='삼성전자']
df_list = df_list.fillna('-')

df_list['거래량'] =(df_list['거래량'].str.replace(pat=r'[^A-Za-z0-9]', repl= r'', regex=True)).astype(int)
df_list['거래량'] = (df_list['거래량']/1000).round(0).astype(int)
df_list['header'] = df_list['대비'] + ' ' +df_list['종목명'] + ' (' +df_list['등락률'].astype(str) + '% '+ '고가 :' +df_list['고가 %'].astype(str) + '%) (' +df_list['거래량'].astype(str) + 'K' + ') ('\
    + df_list['시가총액'].astype(str)+'억/' +df_list['부채비율(Y)'].astype(str)+'%/' +df_list['유보율(Y)'].astype(str) + '%)'
items = df_list['종목명'].values.tolist()
outputFileName1 = '_%s-%s-%s %s시%s분%s초.xlsx' % (now.year, now.month, now.day,now.hour,now.minute,now.second)
df_list.to_excel(RESULT_PATH+'list_modified'+outputFileName1,encoding='utf-8')


#날짜 정제화 함수
def date_cleansing(test):
    try:
        #지난 뉴스
        #머니투데이  10면1단  2018.11.05.  네이버뉴스   보내기  
        pattern = '\d+.(\d+).(\d+).'  #정규표현식 
    
        r = re.compile(pattern)
        match = r.search(test).group(0)  # 2018.11.05.
        date_text.append(match)
        
    except AttributeError:
        #최근 뉴스
        #이데일리  1시간 전  네이버뉴스   보내기  
        pattern = '\w* (\d\w*)'     #정규표현식 
        
        r = re.compile(pattern)
        match = r.search(test).group(1)
        #print(match)
        date_text.append(match)


#내용 정제화 함수 
def contents_cleansing(contents):
    first_cleansing_contents = re.sub('<dl>.*?</a> </div> </dd> <dd>', '', 
                                      str(contents)).strip()  #앞에 필요없는 부분 제거
    second_cleansing_contents = re.sub('<ul class="relation_lst">.*?</dd>', '', 
                                       first_cleansing_contents).strip()#뒤에 필요없는 부분 제거 (새끼 기사)
    third_cleansing_contents = re.sub('<.+?>', '', second_cleansing_contents).strip()
    contents_text.append(third_cleansing_contents)
    contents_full.append(contents)
    #print(contents_text)
    

def crawler(maxpage,query,sort,s_date,e_date):

    s_from = s_date.replace(".","")
    e_to = e_date.replace(".","")
    page = 1  
    maxpage_t =(int(maxpage)-1)*10+1   # 11= 2페이지 21=3페이지 31=4페이지  ...81=9페이지 , 91=10페이지, 101=11페이지
    
    while page <= maxpage_t:
        url = "https://search.naver.com/search.naver?where=news&query=" + query + "&sort="+sort+"&ds=" + s_date + "&de=" + e_date + "&nso=so%3Ar%2Cp%3Afrom" + s_from + "to" + e_to + "%2Ca%3A&start=" + str(page)
        
        response = requests.get(url)
        html = response.text
 
        #뷰티풀소프의 인자값 지정
        soup = BeautifulSoup(html, 'html.parser')
 
        #<a>태그에서 제목과 링크주소 추출
        atags = soup.select('.news_tit')
        for atag in atags:
            title_text.append(atag.text)     #제목
            link_text.append(atag['href'])   #링크주소
            queries.append(query)
            
        #신문사 추출
        source_lists = soup.select('.info_group > .press')
        for source_list in source_lists:
            source_text.append(source_list.text)    #신문사
        
        #날짜 추출 
        date_lists = soup.select('.info_group > span.info')
        for date_list in date_lists:
            # 1면 3단 같은 위치 제거
            if date_list.text.find("면") == -1:
                if '일 전' in date_list.text:
                    #print(date_list.text,type(date_list.text))
                    temp_date = str(date.today()-timedelta(int(date_list.text[0])))
                    date_text.append(temp_date)
                elif '시간 전' in date_list.text:
                    #print(date_list.text,type(date_list.text))
                    temp_date = str(date.today())
                    date_text.append(temp_date)
                elif '분 전' in date_list.text:
                    #print(date_list.text,type(date_list.text))
                    temp_date = str(date.today())
                    date_text.append(temp_date)
                elif '.' not in date_list.text:
                    continue
                elif '공정거래위원회' in date_list.text:
                    continue
                else:
                    date_text.append(date_list.text[:10].replace('.','-'))
        
        #본문요약본
        contents_lists = soup.select('.news_dsc')
        for contents_list in contents_lists:
            contents_cleansing(contents_list) #본문요약 정제화
        

        #모든 리스트 딕셔너리형태로 저장
        result= {"date" : date_text , "title":title_text ,"link":link_text,  "source" : source_text ,"contents": contents_text ,'keyword': queries,"contents(full)":contents_full}  
        #print(page)
        
        df = pd.DataFrame(result) #df로 변환

        page += 10
    ban_press = ['이코노뉴스','공감신문','국제뉴스','제주교통복지신문','매일안전신문','더드라이브']
    
    for i in ban_press:
        df = df[df['source']!=i]

    #라씨로 = df[df['title'].str.contains('라씨로')].index
    #df.drop(라씨로,inplace=True)
    df['date'] = "("+df['date']+") "

    df.sort_values('date',ascending=False)
    df.reset_index()
    
    

    #print(df)
        
    return(df)
    # 새로 만들 파일이름 지정
    #outputFileName1 = '%s-%s-%s.csv' % (now.year, now.month, now.day)
    #outputFileName2 = '%s-%s-%s.xlsx' % (now.year, now.month, now.day)
    #df.to_csv(RESULT_PATH+query+'_'+outputFileName1,encoding='utf-8-sig')
    #df.to_excel(RESULT_PATH+query+'_'+outputFileName2)

def main(query):    
    print(query)
    maxpage = 10
    #query = input("검색어 입력: ")  
    sort = '1' #input("뉴스 검색 방식 입력(관련도순=0  최신순=1  오래된순=2): ")    #관련도순=0  최신순=1  오래된순=2
    s_date = '2017.01.01'
    e_date = str(date.today())   

    df_final = pd.DataFrame(columns=['date','title','link','source','contents','keyword'])
    

    keyword_list = ['핵심','유일','최초','특징주','납품','공시','공급','','국내 유일']
    for keyw in keyword_list:
        query2 =  keyw + '|"' + query + '"'
        df = crawler(maxpage,query2,sort,s_date,e_date)
        df_final = pd.concat([df_final,df])
        #print(df)
        del df

    df_final.drop_duplicates(inplace=True)
    df_final.sort_values('date',ascending=False,inplace=True)
    df_final.reset_index()
    
    outputFileName1 = '%s-%s-%s %s시%s분%s초.xlsx' % (now.year, now.month, now.day,now.hour,now.minute,now.second)
    #outputFileName2 = '%s-%s-%s %s시%s분%s초1.xlsx' % (now.year, now.month, now.day,now.hour,now.minute,now.second)
    df_final = df_final.drop_duplicates(['title'], ignore_index = True)
    df_final.to_excel(RESULT_PATH+query+'_'+outputFileName1)
    #print(df_final)

    del df_final

    #엑셀 파일 서식 지정
    wb = openpyxl.load_workbook(RESULT_PATH+query+'_'+outputFileName1)
    sh = wb.active

    #1행, 1열 고정
    sh.freeze_panes = "B2"
    #열 크기 지정
    col_widths = {"A":4, "B":8, "C":40, "D":8, "E":8, \
        "F":90, "G":10, "H":70}
    for col_name in col_widths:
        sh.column_dimensions[col_name].width = col_widths[col_name]

    #폰트 지정
    font_header = Font(name="맑은 고딕",size=8)

    side = Side(style="thin", color="000000")
    border = Border(left=side, right=side, top=side, bottom=side)
    for row in sh:
        for cell in row:
            cell.border = border
            cell.font = font_header
            #sh[cell.coordinate].border = border

    wb.save(RESULT_PATH+query+'_'+outputFileName1)
    wb.close()

#items = ['라온시큐어']


for i in items:
    main(i)
    title_text=[]
    link_text=[]
    source_text=[]
    date_text=[]
    contents_text=[]
    contents_full = []
    result={}
    queries=[]



#추가 예정 기능
#키워드 제외 기능 (예:박정희 from 유신 등), 추가 키워드 편집 기능, 검색 본문 제외 기능