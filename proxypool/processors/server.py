from flask import Flask, g, render_template, Blueprint, redirect
from proxypool.storages.redis import RedisClient
from proxypool.setting import API_HOST, API_PORT, API_THREADED, IS_DEV


__all__ = ['app']

app = Flask(__name__)
api = Blueprint("api", __name__)
if IS_DEV:
    app.debug = True


def get_conn():
    """
    get redis client object
    :return:
    """
    if not hasattr(g, 'redis'):
        g.redis = RedisClient()
    return g.redis


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


@api.route('/random')
def get_proxy():
    """获取随机可用代理
    @@@
    ### 返回值
    返回类型：str
    
    返回实例：
    ```
    1.1.1.1:80
    ```
    Python 代码（使用requests）：
    ```python
    import requests
    response = requests.get("YOUR_SERVER_URL/api/random")
    print(response)
    ```
    Curl 代码：
    ```shell
    curl YOUR_SERVER_URL/api/random
    ```
    @@@
    """
    conn = get_conn()
    return conn.random().string()


@api.route('/all')
def get_proxy_all():
    """获取所有可用代理（按质量排序）
    @@@
    ### 返回值
    返回类型：str
    
    返回实例：
    ```
    1.1.1.1:234
    2.2.2.2:345
    3.3.3.3:456
    4.4.4.4:5678
    5.5.5.5:65532
    ......
    ```
    Python 代码（使用requests）：
    ```python
    import requests
    response = requests.get("YOUR_SERVER_URL/api/all")
    print(response)
    ```
    Curl 代码：
    ```shell
    curl YOUR_SERVER_URL/api/all
    ```
    @@@
    """
    conn = get_conn()
    proxies = conn.all()
    proxies_string = ''
    if proxies:
        for proxy in proxies:
            proxies_string += str(proxy) + '\n'

    return proxies_string


@api.route('/count')
def get_count():
    """获取可用代理的总量
    @@@
    ### 返回值
    返回类型：int
    
    返回实例：
    ```
    5024
    ```
    Python 代码（使用requests）：
    ```python
    import requests
    response = requests.get("YOUR_SERVER_URL/api/count")
    print(response)
    ```
    Curl 代码：
    ```shell
    curl YOUR_SERVER_URL/api/count
    ```
    @@@
    """
    conn = get_conn()
    return str(conn.count())

app.register_blueprint(api, url_prefix="/api")

if __name__ == '__main__':
    app.run(host=API_HOST, port=API_PORT, threaded=API_THREADED)
