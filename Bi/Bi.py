from typing import List, Optional

from Common.cache import make_cache
from Common.CEnum import BI_DIR, BI_TYPE, DATA_FIELD, FX_TYPE, MACD_ALGO
from Common.ChanException import CChanException, ErrCode
from KLine.KLine import CKLine
from KLine.KLine_Unit import CKLine_Unit


class CBi:
    def __init__(self, begin_klc: CKLine, end_klc: CKLine, idx: int, is_sure: bool):
        # 初始化笔对象，起始K线、结束K线、索引、是否是确定笔
        self.__dir = None  # 笔方向（向上或向下）
        self.__idx = idx  # 在列表中的索引
        self.__type = BI_TYPE.STRICT  # 默认笔的类型为严格笔
        self.set(begin_klc, end_klc)  # 设置起止K线并确定方向
        self.__is_sure = is_sure  # 是否是“确定笔”（非虚拟笔）
        self.__sure_end: List[CKLine] = []  # 若是虚拟笔，这里保存过渡过程中真实的结束K线
        self.__seg_idx: Optional[int] = None  # 所属的线段序号

        from Seg.Seg import CSeg
        self.parent_seg: Optional[CSeg[CBi]] = None  # 所属的线段对象

        from BuySellPoint.BS_Point import CBS_Point
        self.bsp: Optional[CBS_Point] = None  # 尾部是否是买卖点对象

        self.next: Optional[CBi] = None  # 下一笔
        self.pre: Optional[CBi] = None  # 上一笔

    def clean_cache(self):
        # 清理缓存（装饰器make_cache用到）
        self._memoize_cache = {}

    @property
    def begin_klc(self): return self.__begin_klc  # 起始K线

    @property
    def end_klc(self): return self.__end_klc  # 结束K线

    @property
    def dir(self): return self.__dir  # 方向

    @property
    def idx(self): return self.__idx  # 索引

    @property
    def type(self): return self.__type  # 类型

    @property
    def is_sure(self): return self.__is_sure  # 是否是确定笔

    @property
    def sure_end(self): return self.__sure_end  # 虚拟笔的真实结束K线列表

    @property
    def klc_lst(self):
        # 返回从begin_klc到end_klc的K线迭代器（正序）
        klc = self.begin_klc
        while True:
            yield klc
            klc = klc.next
            if not klc or klc.idx > self.end_klc.idx:
                break

    @property
    def klc_lst_re(self):
        # 返回从end_klc到begin_klc的K线迭代器（倒序）
        klc = self.end_klc
        while True:
            yield klc
            klc = klc.pre
            if not klc or klc.idx < self.begin_klc.idx:
                break

    @property
    def seg_idx(self): return self.__seg_idx  # 所属线段的索引

    def set_seg_idx(self, idx):
        self.__seg_idx = idx  # 设置所属线段索引

    def __str__(self):
        # 打印笔的方向、起止K线
        return f"{self.dir}|{self.begin_klc} ~ {self.end_klc}"

    def check(self):
        # 校验起止K线是否与方向一致
        try:
            if self.is_down():
                assert self.begin_klc.high > self.end_klc.low
            else:
                assert self.begin_klc.low < self.end_klc.high
        except Exception as e:
            raise CChanException(f"{self.idx}:{self.begin_klc[0].time}~{self.end_klc[-1].time}笔的方向和收尾位置不一致!", ErrCode.BI_ERR) from e

    def set(self, begin_klc: CKLine, end_klc: CKLine):
        # 设置笔的起始和结束K线并确定方向
        self.__begin_klc = begin_klc
        self.__end_klc = end_klc
        if begin_klc.fx == FX_TYPE.BOTTOM:
            self.__dir = BI_DIR.UP
        elif begin_klc.fx == FX_TYPE.TOP:
            self.__dir = BI_DIR.DOWN
        else:
            raise CChanException("ERROR DIRECTION when creating bi", ErrCode.BI_ERR)
        self.check()
        self.clean_cache()

    @make_cache
    def get_begin_val(self):
        # 返回笔的起点值（上笔为low，下笔为high）
        return self.begin_klc.low if self.is_up() else self.begin_klc.high

    @make_cache
    def get_end_val(self):
        # 返回笔的终点值（上笔为high，下笔为low）
        return self.end_klc.high if self.is_up() else self.end_klc.low

    @make_cache
    def get_begin_klu(self) -> CKLine_Unit:
        # 获取起点的极值K线单元
        return self.begin_klc.get_peak_klu(is_high=not self.is_up())

    @make_cache
    def get_end_klu(self) -> CKLine_Unit:
        # 获取终点的极值K线单元
        return self.end_klc.get_peak_klu(is_high=self.is_up())

    @make_cache
    def amp(self):
        # 笔的振幅
        return abs(self.get_end_val() - self.get_begin_val())

    @make_cache
    def get_klu_cnt(self):
        # K线单元数量
        return self.get_end_klu().idx - self.get_begin_klu().idx + 1

    @make_cache
    def get_klc_cnt(self):
        # K线数量
        assert self.end_klc.idx == self.get_end_klu().klc.idx
        assert self.begin_klc.idx == self.get_begin_klu().klc.idx
        return self.end_klc.idx - self.begin_klc.idx + 1

    @make_cache
    def _high(self):
        # 笔的最高点
        return self.end_klc.high if self.is_up() else self.begin_klc.high

    @make_cache
    def _low(self):
        # 笔的最低点
        return self.begin_klc.low if self.is_up() else self.end_klc.low

    @make_cache
    def _mid(self):
        # 中位价
        return (self._high() + self._low()) / 2

    @make_cache
    def is_down(self):
        # 是否是下笔
        return self.dir == BI_DIR.DOWN

    @make_cache
    def is_up(self):
        # 是否是上笔
        return self.dir == BI_DIR.UP

    def update_virtual_end(self, new_klc: CKLine):
        # 更新虚拟笔的结束K线，并保存真实历史
        self.append_sure_end(self.end_klc)
        self.update_new_end(new_klc)
        self.__is_sure = False

    def restore_from_virtual_end(self, sure_end: CKLine):
        # 从虚拟笔恢复为确定笔
        self.__is_sure = True
        self.update_new_end(sure_end)
        self.__sure_end = []

    def append_sure_end(self, klc: CKLine):
        # 保存确定结束K线
        self.__sure_end.append(klc)

    def update_new_end(self, new_klc: CKLine):
        # 更新笔的结束K线
        self.__end_klc = new_klc
        self.check()
        self.clean_cache()

    def cal_macd_metric(self, macd_algo, is_reverse):
        # 计算MACD相关指标
        if macd_algo == MACD_ALGO.AREA:
            return self.Cal_MACD_half(is_reverse)
        elif macd_algo == MACD_ALGO.PEAK:
            return self.Cal_MACD_peak()
        elif macd_algo == MACD_ALGO.FULL_AREA:
            return self.Cal_MACD_area()
        elif macd_algo == MACD_ALGO.DIFF:
            return self.Cal_MACD_diff()
        elif macd_algo == MACD_ALGO.SLOPE:
            return self.Cal_MACD_slope()
        elif macd_algo == MACD_ALGO.AMP:
            return self.Cal_MACD_amp()
        elif macd_algo == MACD_ALGO.AMOUNT:
            return self.Cal_MACD_trade_metric(DATA_FIELD.FIELD_TURNOVER, cal_avg=False)
        elif macd_algo == MACD_ALGO.VOLUMN:
            return self.Cal_MACD_trade_metric(DATA_FIELD.FIELD_VOLUME, cal_avg=False)
        elif macd_algo == MACD_ALGO.VOLUMN_AVG:
            return self.Cal_MACD_trade_metric(DATA_FIELD.FIELD_VOLUME, cal_avg=True)
        elif macd_algo == MACD_ALGO.AMOUNT_AVG:
            return self.Cal_MACD_trade_metric(DATA_FIELD.FIELD_TURNOVER, cal_avg=True)
        elif macd_algo == MACD_ALGO.TURNRATE_AVG:
            return self.Cal_MACD_trade_metric(DATA_FIELD.FIELD_TURNRATE, cal_avg=True)
        elif macd_algo == MACD_ALGO.RSI:
            return self.Cal_Rsi()
        else:
            raise CChanException(f"unsupport macd_algo={macd_algo}, should be one of area/full_area/peak/diff/slope/amp", ErrCode.PARA_ERROR)

    @make_cache
    def Cal_Rsi(self):
        # RSI指标作为度量
        rsi_lst: List[float] = []
        for klc in self.klc_lst:
            rsi_lst.extend(klu.rsi for klu in klc.lst)
        return 10000.0/(min(rsi_lst)+1e-7) if self.is_down() else max(rsi_lst)

    @make_cache
    def Cal_MACD_area(self):
        # 整个笔范围内的MACD面积
        _s = 1e-7
        begin_klu = self.get_begin_klu()
        end_klu = self.get_end_klu()
        for klc in self.klc_lst:
            for klu in klc.lst:
                if begin_klu.idx <= klu.idx <= end_klu.idx:
                    if (self.is_down() and klu.macd.macd < 0) or (self.is_up() and klu.macd.macd > 0):
                        _s += abs(klu.macd.macd)
        return _s

    @make_cache
    def Cal_MACD_peak(self):
        # MACD的峰值
        peak = 1e-7
        for klc in self.klc_lst:
            for klu in klc.lst:
                if abs(klu.macd.macd) > peak:
                    if self.is_down() and klu.macd.macd < 0:
                        peak = abs(klu.macd.macd)
                    elif self.is_up() and klu.macd.macd > 0:
                        peak = abs(klu.macd.macd)
        return peak

    def Cal_MACD_half(self, is_reverse):
        # 半笔MACD面积，"half"的含义 ：仅计算DIFF与DEA交叉后的区域面积
        return self.Cal_MACD_half_reverse() if is_reverse else self.Cal_MACD_half_obverse()

    @make_cache
    def Cal_MACD_half_obverse(self):
        # 从开始计算MACD面积，直到拐点
        _s = 1e-7
        begin_klu = self.get_begin_klu()
        peak_macd = begin_klu.macd.macd
        for klc in self.klc_lst:
            for klu in klc.lst:
                if klu.idx < begin_klu.idx:
                    continue
                if klu.macd.macd * peak_macd > 0:
                    _s += abs(klu.macd.macd)
                else:
                    break
            else:
                continue
            break
        return _s

    @make_cache
    def Cal_MACD_half_reverse(self):
        # 从尾部反向计算MACD面积
        _s = 1e-7
        begin_klu = self.get_end_klu()
        peak_macd = begin_klu.macd.macd
        for klc in self.klc_lst_re:
            for klu in klc[::-1]:
                if klu.idx > begin_klu.idx:
                    continue
                if klu.macd.macd * peak_macd > 0:
                    _s += abs(klu.macd.macd)
                else:
                    break
            else:
                continue
            break
        return _s

    @make_cache
    def Cal_MACD_diff(self):
        # MACD柱最大最小差值
        _max, _min = float("-inf"), float("inf")
        for klc in self.klc_lst:
            for klu in klc.lst:
                macd = klu.macd.macd
                _max = max(_max, macd)
                _min = min(_min, macd)
        return _max - _min

    @make_cache
    def Cal_MACD_slope(self):
        # MACD斜率
        begin_klu = self.get_begin_klu()
        end_klu = self.get_end_klu()
        if self.is_up():
            return (end_klu.high - begin_klu.low) / end_klu.high / (end_klu.idx - begin_klu.idx + 1)
        else:
            return (begin_klu.high - end_klu.low) / begin_klu.high / (end_klu.idx - begin_klu.idx + 1)

    @make_cache
    def Cal_MACD_amp(self):
        # MACD振幅
        begin_klu = self.get_begin_klu()
        end_klu = self.get_end_klu()
        if self.is_down():
            return (begin_klu.high - end_klu.low) / begin_klu.high
        else:
            return (end_klu.high - begin_klu.low) / begin_klu.low

    def Cal_MACD_trade_metric(self, metric: str, cal_avg=False) -> float:
        # 计算交易类指标（成交量、换手率等）
        _s = 0
        for klc in self.klc_lst:
            for klu in klc.lst:
                metric_res = klu.trade_info.metric[metric]
                if metric_res is None:
                    return 0.0
                _s += metric_res
        return _s / self.get_klu_cnt() if cal_avg else _s
