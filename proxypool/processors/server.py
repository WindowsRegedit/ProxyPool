import uuid
import datetime
from flask import Flask, render_template, request, redirect, Blueprint, g, jsonify, url_for
from flask_httpauth import HTTPBasicAuth
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

import sqlite3
from proxypool.storages.redis import RedisClient
from proxypool.setting import API_HOST, API_PORT, API_THREADED, IS_DEV, ENABLE_VERIFY
from itsdangerous.jws import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired, BadSignature


__all__ = ['app']

app = Flask(__name__)
api = Blueprint("api", __name__)
if IS_DEV:
    app.debug = True
DATABASE = 'api_usage.db'
db = SQLAlchemy()
login_manager = LoginManager(app)
login_manager.login_view = 'login'
app.config["SECRET_KEY"] = "proxypoolsystem2.0"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.create_all()

# 用户模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True)
    password_hash = db.Column(db.String)
    login_token = db.Column(db.String(255))


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def revoke_token(self):
        self.login_token = "pps-" + str(uuid.uuid4()).replace(":", "")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
    

def get_db():
    db_analyze = sqlite3.connect(DATABASE)
    db_analyze.row_factory = sqlite3.Row
    return db_analyze


def get_conn():
    """
    get redis client object
    :return:
    """
    if not hasattr(g, 'redis'):
        g.redis = RedisClient()
    return g.redis

def verify(token=""):
    if not ENABLE_VERIFY:
        return True
    s = Serializer(app.config['SECRET_KEY'])
    try:
        token = s.loads(token)
        if not User.query.filter_by(login_token=token).first():
            raise RuntimeError
    except (SignatureExpired, BadSignature, RuntimeError):
        return False
    return True
    

db_analyze = get_db()
db_analyze.execute('CREATE TABLE IF NOT EXISTS api_usage (date DATE PRIMARY KEY, count_random INTEGER, count_all INTEGER, count_count INTEGER)')
today = datetime.date.today().strftime("%Y %m")
db_analyze.execute('INSERT OR IGNORE INTO api_usage (date, count_random, count_all, count_count) VALUES (?, ?, ?, ?)', (today, 0, 0, 0))
db_analyze.commit()


@app.route('/')
def index():
    """
    get home page, you can define your own templates
    :return:
    """
    return render_template("docs.html")

@app.route("/README.md")
def readme():
    return redirect("/static/README.md")

@app.route("/admin/README.md")
def readme_admin():
    return redirect("/static/README-admin.md")

@app.route("/chart")
def chart():
    return render_template("chart.html")

@api.route('/random', methods=["GET", "POST"])
def get_proxy():
    if not ENABLE_VERIFY or verify(request.json.get("token")):
        conn = get_conn()
        proxy = conn.random().string()
        json = {"status": "success", "data": proxy}
        today = datetime.date.today().strftime("%Y %m")
        db_analyze = get_db()
        db_analyze.execute('UPDATE api_usage SET count_random = count_random + 1 WHERE date = ?', (today,))
        db_analyze.commit()
        return jsonify(json)
    return "Token Expired or Incorrect."


@api.route('/all', methods=["GET", "POST"])
def get_proxy_all():
    if not ENABLE_VERIFY or verify(request.json.get("token")):
        conn = get_conn()
        proxies = conn.all()
        data = []
        if proxies:
            for proxy in proxies:
                data.append(str(proxy))
        json = {"status": "success", "data": data}
        today = datetime.date.today().strftime("%Y %m")
        db_analyze = get_db()
        db_analyze.execute('UPDATE api_usage SET count_all = count_all + 1 WHERE date = ?', (today,))
        db_analyze.commit()
        return jsonify(json)
    return "Token Expired or Incorrect."


@api.route('/count', methods=["GET", "POST"])
def get_count():
    if not ENABLE_VERIFY or verify(request.json.get("token")):
        conn = get_conn()
        json = {"status": "success", "data": int(conn.count())}
        today = datetime.date.today().strftime("%Y %m")
        db_analyze = get_db()
        db_analyze.execute('UPDATE api_usage SET count_count = count_count + 1 WHERE date = ?', (today,))
        db_analyze.commit()
        return jsonify(json)
    return "Token Expired or Incorrect."

@api.route("/token", methods=["POST"])
def get_token():
    name = User.query.filter_by(username=request.json.get("name")).first()
    token = User.query.filter_by(login_token=request.json.get("login_token")).first()
    if name and token:
        expires_in= request.json.get("expires_in", 600)
        s = Serializer(app.config['SECRET_KEY'], expires_in=expires_in)
        return jsonify({"status": "success", "token": s.dumps({"token": token.login_token}).decode()})
    return "Error."

@api.route('/analyze')
def analyze():
    db_analyze = get_db()
    rows = db_analyze.execute('SELECT date, count_random, count_all, count_count FROM api_usage ORDER BY date').fetchall()
    dates = [row['date'] for row in rows]
    count_random = [row['count_random'] for row in rows]
    count_all = [row['count_all'] for row in rows]
    count_count = [row['count_count'] for row in rows]
    json = {"status": "success", "data": {"dates": dates, "count_random": count_random, "count_all": count_all, "count_count": count_count}}
    return jsonify(json)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user:
            return 'Username already exists!'

        new_user = User(username=username)
        new_user.set_password(password)
        new_user.revoke_token()
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect(url_for('admin'))

        return 'Invalid username or password'

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin():
    name = current_user.username
    token = current_user.login_token
    return render_template('admin.html', name=name, token=token)

app.register_blueprint(api, url_prefix="/api")

if __name__ == '__main__':
    app.run(host=API_HOST, port=API_PORT, threaded=API_THREADED)
