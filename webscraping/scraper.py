import time
import random
import csv
import pandas as pd
import re
import logging
import os
import threading
from queue import Queue
from urllib.parse import urljoin, urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/91.0.4472.80 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:95.0) Gecko/20100101 Firefox/95.0'
]

categories = [
    {"name": "Electronics", "url": "https://www.amazon.com/s?k=electronics"},
    {"name": "Home_and_Kitchen", "url": "https://www.amazon.com/s?k=home+and+kitchen"},
    {"name": "Books", "url": "https://www.amazon.com/s?k=books"},
    {"name": "Clothing", "url": "https://www.amazon.com/s?k=clothing"},
    {"name": "Sports_and_Outdoors", "url": "https://www.amazon.com/s?k=sports+and+outdoors"},
    {"name": "Toys_and_Games", "url": "https://www.amazon.com/s?k=toys+and+games"},
    {"name": "Beauty_and_Personal_Care", "url": "https://www.amazon.com/s?k=beauty+and+personal+care"},
    {"name": "Grocery_and_Gourmet_Food", "url": "https://www.amazon.com/s?k=grocery+and+gourmet+food"},
    {"name": "Health_and_Household", "url": "https://www.amazon.com/s?k=health+and+household"},
    {"name": "Pet_Supplies", "url": "https://www.amazon.com/s?k=pet+supplies"}
]

file_lock = threading.Lock()

def setup_driver():
    options = Options()
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    options.add_argument("--headless")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    driver.set_window_size(1366, 768)
    
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def get_product_id(url):
    match = re.search(r'/dp/([A-Z0-9]{10})', url)
    if match:
        return match.group(1)
    return "N/A"

def extract_price_value(price_text):
    if price_text == "N/A":
        return None
    
    numeric_string = re.sub(r'[^\d.]', '', price_text)
    try:
        return float(numeric_string)
    except ValueError:
        return None

def extract_percentage(percentage_text):
    if percentage_text == "N/A" or not percentage_text:
        return None
    
    match = re.search(r'(\d+\.?\d*)', percentage_text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None

def get_product_details(driver, url, category_name):
    try:
        logger.info(f"Navigating to product: {url}")
        driver.get(url)
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "productTitle"))
        )
        
        time.sleep(random.uniform(2, 5))
        
        product_data = {
            "product_id": get_product_id(url),
            "product_name": "N/A",
            "category": category_name,
            "discounted_price": None,
            "actual_price": None,
            "discount_percentage": None,
            "rating": None,
            "rating_count": 0,
            "about_product": "N/A",
            "product_link": url
        }
        
        try:
            product_data["product_name"] = driver.find_element(By.ID, "productTitle").text.strip()
        except NoSuchElementException:
            pass
        
        price_text = "N/A"
        try:
            price_elem = driver.find_element(By.CSS_SELECTOR, '.a-price .a-offscreen')
            price_text = price_elem.get_attribute('textContent').strip()
        except NoSuchElementException:
            try:
                price_elem = driver.find_element(By.CSS_SELECTOR, '#priceblock_ourprice, #priceblock_dealprice')
                price_text = price_elem.text.strip()
            except NoSuchElementException:
                pass
        
        product_data["discounted_price"] = extract_price_value(price_text)
        
        # Skip products with missing price
        if product_data["discounted_price"] is None:
            return None
        
        original_price_text = "N/A"
        try:
            original_price = driver.find_element(By.CSS_SELECTOR, '.a-text-strike')
            original_price_text = original_price.text.strip()
            product_data["actual_price"] = extract_price_value(original_price_text)
            
            if product_data["discounted_price"] and product_data["actual_price"]:
                if product_data["actual_price"] > 0:
                    discount = ((product_data["actual_price"] - product_data["discounted_price"]) / product_data["actual_price"]) * 100
                    product_data["discount_percentage"] = round(discount, 1)
        except NoSuchElementException:
            pass
        
        try:
            rating_elem = driver.find_element(By.CSS_SELECTOR, 'span[data-hook="rating-out-of-text"], .a-icon-star')
            rating_text = rating_elem.get_attribute('textContent') or rating_elem.get_attribute('aria-label')
            if rating_text:
                rating_str = rating_text.split(' ')[0]
                try:
                    product_data["rating"] = float(rating_str)
                except ValueError:
                    pass
        except NoSuchElementException:
            pass
        
        try:
            count_elem = driver.find_element(By.ID, 'acrCustomerReviewText')
            count_text = count_elem.text.strip()
            count_str = count_text.split(' ')[0].replace(',', '')
            try:
                product_data["rating_count"] = int(count_str)
            except ValueError:
                pass
        except NoSuchElementException:
            pass
        
        try:
            bullet_points = driver.find_elements(By.CSS_SELECTOR, '#feature-bullets li .a-list-item')
            if bullet_points:
                descriptions = [elem.text.strip() for elem in bullet_points]
                product_data["about_product"] = ' '.join(descriptions)
        except NoSuchElementException:
            try:
                description = driver.find_element(By.ID, 'productDescription')
                product_data["about_product"] = description.text.strip()
            except NoSuchElementException:
                pass
        
        return product_data
    except Exception as e:
        logger.error(f"Error scraping product {url}: {str(e)}")
        return None

def get_next_page_url(driver, current_url):
    try:
        next_page_btn = driver.find_element(By.CSS_SELECTOR, '.s-pagination-next:not(.s-pagination-disabled)')
        if next_page_btn:
            return next_page_btn.get_attribute("href")
    except NoSuchElementException:
        pass
    
    return None

def get_products_from_category(driver, category):
    logger.info(f"Scraping category: {category['name']}")
    all_product_urls = []
    current_page = 1
    current_url = category['url']
    max_pages = 5
    
    while current_url and current_page <= max_pages:
        try:
            logger.info(f"Navigating to page {current_page}: {current_url}")
            driver.get(current_url)
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.s-result-item'))
            )
            
            time.sleep(random.uniform(3, 6))
            
            product_cards = driver.find_elements(By.CSS_SELECTOR, '.s-result-item[data-component-type="s-search-result"]')
            
            product_urls = []
            logger.info(f"Found {len(product_cards)} product cards on page {current_page}")
            
            for card in product_cards:
                try:
                    product_link = card.find_element(By.CSS_SELECTOR, 'h2 a, .a-link-normal.a-text-normal')
                    if product_link:
                        href = product_link.get_attribute('href')
                        if href and ('/dp/' in href or '/gp/product/' in href):
                            product_urls.append(href)
                            logger.info(f"Added product URL: {href}")
                except NoSuchElementException:
                    continue
            
            all_product_urls.extend(product_urls)
            
            next_url = get_next_page_url(driver, current_url)
            if next_url:
                current_url = next_url
                current_page += 1
                time.sleep(random.uniform(5, 8))
            else:
                break
        except Exception as e:
            logger.error(f"Error processing page {current_page} of {category['name']}: {str(e)}")
            break
    
    logger.info(f"Found a total of {len(all_product_urls)} products across {current_page} pages in {category['name']}")
    return all_product_urls

def save_to_csv(products, category_name):
    if not products:
        logger.warning(f"No products to save for {category_name}")
        return
    
    filename = f"amazon_data/{category_name.lower().replace(' ', '_')}.csv"
    
    with file_lock:
        try:
            df = pd.DataFrame(products)
            columns = [
                "product_id", 
                "product_name", 
                "category", 
                "discounted_price", 
                "actual_price", 
                "discount_percentage", 
                "rating", 
                "rating_count", 
                "about_product", 
                "product_link"
            ]
            df = df[columns]
            df.to_csv(filename, index=False)
            logger.info(f"Successfully saved {len(products)} products to {filename}")
        except Exception as e:
            logger.error(f"Error saving CSV for {category_name}: {str(e)}")

def process_category(category):
    thread_name = threading.current_thread().name
    logger.info(f"{thread_name} - Processing category: {category['name']}")
    
    driver = setup_driver()
    products = []
    
    try:
        product_urls = get_products_from_category(driver, category)
        
        product_urls = product_urls[:100]
        
        logger.info(f"{thread_name} - Will scrape {len(product_urls)} products for {category['name']}")
        
        for idx, url in enumerate(product_urls):
            try:
                logger.info(f"{thread_name} - Processing product {idx+1}/{len(product_urls)} in {category['name']}")
                product_data = get_product_details(driver, url, category['name'])
                
                if product_data:
                    products.append(product_data)
                    
                time.sleep(random.uniform(3, 8))
                
                if (idx + 1) % 10 == 0:
                    save_to_csv(products, category['name'])
                    logger.info(f"{thread_name} - Saved intermediate results ({idx+1} products) for {category['name']}")
            except Exception as e:
                logger.error(f"{thread_name} - Error processing product {url}: {str(e)}")
                continue
        
        if products:
            save_to_csv(products, category['name'])
            logger.info(f"{thread_name} - Completed scraping {len(products)} products for {category['name']}")
    except Exception as e:
        logger.error(f"{thread_name} - Error processing category {category['name']}: {str(e)}")
    finally:
        driver.quit()

def category_thread_worker(category_queue):
    while not category_queue.empty():
        try:
            category = category_queue.get()
            process_category(category)
            category_queue.task_done()
        except Exception as e:
            logger.error(f"Thread error: {str(e)}")

def main():
    os.makedirs("amazon_data", exist_ok=True)
    
    with file_lock:
        with open('amazon_data/categories.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Category Name', 'URL'])
            for category in categories:
                writer.writerow([category['name'], category['url']])
    
    logger.info("Category list saved to amazon_data/categories.csv")
    
    category_queue = Queue()
    
    for category in categories:
        category_queue.put(category)
    
    threads = []
    for i in range(min(10, len(categories))):
        thread = threading.Thread(
            target=category_thread_worker, 
            args=(category_queue,),
            name=f"Thread-{i+1}"
        )
        thread.daemon = True
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    logger.info("All threads completed. Scraping finished.")

if __name__ == "__main__":
    main()