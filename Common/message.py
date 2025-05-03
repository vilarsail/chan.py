import requests
from urllib.parse import quote

def send_bark_notification(
    device_key: str,
    message: str,
    title: str = "股票买卖点提醒",
    sound: str = "bell.caf",
    group: str = "stock_trading",
    icon: str = "https://example.com/stock.png",
    level: str = "active"
) -> dict:
    """
    发送 Bark 通知到手机
    :param device_key: Bark 设备唯一标识（从 App 获取）
    :param message: 通知内容（支持 Markdown）
    :param title: 通知标题（可选）
    :param sound: 提示音类型（可选，如 "bell.caf", "birdsong.caf"）
    :param group: 通知分组（可选）
    :param icon: 通知图标 URL（可选）
    :param level: 通知级别（可选，"active"=主动提醒, "timeSensitive"=时效性, "passive"=静默）
    :return: Bark 服务器响应
    """
    base_url = f"https://api.day.app/{device_key}"
    
    # 编码参数（处理特殊字符）
    encoded_message = quote(message)
    encoded_title = quote(title)
    
    # 构建完整 URL（支持所有 Bark 参数）
    url = (
        f"{base_url}/{encoded_title}/{encoded_message}?"
        f"sound={sound}&"
        f"group={group}&"
        f"icon={icon}&"
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
    # 模拟买卖点触发
    current_price = 15.34
    trigger_type = "买入"  # 或 "卖出"
    
    # 构建通知内容
    notification_msg = (
        f"🚨 **{trigger_type}信号触发**\n"
        f"- 股票代码: AAPL\n"
        f"- 当前价格: ${current_price}\n"
        f"- 时间: 2023-10-01 14:30:00"
    )
    
    # 发送通知（参数可自定义）
    result = send_bark_notification(
        device_key="YOUR_DEVICE_KEY",  # 替换为你的设备 Key
        message=notification_msg,
        title="📈 交易提醒",
        sound="cashregister.caf",  # 使用收银机音效
        icon="https://img.icons8.com/ios/452/stock-share.png"
    )
    
    print("推送结果:", result)