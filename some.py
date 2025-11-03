from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from pymongo import MongoClient
from bson import ObjectId
import os
import bcrypt

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change to a secure random key in production

# MongoDB connection
client = MongoClient('mongodb+srv://umatiyaaziz2004_db_user:umatiyaaziz2004@coinmining.evt4i93.mongodb.net/')
db = client['streamflix']
movies_collection = db['movies']
users_collection = db['users']

# Ensure templates directory exists
os.makedirs('templates', exist_ok=True)

@app.route('/')
def index():
    return redirect(url_for('list_movies'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        if users_collection.find_one({'username': username}):
            return render_template('register.html', error="Username already exists.")
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        users_collection.insert_one({'username': username, 'password': hashed_password})
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        user = users_collection.find_one({'username': username})
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            session['user_id'] = str(user['_id'])
            session['watchlist'] = session.get('watchlist', [])
            return redirect(url_for('list_movies'))
        else:
            return render_template('login.html', error="Invalid username or password.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('watchlist', None)
    return redirect(url_for('list_movies'))

@app.route('/add', methods=['GET', 'POST'])
def add_movie():
    if request.method == 'POST':
        try:
            title = request.form['title'].strip()
            year = int(request.form['year'])
            rating = float(request.form['rating'])
            genre = request.form['genre']
            description = request.form['description'].strip()
            image_seed = request.form['image'].strip() if request.form['image'].strip() else None
            links = [link.strip() for link in request.form.getlist('links[]') if link.strip()]

            movie_data = {
                'title': title,
                'year': year,
                'rating': rating,
                'genre': genre,
                'description': description,
                'image_seed': image_seed,
                'links': links
            }

            result = movies_collection.insert_one(movie_data)
            print(f"Movie added with ID: {result.inserted_id}")
            return redirect(url_for('list_movies'))
        except Exception as e:
            print(f"Error adding movie: {e}")
            return render_template('add_movie.html', error="Failed to add movie. Please try again.")
    return render_template('add_movie.html')

@app.route('/movies')
def list_movies():
    try:
        all_movies = list(movies_collection.find().sort('year', -1))
        for m in all_movies:
            m['_id_str'] = str(m['_id'])
    except Exception as e:
        print(f"Error fetching movies: {e}")
        all_movies = []
    watchlist_ids = session.get('watchlist', [])
    is_logged_in = 'user_id' in session
    return render_template('movies.html', movies=all_movies, watchlist_ids=watchlist_ids, is_logged_in=is_logged_in)

@app.route('/home')
def home():
    try:
        all_movies = list(movies_collection.find().sort('year', -1))
        for m in all_movies:
            m['_id_str'] = str(m['_id'])
    except Exception as e:
        print(f"Error fetching movies: {e}")
        all_movies = []
    watchlist_ids = session.get('watchlist', [])
    is_logged_in = 'user_id' in session
    return render_template('home.html', movies=all_movies, watchlist_ids=watchlist_ids, is_logged_in=is_logged_in)

@app.route('/search', methods=['GET', 'POST'])
def search():
    query = request.args.get('query', '').strip().lower()
    try:
        if query:
            all_movies = list(movies_collection.find({
                '$or': [
                    {'title': {'$regex': query, '$options': 'i'}},
                    {'description': {'$regex': query, '$options': 'i'}}
                ]
            }).sort('year', -1))
        else:
            all_movies = list(movies_collection.find().sort('year', -1))
        for m in all_movies:
            m['_id_str'] = str(m['_id'])
    except Exception as e:
        print(f"Error searching movies: {e}")
        all_movies = []
    watchlist_ids = session.get('watchlist', [])
    is_logged_in = 'user_id' in session
    return render_template('movies.html', movies=all_movies, watchlist_ids=watchlist_ids, is_logged_in=is_logged_in, search_query=query)

@app.route('/mylist')
def mylist():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    sort = request.args.get('sort', 'year')
    watchlist_str_ids = session.get('watchlist', [])
    movies = []
    valid_ids = []
    for mid_str in watchlist_str_ids:
        try:
            movie = movies_collection.find_one({'_id': ObjectId(mid_str)})
            if movie:
                movie['_id_str'] = mid_str
                movies.append(movie)
                valid_ids.append(mid_str)
        except:
            pass
    session['watchlist'] = valid_ids
    watchlist_ids = valid_ids
    if sort == 'title':
        movies.sort(key=lambda m: m['title'].lower())
    elif sort == 'year':
        movies.sort(key=lambda m: m['year'], reverse=True)
    elif sort == 'rating':
        movies.sort(key=lambda m: m['rating'], reverse=True)
    else:
        sort = 'year'
        movies.sort(key=lambda m: m['year'], reverse=True)
    return render_template('mylist.html', movies=movies, watchlist_ids=watchlist_ids, sort=sort, is_logged_in=True)

@app.route('/add_to_watchlist/<movie_id>', methods=['POST'])
def add_to_watchlist(movie_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in', 'redirect': url_for('login')}), 401
    watchlist = session.get('watchlist', [])
    if movie_id not in watchlist:
        watchlist.append(movie_id)
        session['watchlist'] = watchlist
        session.modified = True
    return jsonify({'success': True})

@app.route('/remove_from_watchlist/<movie_id>', methods=['POST'])
def remove_from_watchlist(movie_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in', 'redirect': url_for('login')}), 401
    watchlist = session.get('watchlist', [])
    session['watchlist'] = [mid for mid in watchlist if mid != movie_id]
    session.modified = True
    return jsonify({'success': True})

@app.route('/movie/<movie_id>')
def movie_detail(movie_id):
    try:
        movie = movies_collection.find_one({'_id': ObjectId(movie_id)})
        if not movie:
            return render_template('movie_not_found.html'), 404
        movie['_id_str'] = movie_id
        is_logged_in = 'user_id' in session
        in_watchlist = movie_id in session.get('watchlist', [])
        return render_template('movie_detail.html', movie=movie, is_logged_in=is_logged_in, in_watchlist=in_watchlist)
    except Exception as e:
        print(f"Error fetching movie: {e}")
        return render_template('movie_not_found.html'), 404

@app.route('/sync_watchlist', methods=['POST'])
def sync_watchlist():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in', 'redirect': url_for('login')}), 401
    data = request.get_json()
    watchlist = data.get('watchlist', [])
    session['watchlist'] = watchlist
    session.modified = True
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)