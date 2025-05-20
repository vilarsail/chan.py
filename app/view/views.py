import json
from datetime import datetime, timedelta

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
    if source == 'stock':
        data = json.dumps(filter_dict(json.loads(data)))
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


def filter_dict(data):
    # 获取当前时间（基于香港时间 2025-05-17 10:00:00）
    current_time = datetime(2025, 5, 17, 10, 0, 0)
    # 计算7天前的截止时间
    cutoff_time = current_time - timedelta(days=7)

    # 创建过滤后的结果字典
    filtered_data = {
        "update_time": data["update_time"],
        "level": {}
    }

    # 遍历 level 中的所有子键（K_DAY, K_60M, K_30M 等）
    for level_key, level_data in data["level"].items():
        filtered_level_data = {}
        # 遍历每个 level_key 下的符号数据
        for symbol, info in level_data.items():
            # 检查 is_buy 是否为 True
            if info.get("is_buy", False):
                # 将 time 字符串转换为 datetime 对象
                item_time = datetime.strptime(info["time"], "%Y-%m-%d %H:%M:%S")
                # 检查 time 是否在7天以内
                if item_time >= cutoff_time:
                    filtered_level_data[symbol] = info
        # 只有当 filtered_level_data 不为空时才添加到结果
        if filtered_level_data:
            filtered_data["level"][level_key] = filtered_level_data

    return filtered_data