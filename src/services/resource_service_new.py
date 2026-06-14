"""资源服务（含种子数据）。"""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.models.resource import GeneratedResource, PlatformResource
from src.services.dify_service import dify_service


class ResourceNotFound(Exception):
    pass


