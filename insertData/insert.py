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
    'electronics.csv', 'clothing.csv', 'home_and_kitchen.csv',
    'beauty_and_personal_care.csv', 'sports_and_outdoors.csv', 'health_and_household.csv',
    'Books.csv', 'Toys_and_Games.csv', 'grocery_and_Gourmet_Food.csv', 'pet_Supplies.csv'
]

INSERT_QUERY = f"""
INSERT INTO {TABLE_NAME} (
    product_id, product_name, category, discounted_price, actual_price,
    discount_percentage, rating, rating_count, about_product, product_link, category_id
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (product_id) DO NOTHING
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

total_products_added = 0
total_products_existing = 0
total_products_invalid = 0

def add_product_link_column():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        alter_query = """
        ALTER TABLE products ADD COLUMN IF NOT EXISTS product_link TEXT;
        """
        cursor.execute(alter_query)
        conn.commit()
    except Exception as e:
        print(f"Error adding column: {e}")
    finally:
        cursor.close()
        conn.close()

def insert_csv(filepath):
    global total_products_added, total_products_existing, total_products_invalid
    
    category_name = os.path.splitext(os.path.basename(filepath))[0]
    category_id = CATEGORY_MAPPING.get(category_name)
    
    file_products_added = 0
    file_products_existing = 0
    file_products_invalid = 0
    
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        print(f"[!] File not found or empty: {filepath}")
        return
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            
            for row in reader:
                if len(row) < 9 or any(not row[i].strip() for i in range(9)):
                    file_products_invalid += 1
                    continue
                
                product_id = row[0]
                
                cursor.execute(f"SELECT 1 FROM {TABLE_NAME} WHERE product_id = %s LIMIT 1", (product_id,))
                exists = cursor.fetchone() is not None
                
                if exists:
                    print(f"[→] Product already exists: {product_id}")
                    file_products_existing += 1
                    continue
           
                try:
                    discount_percentage = float(row[5])
                    if discount_percentage < -100 or discount_percentage > 100:
                        print(f"[⚠] Invalid discount percentage for product {product_id}: {discount_percentage}%")
                        file_products_invalid += 1
                        continue
                    
                    if discount_percentage < 0 and discount_percentage >= -100:
                        discount_percentage = abs(discount_percentage)
                except ValueError:
                    file_products_invalid += 1
                    continue
                
                try:
                    cursor.execute(INSERT_QUERY, (
                        product_id,               
                        row[1],                    
                        row[2],                   
                        float(row[3]),             
                        float(row[4]),            
                        discount_percentage,       
                        float(row[6]),           
                        int(row[7]),          
                        row[8],             
                        row[9] if len(row) > 9 else "",  
                        category_id  
                    ))
                    conn.commit()
                    print(f"[✓] Added product: {product_id}")
                    file_products_added += 1
                except Exception as e:
                    print(f"[✗] Error adding product {product_id}: {str(e)}")
                    file_products_invalid += 1
        
        total_products_added += file_products_added
        total_products_existing += file_products_existing
        total_products_invalid += file_products_invalid
        
        print(f"[📊] {category_name.capitalize()} import summary: {file_products_added} added, {file_products_existing} existing, {file_products_invalid} invalid")
    
    except Exception as e:
        print(f"[✗] Error processing file {filepath}: {str(e)}")
    finally:
        cursor.close()
        conn.close()

def main():
    print("[🚀] Starting product import process...")
    add_product_link_column()
    print("[✓] Product link column ensured")
    
    filepaths = [os.path.join(CSV_DIR, filename) for filename in CSV_FILES]
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(insert_csv, filepaths)
    
    print("\n" + "="*50)
    print(f"[📊] IMPORT COMPLETE")
    print(f"[📊] Total products added: {total_products_added}")
    print(f"[📊] Total products already existing: {total_products_existing}")
    print(f"[📊] Total products invalid or skipped: {total_products_invalid}")
    print("="*50)

if __name__ == '__main__':
    main()