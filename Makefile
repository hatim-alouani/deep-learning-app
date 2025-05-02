GREEN=\033[1;32m
YELLOW=\033[1;33m
RED=\033[1;31m
BLUE=\033[1;34m
NC=\033[0m

all:
	@echo -e "$(BLUE)[+] Starting Docker containers...$(NC)"
	@docker compose -f docker-compose.yml up --build -d
	@echo -e "$(GREEN)[✔] Containers are running!$(NC)"
	@echo -e "$(BLUE)[+] Waiting for the database to be ready...$(NC)"
	@sleep 2
	@echo -e "$(GREEN)[✔] Database is ready!$(NC)"

start: all 
	@echo -e "$(BLUE)[+] Running database migrations...$(NC)"
	@docker exec -it flask /bin/bash /flask/insertData/insert.sh

down:
	@echo -e "$(YELLOW)[-] Stopping and removing containers without deleting volumes...$(NC)"
	@docker compose -f docker-compose.yml down
	@echo -e "$(GREEN)[✔] Containers stopped and removed (volumes intact).$(NC)"

clean: 
	@echo -e "$(YELLOW)[-] Stopping and removing containers...$(NC)"
	@docker compose -f docker-compose.yml down -v
	@echo -e "$(GREEN)[✔] Containers stopped and removed.$(NC)"
	@echo -e "$(RED)[!] Removing volumes...$(NC)"
	@docker system prune -af --volumes
	@echo -e "$(GREEN)[✔] Cleanup complete!$(NC)"

YELLOW=\033[1;33m
GREEN=\033[0;32m
RED=\033[0;31m
NC=\033[0m

scrap: all
	@if [ ! -d "myenv" ]; then \
		echo -e "$(YELLOW)[+] Creating virtual environment...$(NC)"; \
		python3 -m venv myenv && \
		echo -e "$(GREEN)[✔] Virtual environment created!$(NC)"; \
		echo -e "$(YELLOW)[+] Installing dependencies...$(NC)"; \
		myenv/bin/pip install -r webscraping/requirements.txt && \
		echo -e "$(GREEN)[✔] Dependencies installed!$(NC)"; \
	fi
	@echo -e "$(YELLOW)[+] Starting web scraping...$(NC)"
	@myenv/bin/python webscraping/scraper.py
	@echo -e "$(GREEN)[✔] Web scraping script completed!$(NC)"

rmscrap:
	@echo -e "$(YELLOW)[-] Removing scraping data...$(NC)"
	@rm -rf amazon_data

restart: down all
