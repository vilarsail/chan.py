import os
import tempfile
import traceback

import matplotlib
matplotlib.use('Agg')

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from Plot.PlotDriver import CPlotDriver


def generate_stock_image(stock_code, begin_time, end_time, lv_list):
    config = CChanConfig({
        "bi_algo": "advanced",
        "bi_strict": False,
        "trigger_step": False,
        "skip_step": 0,
        "divergence_rate": 0.8,
        "bsp2_follow_1": False,
        "bsp3_follow_1": False,
        "min_zs_cnt": 0,
        "bs1_peak": False,
        "macd_algo": "area",
        "bs_type": '1,2,3a,1p,2s,3b',
        "print_warning": True,
        "zs_algo": "normal",
        "zs_combine": False,
    })
    plot_config = {
        "plot_kline": True,
        "plot_kline_combine": False,
        "plot_bi": True,
        "plot_seg": True,
        "plot_eigen": False,
        "plot_zs": True,
        "plot_macd": True,
        "plot_mean": False,
        "plot_channel": False,
        "plot_bsp": True,
        "plot_extrainfo": False,
        "plot_demark": False,
        "plot_marker": False,
        "plot_rsi": False,
        "plot_kdj": False,
    }
    plot_para = {
        "seg": {
            # "plot_trendline": True,
        },
        "bi": {
            "show_num": True,
            "disp_end": True,
        },
        "figure": {
            "x_range": 400,
        },
        "marker": {
            # "markers": {  # text, position, color
            #     '2023/06/01': ('marker here', 'up', 'red'),
            #     '2023/06/08': ('marker here', 'down')
            # },
        }
    }
    try:
        chan = CChan(
            code=stock_code,
            begin_time=begin_time,
            end_time=end_time,
            data_src=DATA_SRC.SINA,
            lv_list=[KL_TYPE[kl_type] for kl_type in lv_list],
            config=config,
            autype=AUTYPE.QFQ,
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmpfile:
            plot_driver = CPlotDriver(
                chan,
                plot_config=plot_config,
                plot_para=plot_para,
            )
            print(f"save tmpfile: {tmpfile.name}")
            plot_driver.save2img(tmpfile.name)
            tmpfile.close() 
            return tmpfile.name
    except Exception as e:
        print(f"generate_stock_image exception: {traceback.format_exc()}")