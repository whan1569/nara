import os
import pyautogui
import time
import re
import keyboard
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from google.cloud import vision
from sqlalchemy import create_engine, Table, MetaData, select, func
from sqlalchemy.orm import sessionmaker

# Google Cloud Vision API 환경 변수 설정 (실제 경로로 수정)
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'C:\Users\USER\Desktop\nara\my-key.json'

year = 2012
# 데이터베이스 연결 설정
DATABASE_URL = 'mysql+mysqlconnector://root:1234@127.0.0.1:3306/nara'
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def capture_screen(region):
    """특정 영역의 화면을 캡처합니다."""
    screenshot = pyautogui.screenshot(region=region)
    screenshot.save('captured_image.png')
    return 'captured_image.png'

def extract_prices(text):
    """추출한 텍스트에서 가격 정보를 정리합니다."""
    try:
        # 정규 표현식을 사용해 필요한 부분만 추출
        draw_prices_pattern = r"추첨가격 (\d+)\n([\d,]+)\n(\d+)"
        draw_prices_matches = re.findall(draw_prices_pattern, text)
        
        # draw_prices 리스트 구성
        draw_prices = [
            (int(match[0]), int(match[1].replace(',', '')), int(match[2]))
            for match in draw_prices_matches
        ]

        # 예상 가격 및 기초 금액 추출
        expected_price_pattern = r"예정가격\n([\d,]+)"
        base_price_pattern = r"기초금액\n([\d,]+)"
        
        expected_price = int(re.search(expected_price_pattern, text).group(1).replace(',', ''))
        base_price = int(re.search(base_price_pattern, text).group(1).replace(',', ''))

        return draw_prices, expected_price, base_price
    except Exception as e:
        print(f"가격 정보 추출 중 오류 발생: {e}")
        return [], 0, 0

def detect_text(image_path, bidno):
    """Google Cloud Vision API를 사용하여 이미지에서 텍스트를 감지합니다."""
    client = vision.ImageAnnotatorClient()

    try:
        with open(image_path, 'rb') as image_file:
            content = image_file.read()

        image = vision.Image(content=content)
        response = client.text_detection(image=image)
        texts = response.text_annotations

        if texts:
            print("감지된 텍스트 (정제 후):")
            full_text = texts[0].description  # 전체 텍스트

            # 추출한 텍스트 정제
            draw_prices, expected_price, base_price = extract_prices(full_text)

            # 첫 번째 DataFrame: draw_prices 정보
            df_draw_prices = pd.DataFrame(draw_prices, columns=['Number', 'Price', 'Choose'])
            df_draw_prices['Code'] = bidno  # bidno를 Code 열에 추가
            df_draw_prices = df_draw_prices[['Code', 'Number', 'Price', 'Choose']]  # 열 순서 변경

            # 두 번째 DataFrame: Summary 정보
            summary_data = {'Code': [bidno], 'Expected_price': [expected_price], 'Base_price': [base_price]}
            df_summary = pd.DataFrame(summary_data)

            # DataFrame을 MySQL 테이블에 삽입
            df_draw_prices.to_sql(f'draw_{year}', con=engine, if_exists='append', index=False)
            df_summary.to_sql(f'summary_{year}', con=engine, if_exists='append', index=False)

            print(f"Data for {bidno} inserted successfully!")

        else:
            print("텍스트를 감지하지 못했습니다.")
    except Exception as e:
        print(f"텍스트 감지 중 오류 발생: {e}")

def fetch_codes_from_database():
    """MySQL 데이터베이스에서 코드를 조회하고 마지막 3자를 제거하여 반환합니다."""
    metadata = MetaData()
    ticker_table = Table(f'ticker_{year}', metadata, autoload_with=engine)

    query = select(ticker_table.c.Code).where(
        (func.length(ticker_table.c.Code) == 14) &
        (func.right(ticker_table.c.Code, 2) == '00')
    )

    with engine.connect() as connection:
        result = connection.execute(query).fetchall()

    modified_codes = [row[0][:-3] for row in result]
    return modified_codes

def fetch_processed_codes():
    """이미 처리된 코드들을 summary_table에서 조회하고 반환합니다."""
    metadata = MetaData()
    summary_table = Table(f'summary_{year}', metadata, autoload_with=engine)

    query = select(summary_table.c.Code)

    with engine.connect() as connection:
        result = connection.execute(query).fetchall()

    processed_codes = [row[0] for row in result]
    return processed_codes

def process_bid(bidno):
    """주어진 bidno 값을 사용하여 웹 페이지를 열고 작업을 수행합니다."""
    url = f"https://www.g2b.go.kr:8081/ep/invitation/publish/bidInfoDtl.do?bidno={bidno}&bidseq=00&releaseYn=Y&taskClCd=3"

    # 크롬 브라우저 설정
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")  # 브라우저 창을 최대화

    # 웹 드라이버 설정
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        # URL 열기
        driver.get(url)

        # 페이지 스크롤을 끝까지 내리기
        last_height = driver.execute_script("return document.body.scrollHeight")

        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # pyautogui로 특정 위치 클릭
        pyautogui.moveTo(936, 913)
        pyautogui.click()
        time.sleep(2)
        pyautogui.moveTo(724, 557)
        pyautogui.click()

        time.sleep(2)

        # 캡처할 영역 (x, y, width, height)
        region = (23, 555, 880, 340)  # 원하는 좌표로 수정

        # 화면 캡처
        captured_image_path = capture_screen(region)

        # 이미지에서 한글 텍스트 추출 및 정제
        detect_text(captured_image_path, bidno)
    except Exception as e:
        print(f"웹 페이지 처리 중 오류 발생: {e}")
    finally:
        # 드라이버 종료
        driver.quit()

def process_with_keyboard_interrupt(codes_to_process):
    """키보드 's' 입력으로 중단이 가능한 코드 처리 함수."""
    for code in codes_to_process:
        print(f"Processing bidno: {code}")
        process_bid(code)

        if keyboard.is_pressed('s'):
            print("작업이 중단되었습니다.")
            break

# 메인 함수
if __name__ == "__main__":
    # 데이터베이스에서 코드 조회
    all_codes = fetch_codes_from_database()
    processed_codes = fetch_processed_codes()

    # 처리되지 않은 코드 찾기 (이미 처리된 코드는 생략)
    codes_to_process = [code for code in all_codes if code not in processed_codes]

    # 각 코드에 대해 작업 수행, 키보드 's' 입력으로 중단 가능
    process_with_keyboard_interrupt(codes_to_process)
