class InternalError(Exception):

    def __init__(self, code, message):
        self.code = code
        self.message = message
        self.details = {}
