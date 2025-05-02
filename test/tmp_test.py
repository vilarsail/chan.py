import requests
from urllib.parse import quote

def get_realtime_data(symbol):
    url = f'https://hq.sinajs.cn/list={quote(symbol)}'
    
    headers = {
        "Referer": "https://finance.sina.com.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = 'gbk'  # 关键：处理中文编码
        
        if response.status_code != 200:
            return None
            
        data_str = response.text
        # 解析数据格式：var hq_str_sh601006="大秦铁路, 7.45, 7.45,...";
        data = data_str.split('="')[1].strip('";').split(',')
        
        return {
            'name': data[0].strip(),
            'open': float(data[1]),
            'prev_close': float(data[2]),
            'price': float(data[3]),
            'high': float(data[4]),
            'low': float(data[5]),
            'volume': int(data[8]),  # 成交量（手）
            'time': f"{data[30]} {data[31]}"
        }
        
    except Exception as e:
        print(f"请求失败: {str(e)}")
        return None


# 使用示例
if __name__ == '__main__':
    data = get_realtime_data('sh601006')
    print(data)