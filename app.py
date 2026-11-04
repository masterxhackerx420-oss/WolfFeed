from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'wolffeed-portable-secret-key-change-me'

DB = os.path.join(os.path.dirname(__file__), 'wolffeed.db')

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    bio TEXT DEFAULT '',
                    created_at TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    likes INTEGER DEFAULT 0,
                    mode TEXT DEFAULT 'classic',
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (post_id) REFERENCES posts (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS likes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    UNIQUE(post_id, user_id)
                )''')
    conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    conn = get_db()
    try:
        conn.execute('INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)',
                     (username, password, datetime.utcnow().isoformat()))
        conn.commit()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username taken'}), 400
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?',
                        (username, password)).fetchone()
    conn.close()
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        return jsonify({'success': True, 'username': user['username']})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/me')
def me():
    if 'user_id' in session:
        return jsonify({'logged_in': True, 'username': session.get('username'), 'user_id': session['user_id']})
    return jsonify({'logged_in': False})

@app.route('/api/posts', methods=['GET'])
def get_posts():
    mode = request.args.get('mode', 'classic')
    conn = get_db()
    query = '''
        SELECT p.*, u.username,
               (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) as comment_count,
               EXISTS(SELECT 1 FROM likes l WHERE l.post_id = p.id AND l.user_id = ?) as liked_by_me
        FROM posts p
        JOIN users u ON p.user_id = u.id
    '''
    params = [session.get('user_id', 0)]
    if mode == 'stories':
        query += ' WHERE p.mode = "story"'
    elif mode == 'groups':
        query += ' WHERE p.mode = "group"'
    else:
        query += ' WHERE p.mode IN ("classic", "live")'
    query += ' ORDER BY p.timestamp DESC LIMIT 50'
    posts = conn.execute(query, params).fetchall()
    result = []
    for p in posts:
        result.append({
            'id': p['id'],
            'username': p['username'],
            'content': p['content'],
            'timestamp': p['timestamp'],
            'likes': p['likes'],
            'comment_count': p['comment_count'],
            'liked_by_me': bool(p['liked_by_me']),
            'mode': p['mode']
        })
    conn.close()
    return jsonify(result)

@app.route('/api/posts', methods=['POST'])
@login_required
def create_post():
    data = request.json
    content = data.get('content', '').strip()
    mode = data.get('mode', 'classic')
    if not content:
        return jsonify({'error': 'Content required'}), 400
    if mode not in ['classic', 'live', 'story', 'group']:
        mode = 'classic'
    conn = get_db()
    conn.execute('INSERT INTO posts (user_id, content, timestamp, mode) VALUES (?, ?, ?, ?)',
                 (session['user_id'], content, datetime.utcnow().isoformat(), mode))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/posts/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    conn = get_db()
    try:
        conn.execute('INSERT INTO likes (post_id, user_id) VALUES (?, ?)',
                     (post_id, session['user_id']))
        conn.execute('UPDATE posts SET likes = likes + 1 WHERE id = ?', (post_id,))
        conn.commit()
        liked = True
    except sqlite3.IntegrityError:
        # Already liked, unlike
        conn.execute('DELETE FROM likes WHERE post_id = ? AND user_id = ?',
                     (post_id, session['user_id']))
        conn.execute('UPDATE posts SET likes = likes - 1 WHERE id = ? AND likes > 0', (post_id,))
        conn.commit()
        liked = False
    finally:
        likes = conn.execute('SELECT likes FROM posts WHERE id = ?', (post_id,)).fetchone()
        conn.close()
    return jsonify({'success': True, 'liked': liked, 'likes': likes['likes'] if likes else 0})

@app.route('/api/posts/<int:post_id>/comments', methods=['GET'])
def get_comments(post_id):
    conn = get_db()
    comments = conn.execute('''
        SELECT c.*, u.username FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.post_id = ?
        ORDER BY c.timestamp ASC
    ''', (post_id,)).fetchall()
    result = [{'id': c['id'], 'username': c['username'], 'content': c['content'], 'timestamp': c['timestamp']} for c in comments]
    conn.close()
    return jsonify(result)

@app.route('/api/posts/<int:post_id>/comments', methods=['POST'])
@login_required
def add_comment(post_id):
    data = request.json
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': 'Content required'}), 400
    conn = get_db()
    conn.execute('INSERT INTO comments (post_id, user_id, content, timestamp) VALUES (?, ?, ?, ?)',
                 (post_id, session['user_id'], content, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    init_db()
    # Seed some demo posts if empty
    conn = get_db()
    count = conn.execute('SELECT COUNT(*) as c FROM posts').fetchone()['c']
    if count == 0:
        # Create demo user if needed
        demo = conn.execute('SELECT id FROM users WHERE username = "demo"').fetchone()
        if not demo:
            conn.execute('INSERT INTO users (username, password, bio, created_at) VALUES (?, ?, ?, ?)',
                         ('demo', 'demo', 'WolfFeed demo account', datetime.utcnow().isoformat()))
            conn.commit()
            demo_id = conn.execute('SELECT id FROM users WHERE username = "demo"').fetchone()['id']
        else:
            demo_id = demo['id']
        demos = [
            ("Welcome to WolfFeed! This is a portable Facebook-like feed. Register and start posting.", 'classic'),
            ("Try the different modes in the sidebar. Posts update live.", 'live'),
            ("Story mode: Quick updates that feel more ephemeral.", 'story'),
            ("Group mode: Imagine discussing Debian, hacking, or WolfSec here.", 'group'),
        ]
        for content, mode in demos:
            conn.execute('INSERT INTO posts (user_id, content, timestamp, mode) VALUES (?, ?, ?, ?)',
                         (demo_id, content, datetime.utcnow().isoformat(), mode))
        conn.commit()
    conn.close()
    print("WolfFeed running at http://127.0.0.1:5000")
    print("Portable app - data stays in this folder.")
    app.run(host='127.0.0.1', port=5000, debug=False)
