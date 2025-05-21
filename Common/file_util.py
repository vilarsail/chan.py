import json

from Common.redis_util import RedisClient
from app.common.decorator import singleton


@singleton
class FileOperator:
    def __init__(self):
        self.redis_client = RedisClient().get_client()
        self.schedule_config = None
        self.stock_dict = None
        self.etf_dict = None
        self.etf_dict_100 = None
        self.load_init_files_to_redis()
        self.all_name_to_code_dict = {}
        self.all_name_to_code_dict.update(self.stock_dict)
        self.all_name_to_code_dict.update(self.etf_dict)

    @classmethod
    def load_schedule_config(cls):
        with open("./ScheduleTask/config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            return config

    @classmethod
    def load_stock_code_to_name_dict(cls):
        with open("./Source/stock_code_to_name.json", "r", encoding="utf-8") as f:
            stock_dict = json.load(f)
            return stock_dict

    @classmethod
    def load_eft_code_to_name_dict(cls):
        with open("./Source/etf_code_to_name.json", "r", encoding="utf-8") as f:
            etf_dict = json.load(f)
            return etf_dict

    @classmethod
    def load_eft_code_to_name_100_dict(cls):
        with open("./Source/etf_code_to_name_100.json", "r", encoding="utf-8") as f:
            etf_dict = json.load(f)
            return etf_dict

    def load_init_files_to_redis(self):
        """将配置文件加载到Redis"""
        try:
            # 加载定时任务配置
            self.schedule_config = self.load_schedule_config()
            self.redis_client.set("self.schedule_config", json.dumps(self.schedule_config))

            # 加载股票代码映射
            self.stock_dict = self.load_stock_code_to_name_dict()
            self.redis_client.set("stock_code_to_name", json.dumps(self.stock_dict))

            # 加载ETF代码映射
            self.etf_dict = self.load_eft_code_to_name_dict()
            self.redis_client.set("etf_code_to_name", json.dumps(self.etf_dict))

            self.etf_dict_100 = self.load_eft_code_to_name_100_dict()
            self.redis_client.set("etf_code_to_name_100", json.dumps(self.etf_dict_100))

            print("配置文件已成功加载到Redis")
        except Exception as e:
            print(f"配置文件加载Redis失败: {str(e)}")
            raise

    def get_name_by_code(self, code):
        code_suffix = code[-6:]  # 提取后6位数字
        # 生成可能的股票代码格式
        possible_codes = [
            f"sh.{code_suffix}", f"sh{code_suffix}",
            f"sz.{code_suffix}", f"sz{code_suffix}"
        ]
        # 查找第一个存在的股票代码
        return next((self.all_name_to_code_dict[code] for code in possible_codes if code in self.all_name_to_code_dict), "未知股票")

if __name__ == '__main__':
    fp = FileOperator()
    print(f"{fp.get_name_by_code("sz000799")}")
