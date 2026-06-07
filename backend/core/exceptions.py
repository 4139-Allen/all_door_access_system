"""全局异常(自定义)"""


class NotFoundError(Exception):
    """资源不存在"""
    pass

class AuthError(Exception):
    """认证失败"""
    pass

class TooManyRequestsError(Exception):
    """请求频率过高"""
    pass