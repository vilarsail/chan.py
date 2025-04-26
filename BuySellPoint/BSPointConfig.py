from typing import Dict, List, Optional

from Common.CEnum import BSP_TYPE, MACD_ALGO
from Common.func_util import _parse_inf


class CBSPointConfig:
    def __init__(self, **args):
        # 初始化买卖点配置，分别配置买点和卖点的判定参数
        self.b_conf = CPointConfig(**args)  # 买点配置
        self.s_conf = CPointConfig(**args)  # 卖点配置

    def GetBSConfig(self, is_buy):
        # 根据 is_buy 参数返回买点或卖点的配置
        return self.b_conf if is_buy else self.s_conf


class CPointConfig:
    """
    bs_type：关注的买卖点类型，逗号分隔，默认"1,1p,2,2s,3a,3b"
    1,2：分别表示1，2，3类买卖点
    2s：类二买卖点
    1p：盘整背驰1类买卖点
    3a：中枢出现在1类后面的3类买卖点（3-after）
    3b：中枢出现在1类前面的3类买卖点（3-before）
    """
    def __init__(self,
                 divergence_rate,            # 背驰比例阈值（如0.618等）
                 min_zs_cnt,                 # 最少中枢个数要求
                 bsp1_only_multibi_zs,       # 是否要求1类买卖点出现在多笔组成的中枢中
                 max_bs2_rate,               # 2类买卖点允许的最大波动比例
                 macd_algo,                  # MACD 计算方法（例如 area、peak 等）
                 bs1_peak,                   # 1类买卖点是否必须出现在高低点（极值）
                 bs_type,                    # 指定要检测的买卖点类型（如1, 2, 3a...）
                 bsp2_follow_1,              # 2类买点是否依赖1类买点存在
                 bsp3_follow_1,              # 3类买点是否依赖1类买点存在
                 bsp3_peak,                  # 3类买点是否要求处于极值点
                 bsp2s_follow_2,             # 2s是否依赖于已有2类买点
                 max_bsp2s_lv,               # 2s类点的最大层级
                 strict_bsp3,                # 是否严格限制3类买点的位置
                 ):
        self.divergence_rate = divergence_rate
        self.min_zs_cnt = min_zs_cnt
        self.bsp1_only_multibi_zs = bsp1_only_multibi_zs
        self.max_bs2_rate = max_bs2_rate
        assert self.max_bs2_rate <= 1  # 2类买卖点波动率不能大于1（100%）

        self.SetMacdAlgo(macd_algo)  # 将MACD算法字符串转换为枚举类型

        self.bs1_peak = bs1_peak
        self.tmp_target_types = bs_type  # 暂存字符串形式的买卖点类型
        self.target_types: List[BSP_TYPE] = []  # 解析后的买卖点类型（枚举列表）

        self.bsp2_follow_1 = bsp2_follow_1
        self.bsp3_follow_1 = bsp3_follow_1
        self.bsp3_peak = bsp3_peak
        self.bsp2s_follow_2 = bsp2s_follow_2
        self.max_bsp2s_lv: Optional[int] = max_bsp2s_lv
        self.strict_bsp3 = strict_bsp3

    def parse_target_type(self):
        # 将字符串格式的类型转换为 BSP_TYPE 枚举类型
        _d: Dict[str, BSP_TYPE] = {x.value: x for x in BSP_TYPE}
        if isinstance(self.tmp_target_types, str):
            self.tmp_target_types = [t.strip() for t in self.tmp_target_types.split(",")]
        for target_t in self.tmp_target_types:
            assert target_t in ['1', '2', '3a', '2s', '1p', '3b']  # 有效的买卖点类型
        self.target_types = [_d[_type] for _type in self.tmp_target_types]  # 转换为枚举列表

    def SetMacdAlgo(self, macd_algo):
        # 将 MACD 算法的字符串表示转换为 MACD_ALGO 枚举
        _d = {
            "area": MACD_ALGO.AREA,
            "peak": MACD_ALGO.PEAK,
            "full_area": MACD_ALGO.FULL_AREA,
            "diff": MACD_ALGO.DIFF,
            "slope": MACD_ALGO.SLOPE,
            "amp": MACD_ALGO.AMP,
            "amount": MACD_ALGO.AMOUNT,
            "volumn": MACD_ALGO.VOLUMN,
            "amount_avg": MACD_ALGO.AMOUNT_AVG,
            "volumn_avg": MACD_ALGO.VOLUMN_AVG,
            "turnrate_avg": MACD_ALGO.AMOUNT_AVG,  # NOTE: 此处重复指向 AMOUNT_AVG
            "rsi": MACD_ALGO.RSI,
        }
        self.macd_algo = _d[macd_algo]

    def set(self, k, v):
        # 动态设置某个参数值，支持解析 "inf" 字符串为 float('inf')
        v = _parse_inf(v)
        if k == "macd_algo":
            self.SetMacdAlgo(v)
        else:
            exec(f"self.{k} = {v}")  # 动态执行设置语句
