# 🎉 **Event Management System**

"This project is a full-featured Flask-based Real-Time Product Recommendation System that recommends discounted Amazon products to users based on their preferences. It uses a deep learning model built with TensorFlow, stores data in PostgreSQL, and is fully containerized using Docker. The system includes automated web scraping, data insertion, and a responsive web interface for personalized recommendations.

---

## 📁 **Project Structure**

```
/deep-learning-app
├── Makefile
├── db.sqlite3
├── docker-compose.yml
├── flask
│   ├── app.py
│   ├── dockerfile
│   ├── requirements.txt
│   └── templates
│       ├── edit_profile.html
│       ├── home.html
│       ├── loading.html
│       ├── recommendations.html
│       ├── signup.html
│       └── welcome.html
├── insertData
│   ├── insert.py
│   └── insert.sh
├── myenv
├── nginx
│   └── default.conf
├── postgresql
│   ├── dockerfile
│   └── init.sql
└── webscraping
    ├── requirements.txt
    └── scraper.py

```
## 🛠 Prerequisites

Before running this project, make sure you have the following installed:
- Docker
- Docker Compose
- Make

## 🔧 Installation

```bash
git clone https://github.com/hatim-alouani/deep-learning-app
```

```bash
cd pdeep-learning-app
```

# 🔧 **Build and Start the Application**

```bash
make scrap
```
Run a real-time Amazon data scraper

```bash
make start
```

Builds Docker containers

Installs Composer dependencies

Starts the app with Docker Compose

Run a script that inserts scraped data every 30 seconds


# 🧹 **Clean Everything**

```bash
make clean
```

Stops all containers

Removes Docker containers and volumes

# ⚠️ **Final Note**

Keep Windows open... but use MacOS


## 👤 Contributors
- **ALOUANI Hatim** - [GitHub](https://github.com/hatim-alouani)

## 📜 License
This project is licensed under the MIT License.
