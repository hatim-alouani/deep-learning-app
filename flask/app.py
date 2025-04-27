import psycopg2
from flask import Flask, render_template, request

app = Flask(__name__)

# Database connection details
DB_HOST = 'postgresql'  # The service name in Docker Compose
DB_NAME = 'data'
DB_USER = 'hatim'
DB_PASSWORD = 'hatim'

def get_db_connection():
    connection = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return connection

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit_preferences', methods=['POST'])
def submit_preferences():
    selected_preferences = request.form.getlist('preferences')
    user_id = 1

    conn = get_db_connection()
    cursor = conn.cursor()

    for category in selected_preferences:
        cursor.execute("""
            INSERT INTO user_preferences (user_id, category_name) 
            VALUES (%s, %s)
        """, (user_id, category))

    conn.commit()
    cursor.close()
    conn.close()

    return "Preferences submitted and saved in the database!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
