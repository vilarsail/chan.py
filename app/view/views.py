import json
from flask import request, send_file
from app.common.decorator import http_post,http_get
from app.service.picture_service import generate_stock_image
from Common.redis_util import RedisClient
from Common import constants



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


def get_recent_bsp():
    source = request.args.get('source')
    if not source:
        return json.dumps({'error': 'Missing source parameter'}), 400
    redis_key = ""
    if source == 'stock':
        redis_key = constants.REDIS_KEY_STOCK_BSP_RECORDS
    elif source == 'etf':
        redis_key = constants.REDIS_KEY_ETF_BSP_RECORDS
    else:
        return json.dumps({'error': 'Invalid source value'}), 400
    redis_client = RedisClient().get_client()
    data = redis_client.get(redis_key)
    return data if data else json.dumps({}), 200


def get_all_code_to_name_dict():
    source = request.args.get('source')
    if not source:
        return json.dumps({'error': 'Missing source parameter'}), 400

    redis_key = ""
    if source == 'stock':
        redis_key = constants.REDIS_KEY_STOCK_TO_NAME
    elif source == 'etf':
        redis_key = constants.REDIS_KEY_ETF_TO_NAME
    else:
        return json.dumps({'error': 'Invalid source value'}), 400

    redis_client = RedisClient().get_client()
    data = redis_client.get(redis_key)
    return data if data else json.dumps({}), 200