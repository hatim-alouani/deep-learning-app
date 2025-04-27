import psycopg2

# Database connection details
DB_HOST = 'postgresql'  # Use 'postgresql' as the hostname for the Postgres service
DB_NAME = 'data'  # Replace with your database name
DB_USER = 'hatim'  # Your Postgres user
DB_PASSWORD = 'hatim'  # Your Postgres password

def create_database_and_tables():
    try:
        # Connect to PostgreSQL to create the database if not exists
        conn = psycopg2.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # Create database if it doesn't exist
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
        exists = cursor.fetchone()
        if not exists:
            cursor.execute(f"CREATE DATABASE {DB_NAME}")
            print(f"Database {DB_NAME} created successfully.")
        else:
            print(f"Database {DB_NAME} already exists.")

        # Connect to the newly created database
        conn.close()
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()

        # Create the products table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id BIGINT PRIMARY KEY,
            product_name VARCHAR(255),
            category VARCHAR(255),
            discounted_price FLOAT,
            actual_price FLOAT,
            discount_percentage FLOAT,
            rating FLOAT,
            rating_count INT,
            about_product TEXT,
            user_id INT,
            user_name VARCHAR(255),
            review_id BIGINT PRIMARY KEY,
            review_title VARCHAR(255),
            review_content TEXT,
            img_link TEXT,
            product_link TEXT
        );
        """)
        conn.commit()
        print("Table products created successfully.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    create_database_and_tables()
