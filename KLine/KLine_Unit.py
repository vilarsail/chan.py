import copy
from typing import Dict, Optional

from Common.CEnum import DATA_FIELD, TRADE_INFO_LST, TREND_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.CTime import CTime
from Math.BOLL import BOLL_Metric, BollModel
from Math.Demark import CDemarkEngine, CDemarkIndex
from Math.KDJ import KDJ
from Math.MACD import CMACD, CMACD_item
from Math.RSI import RSI
from Math.TrendModel import CTrendModel

from .TradeInfo import CTradeInfo


class CKLine_Unit:
    def __init__(self, kl_dict, autofix=False):
        """K线单元构造函数
        Args:
            kl_dict: K线数据字典，包含时间、四价等基础数据
            autofix: 是否自动修正异常数据（默认False）
        """
        # 初始化基础K线属性
        self.kl_type = None  # K线类型（分钟/日线等）
        self.time: CTime = kl_dict[DATA_FIELD.FIELD_TIME]  # 时间戳
        self.close = kl_dict[DATA_FIELD.FIELD_CLOSE]  # 收盘价
        self.open = kl_dict[DATA_FIELD.FIELD_OPEN]  # 开盘价
        self.high = kl_dict[DATA_FIELD.FIELD_HIGH]  # 最高价
        self.low = kl_dict[DATA_FIELD.FIELD_LOW]  # 最低价

        self.check(autofix)  # 数据完整性校验

        # 初始化交易信息和技术指标
        self.trade_info = CTradeInfo(kl_dict)  # 成交量等交易指标
        self.demark: CDemarkIndex = CDemarkIndex()  # 德马克指标

        # 多级别K线关联结构
        self.sub_kl_list = []  # 次级别K线单元列表
        self.sup_kl: Optional[CKLine_Unit] = None  # 高级别K线单元指针

        # 合并K线容器指针（延迟导入避免循环依赖）
        from KLine.KLine import CKLine
        self.__klc: Optional[CKLine] = None  # 所属合并K线容器

        # 技术指标存储
        self.trend: Dict[TREND_TYPE, Dict[int, float]] = {}  # 趋势指标（多周期）
        self.limit_flag = 0  # 涨跌停标记：1=涨停，-1=跌停，0=正常

        # K线单元链表指针
        self.pre: Optional[CKLine_Unit] = None  # 前驱K线
        self.next: Optional[CKLine_Unit] = None  # 后继K线

        self.set_idx(-1)  # 初始化索引位置

    def __deepcopy__(self, memo):
        """深拷贝实现（用于回测系统状态保存）"""
        # 构造基础数据字典
        _dict = {
            DATA_FIELD.FIELD_TIME: self.time,
            DATA_FIELD.FIELD_CLOSE: self.close,
            DATA_FIELD.FIELD_OPEN: self.open,
            DATA_FIELD.FIELD_HIGH: self.high,
            DATA_FIELD.FIELD_LOW: self.low,
        }
        # 复制交易指标
        for metric in TRADE_INFO_LST:
            if metric in self.trade_info.metric:
                _dict[metric] = self.trade_info.metric[metric]

        # 创建新对象并复制技术指标
        obj = CKLine_Unit(_dict)
        obj.demark = copy.deepcopy(self.demark, memo)
        obj.trend = copy.deepcopy(self.trend, memo)
        obj.limit_flag = self.limit_flag
        # 复制各类技术指标
        if hasattr(self, "macd"):
            obj.macd = copy.deepcopy(self.macd, memo)
        if hasattr(self, "boll"):
            obj.boll = copy.deepcopy(self.boll, memo)
        if hasattr(self, "rsi"):
            obj.rsi = copy.deepcopy(self.rsi, memo)
        if hasattr(self, "kdj"):
            obj.kdj = copy.deepcopy(self.kdj, memo)
        obj.set_idx(self.idx)
        memo[id(self)] = obj  # 注册到memo防止循环引用
        return obj

    @property
    def klc(self):
        """获取所属合并K线容器（非空断言）"""
        assert self.__klc is not None
        return self.__klc

    def set_klc(self, klc):
        """设置所属合并K线容器"""
        self.__klc = klc

    @property
    def idx(self):
        """获取在合并K线中的索引位置"""
        return self.__idx

    def set_idx(self, idx):
        """设置索引位置"""
        self.__idx: int = idx

    def __str__(self):
        """字符串表示：索引+时间+四价+交易信息"""
        return f"{self.idx}:{self.time}/{self.kl_type} open={self.open} close={self.close} high={self.high} low={self.low} {self.trade_info}"

    def check(self, autofix=False):
        """数据完整性校验
        Args:
            autofix: 是否自动修正异常数据（默认False）
        """
        # 校验最低价是否真实最低
        if self.low > min([self.low, self.open, self.high, self.close]):
            if autofix:
                self.low = min([self.low, self.open, self.high, self.close])
            else:
                raise CChanException(f"{self.time} low price异常", ErrCode.KL_DATA_INVALID)
        # 校验最高价是否真实最高
        if self.high < max([self.low, self.open, self.high, self.close]):
            if autofix:
                self.high = max([self.low, self.open, self.high, self.close])
            else:
                raise CChanException(f"{self.time} high price异常", ErrCode.KL_DATA_INVALID)

    def add_children(self, child):
        """添加次级别K线单元"""
        self.sub_kl_list.append(child)

    def set_parent(self, parent: 'CKLine_Unit'):
        """设置父级K线单元"""
        self.sup_kl = parent

    def get_children(self):
        """迭代获取所有子级K线单元"""
        yield from self.sub_kl_list

    def _low(self):
        """获取有效最低价（兼容笔/线段处理）"""
        return self.low

    def _high(self):
        """获取有效最高价（兼容笔/线段处理）"""
        return self.high

    def set_metric(self, metric_model_lst: list) -> None:
        """批量设置技术指标
        Args:
            metric_model_lst: 指标计算模型列表
        """
        for metric_model in metric_model_lst:
            if isinstance(metric_model, CMACD):
                self.macd: CMACD_item = metric_model.add(self.close)
            elif isinstance(metric_model, CTrendModel):
                if metric_model.type not in self.trend:
                    self.trend[metric_model.type] = {}
                self.trend[metric_model.type][metric_model.T] = metric_model.add(self.close)
            elif isinstance(metric_model, BollModel):
                self.boll: BOLL_Metric = metric_model.add(self.close)
            elif isinstance(metric_model, CDemarkEngine):
                self.demark = metric_model.update(idx=self.idx, close=self.close, high=self.high, low=self.low)
            elif isinstance(metric_model, RSI):
                self.rsi = metric_model.add(self.close)
            elif isinstance(metric_model, KDJ):
                self.kdj = metric_model.add(self.high, self.low, self.close)

    def get_parent_klc(self):
        """获取父级合并K线容器"""
        assert self.sup_kl is not None
        return self.sup_kl.klc

    def include_sub_lv_time(self, sub_lv_t: str) -> bool:
        """检查是否包含指定时间的子级别K线（递归查询）
        Args:
            sub_lv_t: 目标时间字符串
        """
        if self.time.to_str() == sub_lv_t:
            return True
        for sub_klu in self.sub_kl_list:
            if sub_klu.time.to_str() == sub_lv_t:
                return True
            if sub_klu.include_sub_lv_time(sub_lv_t):
                return True
        return False

    def set_pre_klu(self, pre_klu: Optional['CKLine_Unit']):
        """设置前驱K线并建立双向链接"""
        if pre_klu is None:
            return
        pre_klu.next = self
        self.pre = pre_klu