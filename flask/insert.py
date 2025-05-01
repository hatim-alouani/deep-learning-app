import os
import csv
import psycopg2
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'dbname': os.getenv('POSTGRES_DB', 'postgres'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
    'host': os.getenv('POSTGRES_HOST', 'postgresql'),
    'port': os.getenv('POSTGRES_PORT', 5432)
}

TABLE_NAME = 'products'
CSV_DIR = 'amazon_data'
CSV_FILES = [
    'electronics.csv', 'clothing.csv', 'home_appliances.csv',
    'beauty.csv', 'sports.csv', 'automotive.csv',
    'books.csv', 'games.csv', 'groceries.csv', 'furniture.csv'
]

INSERT_QUERY = f"""
INSERT INTO {TABLE_NAME} (
    product_id, product_name, category, discounted_price, actual_price,
    discount_percentage, rating, rating_count, about_product, product_link, category_id
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

CATEGORY_MAPPING = {
    'electronics': 1,
    'home_appliances': 2,
    'books': 3,
    'clothing': 4,
    'sports': 5,
    'toys': 6,
    'beauty': 7,
    'groceries': 8,
    'furniture': 9,
    'automotive': 10
}

def insert_csv(filepath):
    category_name = os.path.splitext(os.path.basename(filepath))[0]
    category_id = CATEGORY_MAPPING.get(category_name)
    
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = []
            for row in reader:
                if len(row) < 9 or any(not row[i].strip() for i in range(9)):
                    continue
                rows.append((
                    row[0],  # product_id
                    row[1],  # product_name
                    row[2],  # category
                    float(row[3]),  # discounted_price
                    float(row[4]),  # actual_price
                    float(row[5]),  # discount_percentage
                    float(row[6]),  # rating
                    int(row[7]),    # rating_count
                    row[8],         # about_product
                    row[9],         # product_link
                    category_id     # category_id
                ))
            if rows:
                cursor.executemany(INSERT_QUERY, rows)
                conn.commit()
    except Exception as e:
        print(e)
    finally:
        cursor.close()
        conn.close()

def main():
    filepaths = [os.path.join(CSV_DIR, filename) for filename in CSV_FILES]
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(insert_csv, filepaths)

if __name__ == '__main__':
    main()
