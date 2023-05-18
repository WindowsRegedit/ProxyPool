import sqlite3
import datetime
from flask import Flask, g, render_template, Blueprint, redirect, jsonify, request
from proxypool.storages.redis import RedisClient
from proxypool.setting import API_HOST, API_PORT, API_THREADED, IS_DEV, ENABLE_VERIFY
from itsdangerous.jws import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired, BadSignature


__all__ = ['app']

app = Flask(__name__)
api = Blueprint("api", __name__)
app.config["SECRET_KEY"] = "proxypoolsystem2.0"
if IS_DEV:
    app.debug = True
DATABASE = 'api_usage.db'

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


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
        s.loads(token)
    except (SignatureExpired, BadSignature):
        return False
    return True
    

db = get_db()
db.execute('CREATE TABLE IF NOT EXISTS api_usage (date DATE PRIMARY KEY, count_random INTEGER, count_all INTEGER, count_count INTEGER)')
today = datetime.date.today().strftime("%Y %m")
db.execute('INSERT OR IGNORE INTO api_usage (date, count_random, count_all, count_count) VALUES (?, ?, ?, ?)', (today, 0, 0, 0))
db.commit()


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
        db = get_db()
        db.execute('UPDATE api_usage SET count_random = count_random + 1 WHERE date = ?', (today,))
        db.commit()
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
        db = get_db()
        db.execute('UPDATE api_usage SET count_all = count_all + 1 WHERE date = ?', (today,))
        db.commit()
        return jsonify(json)
    return "Token Expired or Incorrect."


@api.route('/count', methods=["GET", "POST"])
def get_count():
    if not ENABLE_VERIFY or verify(request.json.get("token")):
        conn = get_conn()
        json = {"status": "success", "data": int(conn.count())}
        today = datetime.date.today().strftime("%Y %m")
        db = get_db()
        db.execute('UPDATE api_usage SET count_count = count_count + 1 WHERE date = ?', (today,))
        db.commit()
        return jsonify(json)
    return "Token Expired or Incorrect."

@api.route("/token")
def get_token():
    s = Serializer(app.config['SECRET_KEY'], expires_in=600)
    return jsonify({"status": "success", "token": s.dumps({"token": app.config["SECRET_KEY"]}).decode()})

@api.route('/analyze')
def analyze():
    db = get_db()
    rows = db.execute('SELECT date, count_random, count_all, count_count FROM api_usage ORDER BY date').fetchall()
    dates = [row['date'] for row in rows]
    count_random = [row['count_random'] for row in rows]
    count_all = [row['count_all'] for row in rows]
    count_count = [row['count_count'] for row in rows]
    json = {"status": "success", "data": {"dates": dates, "count_random": count_random, "count_all": count_all, "count_count": count_count}}
    return jsonify(json)

app.register_blueprint(api, url_prefix="/api")

if __name__ == '__main__':

    app.run(host=API_HOST, port=API_PORT, threaded=API_THREADED)
