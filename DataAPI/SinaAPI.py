import json
import requests
from datetime import datetime

from Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from Common.func_util import kltype_lt_day, str2float
from KLine.KLine_Unit import CKLine_Unit
from .CommonStockAPI import CCommonStockApi


SINA_KLINE_DATA_URL = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
SINA_REALTIME_DATA_URL = "https://hq.sinajs.cn/list="
DEFAULT_HEADERS = {
    "Referer": "https://finance.sina.com.cn/",
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.137 '
                  'Safari/537.36 LBBROWSER ',
}
# 1min数据无法获取
# 5min可以获取4-5个月数据，
# 15min可以获取1.2-1.3年数据，
# 30min可以获取2.5年的数据，
# 日线可以获取10年的数据，
MAX_DEFULT_LENGTH = 10000 


class SinaAPI(CCommonStockApi):

    def __init__(self, code, k_type=KL_TYPE.K_DAY, begin_date=None, end_date=None, autype=AUTYPE.QFQ):
        super(SinaAPI, self).__init__(code, k_type, begin_date, end_date, autype)     

    def get_kl_data(self):
        params = {
            "symbol": self.code,
            "scale": self.__convert_type(),
            "ma": "no",
            "datalen": MAX_DEFULT_LENGTH
        }
        result = requests.get(url=SINA_KLINE_DATA_URL, params=params, headers=DEFAULT_HEADERS)
        raw_data = json.loads(result.text)
        
        for item in raw_data:
            # 处理不同时间格式的日期
            dt_str = item["day"].split()[0]  # 去除分钟数据的时间部分
            if self.begin_date and dt_str < self.begin_date:
                continue
            if self.end_date and dt_str > self.end_date:
                continue
            # 统一时间格式为datetime
            if " " in item["day"]:  # 分钟数据
                dt = datetime.strptime(item["day"], "%Y-%m-%d %H:%M:%S")
                ctime = CTime(dt.year, dt.month, dt.day, dt.hour, dt.minute)
            else:  # 日线及以上
                dt = datetime.strptime(item["day"], "%Y-%m-%d")
                ctime = CTime(dt.year, dt.month, dt.day, 0, 0)
            yield CKLine_Unit({
                DATA_FIELD.FIELD_TIME: ctime,
                DATA_FIELD.FIELD_OPEN: float(item["open"]),
                DATA_FIELD.FIELD_HIGH: float(item["high"]),
                DATA_FIELD.FIELD_LOW: float(item["low"]),
                DATA_FIELD.FIELD_CLOSE: float(item["close"]),
                DATA_FIELD.FIELD_VOLUME: int(item["volume"])
            })

    def get_realtime_data(self):
        realtime_url = f'{SINA_REALTIME_DATA_URL}{self.code}'
        realtime_response = requests.get(realtime_url, headers=DEFAULT_HEADERS)
        realtime_response.encoding = 'gbk'
        realtime_data = realtime_response.text.split('="')[1].strip('";').split(',')
        
        realtime_time = datetime.strptime(f"{realtime_data[30]} {realtime_data[31]}", "%Y-%m-%d %H:%M:%S")
        return {
            "day": realtime_time.strftime("%Y-%m-%d %H:%M:%S"),
            "open": float(realtime_data[1]),
            "high": float(realtime_data[4]),
            "low": float(realtime_data[5]),
            "close": float(realtime_data[3]),
            "volume": int(realtime_data[8])
        }

    # 当前逻辑：尝试用实时数据添加一根新K线
    # 另一个思路：直接修改最后一根K线的close，其他数据不变
    def try_add_real_time_data(self, raw_data, realtime_data):
        if not realtime_data:
            return raw_data
        realtime_time = datetime.strptime(realtime_data["day"], "%Y-%m-%d %H:%M:%S")
        if self.k_type == KL_TYPE.K_DAY:
            # 日线级别：检查日期是否已存在
            last_day = raw_data[-1]["day"].split()[0] if raw_data else None
            if last_day and last_day == realtime_time.strftime("%Y-%m-%d"):
                return raw_data
            formatted_data = {
                "day": realtime_time.strftime("%Y-%m-%d"),
                "open": realtime_data["open"],
                "high": realtime_data["high"],
                "low": realtime_data["low"],
                "close": realtime_data["close"],
                "volume": realtime_data["volume"]
            }
        if self.k_type == KL_TYPE.K_60M or self.k_type == KL_TYPE.K_30M or self.k_type == KL_TYPE.K_15M or self.k_type == KL_TYPE.K_5M:
            # 日线级别以下，开盘价用上一根K线的收盘价，收盘价用实时收盘价，high取两者大的，low取两者小的，成交量取上一根K线成交量
            formatted_data = {
                "day": realtime_time.strftime("%Y-%m-%d %H:%M:%S"),
                "open": raw_data[-1]["close"],
                "high": max(raw_data[-1]["close"], realtime_data["close"]),
                "low": min(raw_data[-1]["close"], realtime_data["close"]),
                "close": realtime_data["close"],
                "volume": raw_data[-1]["volume"]
            }
        return raw_data + [formatted_data]




    def __convert_type(self):
        _dict = {
            KL_TYPE.K_1M: 1,
            KL_TYPE.K_5M: 5,
            KL_TYPE.K_15M: 15,
            KL_TYPE.K_30M: 30,
            KL_TYPE.K_60M: 60,
            KL_TYPE.K_DAY: 240,  # 日线对应240分钟
            KL_TYPE.K_WEEK: 1200,  # 周线（假设5个交易日）
            KL_TYPE.K_MON: 7200,   # 月线（假设30个交易日）
        }
        return _dict[self.k_type]


if __name__ == '__main__':
    api = SinaAPI(code="sh600000", begin_date="2023-01-01")
    for kline in api.get_kl_data():
        print(kline)