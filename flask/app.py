import os
import time
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
import psycopg2
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam

# Wait for PostgreSQL to be ready
while True:
    try:
        conn = psycopg2.connect(
            dbname=os.environ.get('POSTGRES_DB', 'postgres'),
            user=os.environ.get('POSTGRES_USER', 'postgres'),
            password=os.environ.get('POSTGRES_PASSWORD', 'postgres'),
            host=os.environ.get('POSTGRES_HOST', 'postgresql'),
            port=os.environ.get('POSTGRES_PORT', 5432)
        )
        conn.close()
        print("PostgreSQL is available.")
        break
    except psycopg2.OperationalError:
        print("Waiting for PostgreSQL...")
        time.sleep(2)

# Flask setup
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '2908')
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@postgresql/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# DB Models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    preferences = db.relationship('UserPreference', backref='user', lazy=True, cascade="all, delete-orphan")

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class UserPreference(db.Model):
    __tablename__ = 'user_preferences'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    category = db.relationship('Category', backref='preferences')

class Product(db.Model):
    __tablename__ = 'products'
    product_id = db.Column(db.Text, primary_key=True)
    product_name = db.Column(db.Text, nullable=False)
    category = db.Column(db.Text, nullable=False)
    discounted_price = db.Column(db.Float)
    actual_price = db.Column(db.Float)
    discount_percentage = db.Column(db.Float)
    rating = db.Column(db.Float)
    rating_count = db.Column(db.Integer)
    about_product = db.Column(db.Text)
    product_link = db.Column(db.Text)
    category_id = db.Column(db.Integer)

@app.before_first_request
def create_tables():
    db.create_all()
    categories = [
        "Electronics", "Home_and_Kitchen", "Books", "Clothing", 
        "Sports_and_Outdoors", "Toys_and_Games", "Beauty_and_Personal_Care", 
        "Grocery_and_Gourmet_Food", "Health_and_Household", "Pet_Supplies"
    ]
    for category_name in categories:
        if not Category.query.filter_by(name=category_name).first():
            db.session.add(Category(name=category_name))
    db.session.commit()

# Recommendation Routes
@app.route('/get_recommendations')
def get_recommendations_page():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('recommendations.html')

@app.route('/recommendations')
def legacy_redirect():
    return redirect(url_for('get_recommendations_page'))  # Ensure this references the correct route

@app.route('/api/recommendations')
def api_recommendations():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    
    # Get the user's preferred categories
    preferred_categories = db.session.query(UserPreference.category_id).filter_by(user_id=user_id).all()
    preferred_categories = [cat_id for (cat_id,) in preferred_categories]
    
    # Get all products in the preferred categories
    products = Product.query.filter(Product.category_id.in_(preferred_categories)).all()
    
    if not products:
        return jsonify({'error': 'No products found for the selected categories.'}), 404

    # Collect product features for the model
    features = []
    product_map = []
    for product in products:
        if None not in (product.discounted_price, product.actual_price, product.discount_percentage, product.rating, product.rating_count):
            features.append([
                product.discounted_price,
                product.actual_price,
                product.discount_percentage,
                product.rating,
                product.rating_count
            ])
            product_map.append(product)

    # Check if features are collected
    if features:
        # Create recommendation model dynamically
        recommendation_model = Sequential([
            Dense(64, input_dim=5, activation='relu'),
            Dense(32, activation='relu'),
            Dense(1, activation='linear')
        ])
        recommendation_model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
        
        # Train the model using product features
        X = np.array(features)
        y = np.random.rand(len(features))  # Dummy target for recommendation purpose
        recommendation_model.fit(X, y, epochs=10, batch_size=32, verbose=0)
        
        # Generate recommendations based on the model's prediction scores
        scores = recommendation_model.predict(X).flatten()
        top_indices = np.argsort(scores)[-5:][::-1]
        top_products = [product_map[i] for i in top_indices]

        def product_to_dict(product):
            category_name = db.session.query(Category.name).filter_by(id=product.category_id).scalar() or ''
            return {
                'product_name': product.product_name,
                'discounted_price': product.discounted_price,
                'actual_price': product.actual_price,
                'discount_percentage': product.discount_percentage,
                'rating': product.rating,
                'rating_count': product.rating_count,
                'about_product': product.about_product,
                'category_name': category_name
            }

        return jsonify({'recommendations': [product_to_dict(p) for p in top_products]})
    else:
        return jsonify({'recommendations': []})

# Additional routes and login flow (sign-up, login, profile, etc.)
@app.route('/')
def index():
    return render_template('home.html')

@app.route('/signin', methods=['POST'])
def signin():
    email = request.form.get('email')
    name = request.form.get('name')
    user = User.query.filter_by(email=email, name=name).first()
    if user:
        session['user_id'] = user.id
        session['user_name'] = user.name
        return redirect(url_for('welcome'))
    flash('User does not exist. Please sign up.')
    return redirect(url_for('index'))

@app.route('/signup')
def signup_form():
    categories = Category.query.all()
    return render_template('signup.html', categories=categories)

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    email = request.form.get('email')
    selected_categories = request.form.getlist('categories')
    if User.query.filter_by(email=email).first():
        flash('Email already registered.')
        return redirect(url_for('signup_form'))
    user = User(name=name, email=email)
    db.session.add(user)
    db.session.flush()
    for category_name in selected_categories:
        category = Category.query.filter_by(name=category_name).first()
        if category:
            db.session.add(UserPreference(user_id=user.id, category_id=category.id))
    db.session.commit()
    session['user_id'] = user.id
    session['user_name'] = user.name
    flash('Registration successful!')
    return redirect(url_for('welcome'))

@app.route('/welcome')
def welcome():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('index'))
    prefs = db.session.query(Category.name).join(UserPreference).filter(UserPreference.user_id == user.id).all()
    preferences = [p[0] for p in prefs]
    return render_template('welcome.html', user=user, preferences=preferences)

@app.route('/edit_profile')
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('index'))
    all_categories = Category.query.all()
    user_category_ids = [pref.category_id for pref in UserPreference.query.filter_by(user_id=user.id).all()]
    return render_template('edit_profile.html', user=user, categories=all_categories, selected_categories=user_category_ids)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('index'))
    user.name = request.form.get('name')
    user.email = request.form.get('email')
    selected_categories = request.form.getlist('categories')
    UserPreference.query.filter_by(user_id=user.id).delete()
    for category_name in selected_categories:
        category = Category.query.filter_by(name=category_name).first()
        if category:
            db.session.add(UserPreference(user_id=user.id, category_id=category.id))
    db.session.commit()
    session['user_name'] = user.name
    flash('Profile updated successfully!')
    return redirect(url_for('welcome'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
