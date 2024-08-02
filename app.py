from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import json
import openai

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Load the story data from the JSON file
with open('story_data.json') as f:
    story_data = json.load(f)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    progress = db.Column(db.String, nullable=True)
    items = db.Column(db.String, nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Login failed. Check your credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/story', methods=['POST'])
def story():
    data = request.json
    current_scene = data.get('current_scene', 'start')
    name = data.get('name', 'Adventurer')

    scene = story_data.get(current_scene, None)
    if scene:
        scene_text = scene['text'].replace("{name}", name)
        response = {
            'text': scene_text,
            'choices': scene['choices'],
            'image': scene['image'],
            'sound': scene['sound'],
            'items': scene.get('items', []),
            'ending': scene.get('ending', False)
        }
    else:
        response = {'text': 'Scene not found.'}

    return jsonify(response)

@app.route('/save_progress', methods=['POST'])
@login_required
def save_progress():
    current_scene = request.json.get('current_scene')
    items = request.json.get('items', [])
    current_user.progress = current_scene
    current_user.items = ','.join(items)
    db.session.commit()
    return jsonify({"message": "Progress saved"})

@app.route('/load_progress')
@login_required
def load_progress():
    if current_user.progress:
        items = current_user.items.split(',') if current_user.items else []
        return jsonify({"current_scene": current_user.progress, "items": items})
    return jsonify({"current_scene": 'start', "items": []})

openai.api_key = 'your_openai_api_key'

def generate_story(prompt):
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150
    )
    return response.choices[0].text.strip()

@app.route('/generate_story', methods=['POST'])
def generate_story_route():
    prompt = request.json.get('prompt')
    story_text = generate_story(prompt)
    return jsonify({"story_text": story_text})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
