
from flask import Flask
from flask_cors import CORS

from app.urls import register_urlpatterns

# Init the Flask application
app = Flask(__name__)
CORS(app)

# Config
app.config['JSON_AS_ASCII'] = False
app.secret_key = 'your_secret_key_config'

# Init the global logger
# logger.init()
# Init routers and handlers
register_urlpatterns(app)


@app.route('/')
def index(): # Used for local test
    return 'Hello, this is Leo!'


if __name__ == '__main__':
    # logging.info('Run app in ' + settings.APP_MODE + ' mode')
    app.run("0.0.0.0", port=8080)
