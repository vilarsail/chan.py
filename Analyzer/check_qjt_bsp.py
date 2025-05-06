from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, BSP_TYPE, DATA_SRC, FX_TYPE, KL_TYPE


if __name__ == "__main__":
    """
    一个极其弱智的策略，只交易一类买卖点，底分型形成后就开仓，直到一类卖点顶分型形成后平仓
    只用做展示如何自己实现策略，做回测用~
    """
    code = "sh.601360"
    begin_time = "2025-01-01"
    end_time = "2025-05-18"
    data_src = DATA_SRC.BAO_STOCK
    lv_list = [KL_TYPE.K_60M, KL_TYPE.K_15M]

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

    chan = CChan(
        code=code,
        begin_time=begin_time,
        end_time=end_time,
        data_src=data_src,
        lv_list=lv_list,
        config=config,
        autype=AUTYPE.QFQ,
    )

    is_hold = False
    last_buy_price = None

    if len(lv_list) < 2:
        print(f"error: invalid lv list {lv_list}")

    for chan_snapshot in chan.step_load():
        cur_bsp_list = chan_snapshot.get_bsp(0)  # 获取买卖点列表
        sub_bsp_list = chan_snapshot.get_bsp(1)
        if not cur_bsp_list:  # 为空
            continue
        cur_last_bsp = cur_bsp_list[-1]  # 最后一个买卖点
        cur_lv_chan = chan_snapshot[0]
        sub_lv_chan = chan_snapshot[1]
        if cur_last_bsp.klu.klc.idx != cur_lv_chan[-1].idx:
            continue
        print(f'bsp1: {cur_lv_chan[-1][-1].time}, is buy: {cur_last_bsp.is_buy}')
        cur_last_klu = chan_snapshot[-1][-1]
        # if last_bsp.klu.idx != last_klu.idx:
        #     continue
        sub_bsp = sub_bsp_list[-1]

        cur_main_klu = cur_lv_chan[-1][-1]
        sub_main_klu = sub_bsp.klu.sup_kl
        if sub_main_klu.idx == cur_main_klu.idx:  # 确保比较的是同一层级的K线索引
            print(f'区间套买点触发! 主级时间:{cur_main_klu.time} 次级时间:{sub_lv_chan[-1][-1].time}, '
                  f'主级类型: {cur_last_bsp.type}, {cur_last_bsp.is_buy}, 次级类型: {sub_bsp.type}, {sub_bsp.is_buy}')

