import sys
# import flask_profiler
from flask import Flask

# import setting
from app.urls import register_urlpatterns

# Init the Flask application
app = Flask(__name__)

# Config
app.config['JSON_AS_ASCII'] = False
# app.debug = setting.DEBUG_MODE
# app.config["flask_profiler"] = {
#     "enabled": setting.PROFILER_ENABLED,
#     "storage": {
#         "engine": "sqlite"
#     },
#     "basicAuth": {
#         "enabled": True,
#         "username": "admin",
#         "password": "admin"
#     },
#     "ignore": [
#             "^/static/.*"
#         ]
# }

# flask_profiler.init_app(app)

# Init the global logger
# logger.init()
# Init routers and handlers
register_urlpatterns(app)


@app.route('/')
def index(): # Used for local test
    return 'Hello, this is Leo!'


if __name__ == '__main__':
    # logging.info('Run app in ' + settings.APP_MODE + ' mode')
    port = int(sys.argv[1]) if len(sys.argv) > 1 else "8080"
    app.run(host="0.0.0.0", port=port)
