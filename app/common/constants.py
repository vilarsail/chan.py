
class HttpStatusCode(object):
    ok = 200
    bad_request = 400
    not_found = 404
    method_not_allowed = 405
    internal_server_error = 500


class ErrorCode(object):
    OK = 0, 'success'
    INTERNAL_ERROR = 10001, 'internal excepts'
    PARAM_ERROR = 10008, 'param excepts'
    TIME_OUT = 10010, 'time out'
    METHOD_ERROR = 10021, 'http method unsupported'
    OPERATION_ERROR = 20706, 'operation failed'
    UNKNOWN_ERROR = 60001, 'unknown excepts'


HTTP_RESPONSE_ERROR_CODE = 'code'
HTTP_RESPONSE_ERROR_MSG = 'message'
HTTP_RESPONSE_DATA = 'data'
