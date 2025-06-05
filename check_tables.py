import sqlite3

# DB 파일 경로
db_path = r"C:\caps\myproject\instance\database.db"

# DB 연결
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 모든 테이블 목록 조회
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

# 각 테이블의 구조 조회
for table in tables:
    print(f"Table: {table[0]}")
    cursor.execute(f"PRAGMA table_info({table[0]})")
    columns = cursor.fetchall()

    # 컬럼 정보 출력
    for column in columns:
        print(f"  Column: {column[1]}, Type: {column[2]}")
    print("\n")

conn.close()

