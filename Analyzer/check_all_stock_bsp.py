import json
import time
import traceback
from datetime import datetime

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, BSP_TYPE, DATA_SRC, FX_TYPE, KL_TYPE


data_src = DATA_SRC.BAO_STOCK
with open("../Source/stock_code_to_name.json", "r", encoding="utf-8") as f:
    stock_dict = json.load(f)
stock_list = stock_dict.keys()
print(stock_list)
lv_list = [KL_TYPE.K_WEEK, KL_TYPE.K_DAY]
# lv_list = [KL_TYPE.K_60M]

begin_time = "2022-01-01"
end_time = None
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


def check_stock_bsp_main():
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
                        last_recorded_bsp_list[lv_index] = None
                        continue
                    if (cur_lv_chan[-2].fx == FX_TYPE.BOTTOM and last_bsp.is_buy) or (cur_lv_chan[-2].fx == FX_TYPE.TOP and not last_bsp.is_buy):
                        last_recorded_bsp_list[lv_index] = last_bsp
                        # print(f'bsp: {cur_lv_chan[lv_index][-1].time}, is buy: {last_bsp.is_buy}, lv: {lv_index}')
            for lv_index in range(0, len(lv_list)):
                last_bsp = last_recorded_bsp_list[lv_index]
                if last_bsp:
                    print(f"stock: {stock_code}, "
                          f"last_recorded_bsp: {last_bsp.klu.time}, "
                          f"is buy: {last_bsp.is_buy}, "
                          f"type: {last_bsp.type}, lv: {lv_index}")
            time.sleep(2)
        except Exception as e:
            print(f"{stock_code} check bsp failed: {traceback.format_exc()}")


if __name__ == "__main__":
    check_stock_bsp_main()
