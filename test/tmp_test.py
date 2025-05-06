from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, BSP_TYPE, DATA_SRC, FX_TYPE, KL_TYPE
from collections import defaultdict

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

    def list_intersection_with_counts(list1, list2):
        count = defaultdict(int)
        for x in list2:
            count[x] += 1
        result = []
        for x in list1:
            if count[x] > 0:
                result.append(x)
                count[x] -= 1
        return result
    list1 = []
    list2 = []
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
            print(f'区间套买点触发! 主级时间:{cur_main_klu.time} 次级时间:{sub_lv_chan[-1][-1].time}')
        
            #  if sub_bsp.klu.sup_kl.idx == cur_last_klu.idx and sub_bsp.type2str().find("1") >= 0:
        # list1.append(sub_bsp.klu.sup_kl.idx)
        # list2.append(cur_last_klu.idx)
        # if sub_bsp.klu.sup_kl.idx == cur_last_klu.idx:
        #     print(f'sub bsp1: {sub_lv_chan[-1][-1].time}, is buy: {sub_bsp.is_buy}')
        # else:
        #     print(f"sub_bsp.klu.sup_kl.idx: {sub_bsp.klu.sup_kl.idx}, cur_last_klu.idx: {cur_last_klu.idx}, bsp1: {cur_lv_chan[-1][-1].time}, sub bsp1: {sub_lv_chan[-1][-1].time}")
        # print("no sub bsp found")
    print(list_intersection_with_counts(list1, list2))
    
    # for chan_snapshot in chan.step_load():
    #     bsp_list = chan_snapshot.get_bsp()  # 获取买卖点列表
    #     if not bsp_list:  # 为空
    #         print("bsp empty")
    #         continue
    #     last_bsp = bsp_list[-1]  # 最后一个买卖点
    #     cur_lv_chan = chan_snapshot[0]
    #     if last_bsp.klu.klc.idx != cur_lv_chan[-2].idx:
    #         continue
    #     if cur_lv_chan[-2].fx == FX_TYPE.BOTTOM and last_bsp.is_buy:
    #         print(f'bsp1: {cur_lv_chan[-1][-1].time}, is buy: {last_bsp.is_buy}')
    #     if cur_lv_chan[-2].fx == FX_TYPE.TOP and not last_bsp.is_buy:
    #         print(f'bsp1: {cur_lv_chan[-1][-1].time}, is buy: {last_bsp.is_buy}')

    # for chan_snapshot in chan.step_load():  # 每增加一根K线，返回当前静态精算结果
    #     bsp_list = chan_snapshot.get_bsp()  # 获取买卖点列表
    #     if not bsp_list:  # 为空
    #         continue
    #     last_bsp = bsp_list[-1]  # 最后一个买卖点
    #     if BSP_TYPE.T1 not in last_bsp.type and BSP_TYPE.T1P not in last_bsp.type:  # 假如只做1类买卖点
    #         continue
    #     cur_lv_chan = chan_snapshot[0]
    #     if last_bsp.klu.klc.idx != cur_lv_chan[-2].idx:
    #         continue
    #     if cur_lv_chan[-2].fx == FX_TYPE.BOTTOM and last_bsp.is_buy and not is_hold:  # 底分型形成后开仓
    #         last_buy_price = cur_lv_chan[-1][-1].close  # 开仓价格为最后一根K线close
    #         print(f'{cur_lv_chan[-1][-1].time}:buy price = {last_buy_price}')
    #         is_hold = True
    #     elif cur_lv_chan[-2].fx == FX_TYPE.TOP and not last_bsp.is_buy and is_hold:  # 顶分型形成后平仓
    #         sell_price = cur_lv_chan[-1][-1].close
    #         print(f'{cur_lv_chan[-1][-1].time}:sell price = {sell_price}, profit rate = {(sell_price-last_buy_price)/last_buy_price*100:.2f}%')
    #         is_hold = False
