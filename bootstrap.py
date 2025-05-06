import sys
from flask import Flask

from app.urls import register_urlpatterns

# Init the Flask application
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

register_urlpatterns(app)


@app.route('/')
def index():
    return 'Hello, this is Leo!'


if __name__ == '__main__':
    # logging.info('Run app in ' + settings.APP_MODE + ' mode')
    port = int(sys.argv[1]) if len(sys.argv) > 1 else "8080"
    app.run(host="0.0.0.0", port=port)
