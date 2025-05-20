import json

from Common.redis_util import RedisClient


class FileOperator:
    def __init__(self):
        self.redis_client = RedisClient().get_client()

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
            schedule_config = self.load_schedule_config()
            self.redis_client.set("schedule_config", json.dumps(schedule_config))

            # 加载股票代码映射
            stock_dict = self.load_stock_code_to_name_dict()
            self.redis_client.set("stock_code_to_name", json.dumps(stock_dict))

            # 加载ETF代码映射
            etf_dict = self.load_eft_code_to_name_dict()
            self.redis_client.set("etf_code_to_name", json.dumps(etf_dict))

            etf_dict = self.load_eft_code_to_name_100_dict()
            self.redis_client.set("etf_code_to_name_100", json.dumps(etf_dict))

            print("配置文件已成功加载到Redis")
        except Exception as e:
            print(f"配置文件加载Redis失败: {str(e)}")
            raise

