from sqlalchemy import create_engine, Table, MetaData, select, func

# MySQL 데이터베이스에 연결하기 위한 엔진 생성
DATABASE_URL = 'mysql+mysqlconnector://root:1234@127.0.0.1:3306/nara'
engine = create_engine(DATABASE_URL)

# 메타데이터 객체 생성
metadata = MetaData()

# 데이터베이스와 연결하여 테이블 객체 생성
ticker_table = Table('ticker_2024', metadata, autoload_with=engine)

# 쿼리 작성 (Code 컬럼만 선택)
query = select(ticker_table.c.Code).where(
    (func.length(ticker_table.c.Code) == 14) &
    (func.right(ticker_table.c.Code, 2) == '00')
)

# 쿼리 실행
with engine.connect() as connection:
    result = connection.execute(query).fetchall()

# 결과 출력 및 마지막 3자 제거
for row in result:
    code = row[0]  # 결과 튜플에서 첫 번째 값 추출
    modified_code = code[:-3]  # 마지막 3자 제거
    print(modified_code)
