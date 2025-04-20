from typing import List

from Bi.BiConfig import CBiConfig
from BuySellPoint.BSPointConfig import CBSPointConfig
from Common.CEnum import TREND_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.func_util import _parse_inf
from Math.BOLL import BollModel
from Math.Demark import CDemarkEngine
from Math.KDJ import KDJ
from Math.MACD import CMACD
from Math.RSI import RSI
from Math.TrendModel import CTrendModel
from Seg.SegConfig import CSegConfig
from ZS.ZSConfig import CZSConfig


class CChanConfig:
    """缠论系统配置中心，整合各模块配置参数"""
    
    def __init__(self, conf=None):
        """初始化配置，支持字典参数注入"""
        if conf is None:
            conf = {}
        conf = ConfigWithCheck(conf)  # 配置校验包装器
        
        # 笔配置初始化
        self.bi_conf = CBiConfig(
            bi_algo=conf.get("bi_algo", "normal"),  # 笔识别算法（normal/advanced）
            is_strict=conf.get("bi_strict", True),  # 是否严格模式
            bi_fx_check=conf.get("bi_fx_check", "strict"),  # 分型验证严格程度
            gap_as_kl=conf.get("gap_as_kl", False),  # 缺口是否视为独立K线
            bi_end_is_peak=conf.get('bi_end_is_peak', True),  # 笔端点是否必须为极值
            bi_allow_sub_peak=conf.get("bi_allow_sub_peak", True),  # 是否允许次高点成笔
        )
        
        # 线段配置初始化
        self.seg_conf = CSegConfig(
            seg_algo=conf.get("seg_algo", "chan"),  # 线段算法（chan/dyh）
            left_method=conf.get("left_seg_method", "peak"),  # 未完成线段处理方式
        )
        
        # 中枢配置初始化
        self.zs_conf = CZSConfig(
            need_combine=conf.get("zs_combine", True),  # 是否合并中枢
            zs_combine_mode=conf.get("zs_combine_mode", "zs"),  # 合并模式(zs/peak)
            one_bi_zs=conf.get("one_bi_zs", False),  # 是否允许单笔中枢
            zs_algo=conf.get("zs_algo", "normal"),  # 中枢生成算法
        )

        # 系统运行配置
        self.trigger_step = conf.get("trigger_step", False)  # 是否逐步触发模式
        self.skip_step = conf.get("skip_step", 0)  # 跳过的初始步数

        # 数据校验配置
        self.kl_data_check = conf.get("kl_data_check", True)  # 是否检查K线数据
        self.max_kl_misalgin_cnt = conf.get("max_kl_misalgin_cnt", 2)  # 最大K线不对齐数
        self.max_kl_inconsistent_cnt = conf.get("max_kl_inconsistent_cnt", 5)  # 最大时间不一致数
        self.auto_skip_illegal_sub_lv = conf.get("auto_skip_illegal_sub_lv", False)  # 自动跳过非法子级别
        self.print_warning = conf.get("print_warning", True)  # 打印警告信息
        self.print_err_time = conf.get("print_err_time", True)  # 打印错误时间

        # 技术指标参数
        self.mean_metrics: List[int] = conf.get("mean_metrics", [])  # 均线周期列表
        self.trend_metrics: List[int] = conf.get("trend_metrics", [])  # 趋势周期列表
        self.macd_config = conf.get("macd", {"fast": 12, "slow": 26, "signal": 9})  # MACD参数
        self.cal_demark = conf.get("cal_demark", False)  # 是否计算Demark指标
        self.cal_rsi = conf.get("cal_rsi", False)  # 是否计算RSI
        self.cal_kdj = conf.get("cal_kdj", False)  # 是否计算KDJ
        self.rsi_cycle = conf.get("rsi_cycle", 14)  # RSI计算周期
        self.kdj_cycle = conf.get("kdj_cycle", 9)  # KDJ计算周期
        self.demark_config = conf.get("demark", {  # Demark指标配置
            'demark_len': 9,  # 序列长度
            'setup_bias': 4,  # 趋势偏差阈值
            'countdown_bias': 2,  # 倒计时偏差阈值
            'max_countdown': 13,  # 最大倒计时段数
            'tiaokong_st': True,  # 是否启用跳空处理
            'setup_cmp2close': True,  # Setup阶段是否对比收盘价
            'countdown_cmp2close': True,  # Countdown是否对比收盘价
        })
        self.boll_n = conf.get("boll_n", 20)  # 布林线周期

        self.set_bsp_config(conf)  # 初始化买卖点配置
        conf.check()  # 执行最终配置校验

    def GetMetricModel(self):
        """构建技术指标计算模型集合"""
        res: List[CMACD | CTrendModel | BollModel | CDemarkEngine | RSI | KDJ] = [
            CMACD(  # MACD指标
                fastperiod=self.macd_config['fast'],
                slowperiod=self.macd_config['slow'],
                signalperiod=self.macd_config['signal'],
            )
        ]
        # 添加均线指标
        res.extend(CTrendModel(TREND_TYPE.MEAN, mean_T) for mean_T in self.mean_metrics)
        # 添加极值趋势指标
        for trend_T in self.trend_metrics:
            res.append(CTrendModel(TREND_TYPE.MAX, trend_T))
            res.append(CTrendModel(TREND_TYPE.MIN, trend_T))
        # 添加布林线指标
        res.append(BollModel(self.boll_n))
        # 添加Demark指标
        if self.cal_demark:
            res.append(CDemarkEngine(
                demark_len=self.demark_config['demark_len'],
                setup_bias=self.demark_config['setup_bias'],
                countdown_bias=self.demark_config['countdown_bias'],
                max_countdown=self.demark_config['max_countdown'],
                tiaokong_st=self.demark_config['tiaokong_st'],
                setup_cmp2close=self.demark_config['setup_cmp2close'],
                countdown_cmp2close=self.demark_config['countdown_cmp2close'],
            ))
        # 添加RSI指标
        if self.cal_rsi:
            res.append(RSI(self.rsi_cycle))
        # 添加KDJ指标
        if self.cal_kdj:
            res.append(KDJ(self.kdj_cycle))
        return res

    def set_bsp_config(self, conf):
        """初始化买卖点配置参数"""
        para_dict = {  # 默认参数配置
            "divergence_rate": float("inf"),  # 背驰率阈值
            "min_zs_cnt": 1,  # 最小中枢数量要求
            "bsp1_only_multibi_zs": True,  # 一买是否要求多笔中枢
            "max_bs2_rate": 0.9999,  # 二类买卖点最大幅度
            "macd_algo": "peak",  # MACD计算方式
            "bs1_peak": True,  # 一买是否要求极值
            "bs_type": "1,1p,2,2s,3a,3b",  # 启用的买卖点类型
            "bsp2_follow_1": True,  # 二买是否跟随一买
            "bsp3_follow_1": True,  # 三买是否跟随一买
            "bsp3_peak": False,  # 三买是否要求极值
            "bsp2s_follow_2": False,  # 二卖是否跟随二买
            "max_bsp2s_lv": None,  # 二卖最大级别限制
            "strict_bsp3": False,  # 严格三买模式
        }
        args = {para: conf.get(para, default_value) for para, default_value in para_dict.items()}
        
        # 初始化基础买卖点配置
        self.bs_point_conf = CBSPointConfig(**args)
        # 初始化线段买卖点配置（参数微调）
        self.seg_bs_point_conf = CBSPointConfig(**args)
        self.seg_bs_point_conf.b_conf.set("macd_algo", "slope")
        self.seg_bs_point_conf.s_conf.set("macd_algo", "slope")
        self.seg_bs_point_conf.b_conf.set("bsp1_only_multibi_zs", False)
        self.seg_bs_point_conf.s_conf.set("bsp1_only_multibi_zs", False)

        # 解析自定义配置参数
        for k, v in conf.items():
            if isinstance(v, str):
                v = f'"{v}"'
            v = _parse_inf(v)  # 处理无穷大值
            # 按后缀分类处理不同配置项
            if k.endswith("-buy"):
                prop = k.replace("-buy", "")
                exec(f"self.bs_point_conf.b_conf.set('{prop}', {v})")
            elif k.endswith("-sell"):
                prop = k.replace("-sell", "")
                exec(f"self.bs_point_conf.s_conf.set('{prop}', {v})")
            elif k.endswith("-segbuy"):
                prop = k.replace("-segbuy", "")
                exec(f"self.seg_bs_point_conf.b_conf.set('{prop}', {v})")
            elif k.endswith("-segsell"):
                prop = k.replace("-segsell", "")
                exec(f"self.seg_bs_point_conf.s_conf.set('{prop}', {v})")
            elif k.endswith("-seg"):
                prop = k.replace("-seg", "")
                exec(f"self.seg_bs_point_conf.b_conf.set('{prop}', {v})")
                exec(f"self.seg_bs_point_conf.s_conf.set('{prop}', {v})")
            elif k in args:
                exec(f"self.bs_point_conf.b_conf.set({k}, {v})")
                exec(f"self.bs_point_conf.s_conf.set({k}, {v})")
            else:
                raise CChanException(f"unknown para = {k}", ErrCode.PARA_ERROR)
        
        # 最终配置校验
        self.bs_point_conf.b_conf.parse_target_type()
        self.bs_point_conf.s_conf.parse_target_type()
        self.seg_bs_point_conf.b_conf.parse_target_type()
        self.seg_bs_point_conf.s_conf.parse_target_type()


class ConfigWithCheck:
    """配置校验包装类，防止无效参数"""
    
    def __init__(self, conf):
        self.conf = conf  # 原始配置字典

    def get(self, k, default_value=None):
        """获取并消费配置项"""
        res = self.conf.get(k, default_value)
        if k in self.conf:
            del self.conf[k]
        return res

    def items(self):
        """迭代消费所有配置项"""
        visit_keys = set()
        for k, v in self.conf.items():
            yield k, v
            visit_keys.add(k)
        for k in visit_keys:
            del self.conf[k]

    def check(self):
        """最终校验未消费的配置项"""
        if len(self.conf) > 0:
            invalid_key_lst = ",".join(list(self.conf.keys()))
            raise CChanException(f"invalid CChanConfig: {invalid_key_lst}", ErrCode.PARA_ERROR)