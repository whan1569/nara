import requests
from bs4 import BeautifulSoup
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime, timedelta


# SQLAlchemy 엔진 생성
engine = create_engine('mysql+pymysql://root:1234@127.0.0.1:3306/nara')

# 기본 URL 설정
base_url = "https://www.g2b.go.kr:8101/ep/tbid/tbidList.do"

# 시작 날짜와 종료 날짜 설정
year = 2022
start_date = datetime.strptime(f'{year}/01/01', '%Y/%m/%d')
end_date = datetime.strptime(f'{year}/12/31', '%Y/%m/%d')

# 날짜 범위를 저장할 리스트
date_range = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]

# 결과를 저장할 리스트
all_data = []

# 날짜 범위 반복
for current_date in date_range:
    # 날짜를 문자열로 변환
    date_str = current_date.strftime('%Y/%m/%d')

    # 초기 페이지 번호 설정
    page_no = 1

    while True:
        # 현재 페이지 번호와 날짜를 URL에 추가
        url = f"{base_url}?taskClCds=&bidNm=%C0%FC%B1%E2%B0%F8%BB%E7&searchDtType=1&fromBidDt={date_str}&toBidDt={date_str}&fromOpenBidDt=&toOpenBidDt=&radOrgan=1&instNm=&area=&regYn=Y&bidSearchType=1&searchType=1&currentPageNo={page_no}"

        # 웹 페이지 요청
        response = requests.get(url)

        # 응답 HTML 가져오기
        html_content = response.text

        # BeautifulSoup을 사용하여 HTML 파싱
        soup = BeautifulSoup(html_content, 'html.parser')

        # table에서 모든 tr을 찾는다
        rows = soup.find_all('tr', onmouseover=True)

        # 데이터가 없는 경우 반복 종료
        if not rows:
            break

        # 각 행에서 모든 td 데이터를 저장
        for row in rows:
            cols = row.find_all('td')
            row_data = [col.get_text(strip=True) for col in cols]
            all_data.append(row_data)

            # 진행상황 출력
            if len(row_data) > 1:  # "Code" 컬럼이 있는지 확인
                print("Code:", row_data[1])  # "Code"는 두 번째 컬럼이므로 index 1

        # 다음 페이지로 이동
        page_no += 1

# 가장 많은 열 개수 찾기
max_columns = max(len(row) for row in all_data)

# 컬럼 이름 설정
column_names = [
    'Task', 'Code', 'Category', 'BidName', 
    'Institution', 'Institution_1', 'Contract', 
    'Period', 'Joint', 'Status'
]

# 데이터 프레임으로 변환
df = pd.DataFrame(all_data, columns=column_names[:max_columns])

# 데이터 프레임을 MySQL 데이터베이스에 저장
with engine.connect() as connection:
    df.to_sql(f'ticker_{year}', con=connection, if_exists='replace', index=False)
