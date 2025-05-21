import json
import time
import traceback
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
etf_dict = json.loads(redis_client.get(constants.REDIS_KEY_ETF_TO_NAME_100))

data_src = DATA_SRC.SINA

origin_stock_list = stock_dict.keys()
stock_list = origin_stock_list if data_src == DATA_SRC.BAO_STOCK else [
    code.replace("sz.", "sz").replace("sh.", "sh") for code in origin_stock_list
]
print(f"full stock_list: {stock_list}")


origin_etf_list = etf_dict.keys()
etf_list = origin_etf_list if data_src == DATA_SRC.SINA else [
    code.replace("sz", "sz.").replace("sh", "sh.") for code in origin_etf_list
]
lv_list = [KL_TYPE[kl_type] for kl_type in schedule_config["full_stock_high_level_list"]]
print(f"full etf list: {etf_list}")

begin_time = schedule_config["full_stock_high_level_begin"]
end_time = schedule_config["full_stock_high_level_end"]
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


def full_stock_high_level_bsp_check_main():
    full_bsp_data = {
        "update_time": datetime.now().isoformat(),
        "level": {}
    }
    for stock_code in stock_list:
        try:
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
                lv_key = lv_list[lv_index].name
                last_bsp = last_recorded_bsp_list[lv_index]
                if last_bsp:
                    print(f"stock: {stock_code}, "
                          f"last_recorded_bsp: {last_bsp.klu.time}, "
                          f"is buy: {last_bsp.is_buy}, "
                          f"type: {last_bsp.type}, lv: {lv_index}")
                if lv_key not in full_bsp_data["level"]:
                    full_bsp_data["level"][lv_key] = {}
                ctime_obj = last_bsp.klu.time
                bsp_time = datetime(ctime_obj.year, ctime_obj.month, ctime_obj.day, ctime_obj.hour,
                                    ctime_obj.minute) if last_bsp else None
                format_bsp_time = bsp_time.strftime("%Y-%m-%d %H:%M:%S") if last_bsp else None
                format_bsp_type = [each_type.value for each_type in last_bsp.type]
                bsp_info_dict = {"is_buy": last_bsp.is_buy, "type": format_bsp_type, "time": format_bsp_time}
                print(f"bsp_info_dict: {bsp_info_dict}")
                full_bsp_data["level"][lv_key][stock_code] = bsp_info_dict
        except Exception as e:
            print(f"full_stock_high_level_bsp_check_main error: {traceback.format_exc()}")
        time.sleep(3)
    # 写入最终文件
    redis_client.set(constants.REDIS_KEY_STOCK_BSP_RECORDS, json.dumps(full_bsp_data))
    # with open("./Temp/stock_bsp_records.json", "w") as f:
    #     json.dump(full_bsp_data, f, indent=2, ensure_ascii=False)
    

def full_etf_high_level_bsp_check_main():
    full_bsp_data = {
        "update_time": datetime.now().isoformat(),
        "level": {}
    }
    for etf_code in etf_list:
        try:
            chan = build_chan_object(etf_code)
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
                lv_key = lv_list[lv_index].name
                last_bsp = last_recorded_bsp_list[lv_index]
                if last_bsp:
                    print(f"etf: {etf_code}, "
                          f"last_recorded_bsp: {last_bsp.klu.time}, "
                          f"is buy: {last_bsp.is_buy}, "
                          f"type: {last_bsp.type}, lv: {lv_index}")
                if lv_key not in full_bsp_data["level"]:
                    full_bsp_data["level"][lv_key] = {}
                ctime_obj = last_bsp.klu.time
                bsp_time = datetime(ctime_obj.year, ctime_obj.month, ctime_obj.day, ctime_obj.hour, ctime_obj.minute) if last_bsp else None
                format_bsp_time = bsp_time.strftime("%Y-%m-%d %H:%M:%S") if last_bsp else None
                format_bsp_type = [each_type.value for each_type in last_bsp.type]
                bsp_info_dict = {"is_buy": last_bsp.is_buy, "type": format_bsp_type, "time": format_bsp_time}
                print(f"bsp_info_dict: {bsp_info_dict}")
                full_bsp_data["level"][lv_key][etf_code] = bsp_info_dict
        except Exception as e:
            print(f"full_stock_high_level_bsp_check_main error: {traceback.format_exc()}")
        time.sleep(3)
        # 写入最终文件
    redis_client.set(constants.REDIS_KEY_ETF_BSP_RECORDS, json.dumps(full_bsp_data))
    # with open("./Temp/etf_bsp_records.json", "w") as f:
    #     json.dump(full_bsp_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    full_etf_high_level_bsp_check_main()
    # full_stock_high_level_bsp_check_main()
