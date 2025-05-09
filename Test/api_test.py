import unittest
import json
from unittest.mock import patch
from datetime import datetime

# 添加项目根目录到Python路径
import sys
import os 
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from DataAPI.SinaAPI import SinaAPI, KL_TYPE

class TestSinaAPI(unittest.TestCase):
    
    @patch('DataAPI.SinaAPI.requests.get')
    def test_kday_data(self, mock_get):
        # 模拟API响应
        mock_response = {
            "text": json.dumps([
                {"day":"2023-08-01","open":"10.5","high":"11.2","low":"10.3","close":"10.8","volume":"100000"},
                {"day":"2023-08-02","open":"10.8","high":"11.5","low":"10.6","close":"11.3","volume":"120000"}
            ])
        }
        mock_get.return_value = type('obj', (object,), mock_response)
        
        # 测试用例
        api = SinaAPI(code="sh600000", k_type=KL_TYPE.K_DAY, begin_date="2023-08-01")
        data_generator = api.get_kl_data()
        
        # 验证数据转换
        first_item = next(data_generator)
        self.assertEqual(first_item["datetime"], datetime(2023,8,1))
        self.assertEqual(first_item["close"], 10.8)
        
    @patch('DataAPI.SinaAPI.requests.get')    
    def test_minute_data(self, mock_get):
        # 模拟分钟数据响应
        mock_response = {
            "text": json.dumps([
                {"day":"2023-08-01 10:30:00","open":"10.5","high":"10.8","low":"10.4","close":"10.6","volume":"50000"}
            ])
        }
        mock_get.return_value = type('obj', (object,), mock_response)
        
        api = SinaAPI(code="sh600000", k_type=KL_TYPE.K_30M)
        data = list(api.get_kl_data())
        print(data)
        
        # 验证分钟数据转换
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["datetime"].minute, 30)


if __name__ == '__main__':
    unittest.main()