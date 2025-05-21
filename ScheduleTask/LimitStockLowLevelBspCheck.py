import json
import time
from datetime import datetime

from Chan import CChan
from ChanConfig import CChanConfig
from Common import constants
from Common.CEnum import AUTYPE, BSP_TYPE, DATA_SRC, FX_TYPE, KL_TYPE
from Common.message import build_bsp_message, send_bark_notification
from Common.redis_util import RedisClient

redis_client = RedisClient().get_client()

schedule_config = json.loads(redis_client.get(constants.REDIS_KEY_SCHEDULE_CONFIG))
stock_dict = json.loads(redis_client.get(constants.REDIS_KEY_STOCK_TO_NAME))
# print(f"get sh601360 name: {stock_dict.get('sh.601360')}")
etf_dict = json.loads(redis_client.get(constants.REDIS_KEY_ETF_TO_NAME))
stock_dict.update(etf_dict)


data_src = DATA_SRC.SINA
origin_stock_list = schedule_config["limit_stock_list"]
stock_list = origin_stock_list if data_src == DATA_SRC.SINA else [
    code.replace("sz", "sz.").replace("sh", "sh.") for code in origin_stock_list
]
print(stock_list)
lv_list = [KL_TYPE[kl_type] for kl_type in schedule_config["limit_stock_low_level_list"]]

begin_time = schedule_config["limit_stock_low_level_begin"]
end_time = schedule_config["limit_stock_low_level_end"]
config = CChanConfig({
        "bi_algo": "advanced",
        "bi_strict": False,
        "trigger_step": True,
        "skip_step": 0,
        "divergence_rate": 0.8,
        "bsp2_follow_1": False,
        "bsp3_follow_1": False,
        "min_zs_cnt": 0,
        "bs1_peak": False,
        "macd_algo": "peak",
        "bs_type": '1,2,3a,1p,2s,3b',
        "print_warning": True,
        "zs_algo": "normal",
        "zs_combine": False,
    })


code_to_lv_to_time_dict = {}


def build_chan_object(code):
    return CChan(
        code=code,
        begin_time=begin_time,
        end_time=end_time,
        data_src=data_src,
        lv_list=lv_list,
        config=config,
        autype=AUTYPE.QFQ,
    )


def try_send_message(stock_code, lv_index, bsp):
    stock_code = stock_code if data_src is DATA_SRC.BAO_STOCK else stock_code.replace("sz", "sz.").replace("sh", "sh.")
    ctime_obj = bsp.klu.time
    bsp_time = datetime(ctime_obj.year, ctime_obj.month, ctime_obj.day, ctime_obj.hour, ctime_obj.minute)
    if bsp_time.date() != datetime.now().date():
        return
    lv = lv_list[lv_index]
    sent_time = code_to_lv_to_time_dict.get(stock_code, {}).get(lv)
    if sent_time and sent_time >= bsp_time:
        print(f"message already sent: {stock_code}, {lv_index}, {bsp_time}")
        return

    code_suffix = stock_code[-6:]  # 提取后6位数字
    # 生成两种可能的股票代码格式
    possible_codes = [f"sh.{code_suffix}", f"sh{code_suffix}", f"sz.{code_suffix}", f"sz{code_suffix}"]
    # 查找第一个存在的股票代码
    stock_name = next((stock_dict[code] for code in possible_codes if code in stock_dict), "未知股票")
    title, msg = build_bsp_message(
        code=stock_code,
        stock_name=stock_name,  # 如果需要股票名称需要额外参数
        lv=lv_list[lv_index].name.replace("K_", "").replace("_", ""),
        bsp_type=bsp.type2str(),
        is_buy=bsp.is_buy,
        price=bsp.klu.close,
        time=bsp_time.strftime("%Y-%m-%d %H:%M")
    )
    send_bark_notification(msg, title)
    print(f"send message to bark app, title:{title}, message:{msg}")

    # 更新发送记录
    if stock_code not in code_to_lv_to_time_dict:
        code_to_lv_to_time_dict[stock_code] = {}
    code_to_lv_to_time_dict[stock_code][lv] = bsp_time


def limit_stock_low_level_bsp_check_main():
    for stock_code in stock_list:
        chan = build_chan_object(stock_code)
        last_recorded_bsp_list = [None for _ in range(0, len(lv_list))]
        for chan_snapshot in chan.step_load():
            for lv_index in range(0, len(lv_list)):
                bsp_list = chan_snapshot.get_bsp(lv_index)  # 获取买卖点列表
                if not bsp_list:  # 为空
                    continue
                last_bsp = bsp_list[-1]  # 最后一个买卖点
                cur_lv_chan = chan_snapshot[lv_index]
                if last_bsp.klu.klc.idx != cur_lv_chan[-2].idx:
                    continue
                if (cur_lv_chan[-2].fx == FX_TYPE.BOTTOM and last_bsp.is_buy) or (cur_lv_chan[-2].fx == FX_TYPE.TOP and not last_bsp.is_buy):
                    last_recorded_bsp_list[lv_index] = last_bsp
                    print(f'bsp: {cur_lv_chan[lv_index][-1].time}, is buy: {last_bsp.is_buy}, lv: {lv_index}')
        for lv_index in range(0, len(lv_list)):
            last_bsp = last_recorded_bsp_list[lv_index]
            if last_bsp:
                print(f"stock: {stock_code}, "
                      f"last_recorded_bsp: {last_bsp.klu.time}, "
                      f"is buy: {last_bsp.is_buy}, "
                      f"type: {last_bsp.type}, lv: {lv_index}")
                try_send_message(stock_code, lv_index, last_bsp)


if __name__ == "__main__":
    while True:
        limit_stock_low_level_bsp_check_main()
        time.sleep(60)
