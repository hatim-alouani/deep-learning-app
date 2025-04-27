import psycopg2
import csv

DB_HOST = 'postgresql'  # Postgres service name from docker-compose.yml
DB_NAME = 'data'  # Your database name
DB_USER = 'hatim'  # Your Postgres user
DB_PASSWORD = 'hatim'  # Your Postgres password

def insert_data_from_csv(csv_file):
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()

        # Open the CSV file and insert rows into the database
        with open(csv_file, 'r') as file:
            csv_reader = csv.DictReader(file)  # Using DictReader to read CSV into a dictionary
            for row in csv_reader:
                cursor.execute("""
                    INSERT INTO products (
                        product_id, product_name, category, discounted_price, actual_price, 
                        discount_percentage, rating, rating_count, about_product, 
                        user_id, user_name, review_id, review_title, review_content, 
                        img_link, product_link
                    ) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    row['product_id'], row['product_name'], row['category'], row['discounted_price'],
                    row['actual_price'], row['discount_percentage'], row['rating'], row['rating_count'],
                    row['about_product'], row['user_id'], row['user_name'], row['review_id'], row['review_title'],
                    row['review_content'], row['img_link'], row['product_link']
                ))

        conn.commit()
        print(f"Data from {csv_file} inserted successfully.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    csv_file = '/flask/webscraping/amazon.csv'
    insert_data_from_csv(csv_file)
