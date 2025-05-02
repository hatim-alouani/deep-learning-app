import os
import time
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
import psycopg2
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.preprocessing import StandardScaler

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

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '2908')
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@postgresql/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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

@app.route('/get_recommendations')
def get_recommendations_page():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('recommendations.html')

@app.route('/recommendations')
def legacy_redirect():
    return redirect(url_for('get_recommendations_page'))

@app.route('/api/recommendations')
def api_recommendations():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    
    preferred_categories = db.session.query(UserPreference.category_id).filter_by(user_id=user_id).all()
    preferred_categories = [cat_id for (cat_id,) in preferred_categories]
    
    if not preferred_categories:
        return jsonify({'error': 'No preferred categories selected.'}), 404
    
    products = Product.query.filter(
        Product.category_id.in_(preferred_categories),
        Product.discount_percentage > 0  
    ).all()
    
    if not products:
        return jsonify({'error': 'No discounted products found in your preferred categories.'}), 404

    features = []
    product_map = []
    
    for product in products:
        if None in (product.discounted_price, product.actual_price, 
                    product.discount_percentage, product.rating, product.rating_count):
            continue
            
        feature_vector = [
            float(product.discounted_price),
            float(product.actual_price),
            float(product.discount_percentage),
            float(product.rating),
            float(product.rating_count)
        ]
        
        features.append(feature_vector)
        product_map.append(product)
    
    if not features:
        return jsonify({'recommendations': []})
    
    X = np.array(features)
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    discount_weight = 0.35
    rating_weight = 0.35
    price_weight = 0.15
    rating_count_weight = 0.15

    max_price = np.max(X[:, 0]) if len(X) > 0 else 1
    normalized_prices = 1 - (X[:, 0] / max_price)
    
    weighted_scores = (
        price_weight * normalized_prices +
        discount_weight * (X[:, 2] / 100) +  
        rating_weight * (X[:, 3] / 5) +    
        rating_count_weight * (np.log1p(X[:, 4]) / np.max(np.log1p(X[:, 4]))) 
    )
    
    model = Sequential([
        Dense(128, input_dim=X_scaled.shape[1], activation='relu'),
        BatchNormalization(),
        Dropout(0.3),
        Dense(64, activation='relu'),
        BatchNormalization(),
        Dropout(0.2),
        Dense(32, activation='relu'),
        Dense(1, activation='sigmoid')
    ])
    
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='mean_squared_error'
    )
    

    early_stopping = EarlyStopping(monitor='loss', patience=20, restore_best_weights=True)
    model.fit(
        X_scaled, 
        weighted_scores,
        epochs=100, 
        batch_size=min(32, len(X_scaled)),
        callbacks=[early_stopping],
        verbose=0
    )
    

    predictions = model.predict(X_scaled).flatten()
    
    top_indices = np.argsort(predictions)[-20:][::-1]
    
    selected_indices = []
    price_buckets = {}
    max_per_bucket = 2 

    for idx in top_indices:
        price = product_map[idx].discounted_price
        bucket = int(price / 500) 
        
        if bucket not in price_buckets:
            price_buckets[bucket] = []
        
        if len(price_buckets[bucket]) < max_per_bucket:
            price_buckets[bucket].append(idx)
            selected_indices.append(idx)
            
            if len(selected_indices) >= 5:
                break

    if len(selected_indices) < 5:
        remaining = [idx for idx in top_indices if idx not in selected_indices]
        selected_indices.extend(remaining[:5-len(selected_indices)])
    

    recommended_products = [product_map[i] for i in selected_indices[:5]]
    
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
            'category_name': category_name,
            'product_link': product.product_link
        }

    return jsonify({'recommendations': [product_to_dict(p) for p in recommended_products]})

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