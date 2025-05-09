import json
from flask import request, send_file
from app.common.decorator import http_post,http_get
from app.service.picture_service import generate_stock_image



@http_get
def hello():
    result = {'hello': request.method}
    return result


def generate_image():
    params = request.get_json()
    print(params)
    required_params = ['stock_code', 'begin_time', 'end_time', 'lv_list']

    if not all(param in params for param in required_params):
        return {'error': 'Missing required parameters'}, 400

    try:
        image_path = generate_stock_image(
            stock_code=params['stock_code'],
            begin_time=params['begin_time'],
            end_time=params['end_time'],
            lv_list=params['lv_list']
        )
        return send_file(image_path, mimetype='image/png')
    except Exception as e:
        return {'error': str(e)}, 500