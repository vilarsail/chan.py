import json

from flask import request
from app.common.decorator import http_post,http_get


@http_get
def hello():
    result = {'hello': request.method}
    return result
