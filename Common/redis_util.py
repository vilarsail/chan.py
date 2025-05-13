# redis_client.py
import redis
from threading import Lock


class RedisClient:
    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        # 双重锁检查，确保线程安全的单例
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(RedisClient, cls).__new__(cls)
                    cls._instance._init_connection(*args, **kwargs)
        return cls._instance

    def _init_connection(self, host='localhost', port=6379, db=0, password=None):
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True  # 推荐用于处理字符串
        )

    def get_client(self):
        return self.client
