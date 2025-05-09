from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from Plot.AnimatePlotDriver import CAnimateDriver
from Plot.PlotDriver import CPlotDriver

if __name__ == "__main__":
    code = "sz002714"
    begin_time = "2025-01-01"
    end_time = "2025-05-18"
    data_src = DATA_SRC.SINA
    lv_list = [KL_TYPE.K_60M, KL_TYPE.K_30M, KL_TYPE.K_15M, KL_TYPE.K_5M]
    # lv_list = [KL_TYPE.K_WEEK, KL_TYPE.K_DAY]

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
    chan = CChan(
        code=code,
        begin_time=begin_time,
        end_time=end_time,
        data_src=data_src,
        lv_list=lv_list,
        config=config,
        autype=AUTYPE.QFQ,
    )

    if not config.trigger_step:
        plot_driver = CPlotDriver(
            chan,
            plot_config=plot_config,
            plot_para=plot_para,
        )
        #plot_driver.figure.show()
        plot_driver.save2img("./Test.png")
        # input("...")
    else:
        CAnimateDriver(
            chan,
            plot_config=plot_config,
            plot_para=plot_para,
        )
