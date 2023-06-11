import datetime
import uuid

import jwt
from flask import Flask, render_template, request, redirect, Blueprint, g, jsonify, url_for, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from proxypool.setting import API_HOST, API_PORT, API_THREADED, IS_DEV
from proxypool.storages.redis import RedisClient

__all__ = ['app']

app = Flask(__name__)
api = Blueprint("api", __name__)
if IS_DEV:
    app.debug = True
db = SQLAlchemy()
login_manager = LoginManager(app)
login_manager.login_view = 'login'
app.config["SECRET_KEY"] = "ProxyPool System"
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
    permission = db.Column(db.Integer, default=0)  # 0 for normal user, 1 for manager
    login_token = db.Column(db.String(255), unique=True)
    random_analyze = db.Column(db.Integer, default=0)
    count_analyze = db.Column(db.Integer, default=0)
    all_analyze = db.Column(db.Integer, default=0)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def revoke_token(self):
        self.login_token = "pps-" + str(uuid.uuid4()).replace(":", "")


def create_manager(name, pwd):
    user = User()
    user.username = name
    user.password_hash = generate_password_hash(pwd)
    user.revoke_token()
    user.permission = 1
    db.session.add(user)
    db.session.commit()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def get_conn():
    """
    get redis client object
    :return:
    """
    if not hasattr(g, 'redis'):
        g.redis = RedisClient()
    return g.redis


def verify(token=""):
    try:
        token = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"]).get("token")
        if not User.query.filter_by(login_token=token).first():
            raise RuntimeError
        return token
    except (jwt.exceptions.InvalidSignatureError, RuntimeError):
        return False


@app.errorhandler(404)
def not_found(e):
    return redirect(url_for("index"))


@app.errorhandler(403)
def no_permission(e):
    return render_template("403.html")


@app.errorhandler(405)
def not_allowed(e):
    return abort(403)


@app.route('/')
def index():
    """
    get home page, you can define your own templates
    :return:
    """
    return render_template("docs.html")


@api.route('/random', methods=["POST"])
def get_proxy():
    if verify(request.json.get("token")):
        conn = get_conn()
        proxy = conn.random().string()
        json = {"status": "success", "data": proxy}
        user = User.query.filter_by(login_token=verify(request.json.get("token"))).first()
        user.random_analyze += 1
        return jsonify(json)
    return jsonify({"status": "failed", "reason": "Token expired or incorrect."}), 400


@api.route('/all', methods=["POST"])
def get_proxy_all():
    if verify(request.json.get("token")):
        conn = get_conn()
        proxies = conn.all()
        data = []
        if proxies:
            for proxy in proxies:
                data.append(str(proxy))
        json = {"status": "success", "data": data}
        user = User.query.filter_by(login_token=verify(request.json.get("token"))).first()
        user.all_analyze += 1
        return jsonify(json)
    return jsonify({"status": "failed", "reason": "Token expired or incorrect."}), 400


@api.route('/count', methods=["POST"])
def get_count():
    if verify(request.json.get("token")):
        conn = get_conn()
        json = {"status": "success", "data": int(conn.count())}
        user = User.query.filter_by(login_token=verify(request.json.get("token"))).first()
        user.count_analyze += 1
        return jsonify(json)
    return jsonify({"status": "failed", "reason": "Token expired or incorrect."}), 400


@api.route("/token", methods=["POST"])
def get_token():
    name = User.query.filter_by(username=request.json.get("name")).first()
    token = User.query.filter_by(login_token=request.json.get("login_token")).first()
    if name and token:
        expires_in = request.json.get("expires_in", 600)
        return jsonify({"status": "success", "token": jwt.encode(
            {"token": token.login_token, "exp": datetime.datetime.now(tz=datetime.timezone.utc)
                                                + datetime.timedelta(seconds=expires_in)}, app.config["SECRET_KEY"],
            algorithm="HS256")})
    return jsonify({"status": "failed", "reason": "Given username or temporary password is invalid or Server-Side "
                                                  "Error."}), 400


@api.route('/analyze')
@login_required
def analyze():
    return render_template("statistic.html", random_analyze=current_user.random_analyze,
                           all_analyze=current_user.all_analyze,
                           count_analyze=current_user.count_analyze)


@app.route('/register', methods=['GET', 'POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    use_admin = User.query.count() == 0
    msg = ""
    if request.method == 'POST' and username and password:
        user = User.query.filter_by(username=username).first()
        if user:
            msg = '此用户已存在！'
        else:
            new_user = User()
            new_user.username = username
            new_user.set_password(password)
            new_user.permission = use_admin
            new_user.revoke_token()
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            return redirect(url_for('admin'))

    return render_template('register.html', admin_pm=use_admin, msg=msg)


@app.route('/login', methods=['GET', 'POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    msg = ""
    if request.method == 'POST' and username and password:
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect(url_for('admin'))

        msg = '用户名与密码不匹配，请重新输入。'

    return render_template('login.html', msg=msg)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/admin')
@login_required
def admin():
    if current_user.permission == 1:
        return redirect(url_for("manager"))
    if request.method == 'POST':
        if request.form.get('method') == "setpwd":
            password = request.form.get('password')
            load_user(int(id)).set_password(password)
            db.session.commit()
            logout_user()
            return redirect(url_for("index"))
        elif request.form.get('method') == "revtk":
            load_user(int(id)).revoke_token()
            db.session.commit()
            return redirect(url_for("user_info", id=str(id)))
        elif request.form.get('method') == "delusr":
            db.session.delete(load_user(int(id)))
            db.session.commit()
            logout_user()
            return redirect(url_for("index"))
    name = current_user.username
    token = current_user.login_token
    return render_template('admin.html', name=name, token=token)


@app.route('/manager')
@login_required
def manager():
    if current_user.permission == 1:
        return render_template('manager.html', current_user=current_user, users=User.query.all())
    else:
        return abort(403)


@app.route("/info/<id>", methods=["GET", "POST"])
@login_required
def user_info(id):
    if current_user.permission != 1:
        return abort(403)
    if request.form.get('method') and load_user(int(id)):
        if request.form.get('method') == "setpwd":
            password = request.form.get('password')
            load_user(int(id)).set_password(password)
            db.session.commit()
            return redirect(url_for("user_info", id=str(id)))
        elif request.form.get('method') == "revtk":
            load_user(int(id)).revoke_token()
            db.session.commit()
            return redirect(url_for("user_info", id=str(id)))
        elif request.form.get('method') == "delusr":
            db.session.delete(load_user(int(id)))
            db.session.commit()
            return redirect(url_for("manager"))
    return render_template('info.html', user=load_user(id))


@app.route("/new-usr", methods=["POST"])
@login_required
def new_user():
    if current_user.permission != 1:
        return abort(403)
    username = request.form.get('enter_usrname')
    password = request.form.get('password')
    permission = int(request.form.get('EnableAdminPermission', False) == True)
    if username and password:
        user = User()
        user.username = username
        user.permission = permission
        user.set_password(password)
        user.revoke_token()
        db.session.add(user)
        db.session.commit()
    return redirect(url_for('manager'))


app.register_blueprint(api, url_prefix="/api")

if __name__ == '__main__':
    app.run(host=API_HOST, port=API_PORT, threaded=API_THREADED)
