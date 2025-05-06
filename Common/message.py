import os
import requests
from urllib.parse import quote


device_key_file_url = '~/.config/bark.key'


def build_bsp_message(code, stock_name, lv, bsp_type, is_buy, price, time):
    buy_message = "买入" if is_buy else "卖出"
    title = f"📈 {code}{stock_name}交易提醒"
    message = (
        f"🚨 {lv}级别{bsp_type}{buy_message}交易点形成\n"
        f"- 当前价格: {price}\n"
        f"- 当前时间: {time}\n"
    )
    return title, message


def read_device_key():
    expanded_path = os.path.expanduser(device_key_file_url)
    if not os.path.exists(expanded_path):
        raise FileNotFoundError(f"Key file not found at {expanded_path}")
    with open(expanded_path, 'r', encoding='utf-8') as key_file:
        return key_file.read()


def send_bark_notification(
    message: str,
    title: str = "股票买卖点提醒",
    level: str = "active"
) -> dict:
    """
    发送 Bark 通知到手机
    :param device_key: Bark 设备唯一标识（从 App 获取）
    :param message: 通知内容（支持 Markdown）
    :param title: 通知标题（可选）
    :param level: 通知级别（可选，"active"=主动提醒, "timeSensitive"=时效性, "passive"=静默）
    :return: Bark 服务器响应
    """
    device_key = read_device_key()
    base_url = f"https://api.day.app/{device_key}"
    
    # 编码参数（处理特殊字符）
    encoded_message = quote(message)
    encoded_title = quote(title)
    
    # 构建完整 URL（支持所有 Bark 参数）
    url = (
        f"{base_url}/{encoded_title}/{encoded_message}?"
        f"level={level}"
    )
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # 检查 HTTP 错误
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"推送失败: {e}")
        return {"status": "error", "reason": str(e)}

# 示例用法（替换 YOUR_DEVICE_KEY）
if __name__ == "__main__":
    code = "AAPL"
    stock_name = "苹果公司"
    lv = "日线"
    bsp_type = "一类买点"
    is_buy = True
    price = 150.23
    from datetime import datetime

    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # 读取设备密钥
        device_key = read_device_key()

        # 构建消息
        title, message = build_bsp_message(code, stock_name, lv, bsp_type, is_buy, price, time)

        # 发送通知
        result = send_bark_notification(message, title)

        print("推送结果:", result)
    except FileNotFoundError as e:
        print(f"错误: {e}")
    except Exception as e:
        print(f"发生未知错误: {e}")