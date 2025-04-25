GREEN=\033[1;32m
YELLOW=\033[1;33m
RED=\033[1;31m
BLUE=\033[1;34m
NC=\033[0m

all:
	@echo -e "$(BLUE)[+] Starting Docker containers...$(NC)"
	@docker compose -f docker-compose.yml up --build -d
	@echo -e "$(GREEN)[✔] Containers are running!$(NC)"

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

restart: down all
