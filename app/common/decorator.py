import json
import threading
import logging
import traceback
import time

import app.common.constants as constants

from app.common.excepts import InternalError


logger = logging.getLogger(__name__)

def synchronized(func):
    """
    函数线程安全装饰器
    :param func:
    :return: synced_func
    """
    func.__lock__ = threading.Lock()

    def synced_func(*args, **kws):
        with func.__lock__:
            return func(*args, **kws)

    return synced_func


def singleton(class_):
    """
    线程安全的单实例装饰器
    :param class_:
    :return: instance
    """
    instances = {}

    @synchronized
    def get_instance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return get_instance


def http_post(func):
    """
    http post请求的装饰器，包含了错误处理，结果组装
    :param func:
    :return: http response
    """
    def wrapper():
        try:
            result = func()
            if isinstance(result, dict) or isinstance(result, list):
                response = {constants.HTTP_RESPONSE_ERROR_CODE: constants.ErrorCode.OK[0], constants.HTTP_RESPONSE_DATA: result}
            elif result:
                response = {constants.HTTP_RESPONSE_ERROR_CODE: constants.ErrorCode.OK[0]}
            else:
                response = {constants.HTTP_RESPONSE_ERROR_CODE: constants.ErrorCode.OPERATION_ERROR[0],
                            constants.HTTP_RESPONSE_ERROR_MSG: constants.ErrorCode.OPERATION_ERROR[1]}
        except InternalError as e:
            response = {constants.HTTP_RESPONSE_ERROR_CODE: e.code,
                        constants.HTTP_RESPONSE_ERROR_MSG: e.message}
        except ValueError:
            response = {constants.HTTP_RESPONSE_ERROR_CODE: constants.ErrorCode.PARAM_ERROR[0],
                        constants.HTTP_RESPONSE_ERROR_MSG: constants.ErrorCode.PARAM_ERROR[1]}
        except Exception as e:
            logger.error("http except unknown error, trace {}".format(traceback.format_exc()))
            response = {constants.HTTP_RESPONSE_ERROR_CODE: constants.ErrorCode.UNKNOWN_ERROR[0],
                        constants.HTTP_RESPONSE_ERROR_MSG: constants.ErrorCode.UNKNOWN_ERROR[1]}
        return json.dumps(response)
    wrapper.__name__ = func.__name__
    return wrapper


def http_get(func):
    """
    http post请求的装饰器，包含了错误处理，结果组装
    :param func:
    :return: http response
    """
    def wrapper():
        try:
            result = func()
            if isinstance(result, dict) or isinstance(result, list):
                response = {constants.HTTP_RESPONSE_ERROR_CODE: constants.ErrorCode.OK[0], constants.HTTP_RESPONSE_DATA: result}
            elif result:
                response = {constants.HTTP_RESPONSE_ERROR_CODE: constants.ErrorCode.OK[0]}
            else:
                response = {constants.HTTP_RESPONSE_ERROR_CODE: constants.ErrorCode.OPERATION_ERROR[0],
                            constants.HTTP_RESPONSE_ERROR_MSG: constants.ErrorCode.OPERATION_ERROR[1]}
        except InternalError as e:
            response = {constants.HTTP_RESPONSE_ERROR_CODE: e.code,
                        constants.HTTP_RESPONSE_ERROR_MSG: e.message}
        except ValueError:
            response = {constants.HTTP_RESPONSE_ERROR_CODE: constants.ErrorCode.PARAM_ERROR[0],
                        constants.HTTP_RESPONSE_ERROR_MSG: constants.ErrorCode.PARAM_ERROR[1]}
        except Exception as e:
            logger.error("http except unknown error, trace {}".format(traceback.format_exc()))
            response = {constants.HTTP_RESPONSE_ERROR_CODE: constants.ErrorCode.UNKNOWN_ERROR[0],
                        constants.HTTP_RESPONSE_ERROR_MSG: constants.ErrorCode.UNKNOWN_ERROR[1]}
        return json.dumps(response)
    wrapper.__name__ = func.__name__
    return wrapper


def run_time_recoder(func):
    """
    记录函数运行时间，打点到metric
    :param func:
    :return:
    """
    def wrapper(*args, **kwargs):
        begin_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = (end_time - begin_time) * 1000
        logger.info("function {} run time: {}ms".format(func.__name__, int(duration)))
        timer = 'ies.recommend.leo.duration.{}.timer'.format(func.__name__)
        '''
        metrics.emit_timer(timer, int(duration))
        metrics.flush()
        '''
        return result
    wrapper.__name__ = func.__name__
    return wrapper
