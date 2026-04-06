"""项目内异常类型。"""


class ICostPortError(Exception):
    """可预期的业务/配置错误基类。"""


class ConfigError(ICostPortError):
    """配置文件缺失、格式错误或校验失败。"""


class ParserNotFoundError(ICostPortError):
    """无法根据扩展名或特征选择解析器。"""


class CategoryValidationError(ICostPortError):
    """分类结果不在 categories 白名单内。"""
