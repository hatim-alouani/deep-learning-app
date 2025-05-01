CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT,
    category TEXT,
    discounted_price FLOAT,
    actual_price FLOAT,
    discount_percentage FLOAT,
    rating FLOAT,
    rating_count INT,
    about_product TEXT,
    product_link TEXT,
    category_id INT
);