from typing import Generic, Iterable, List, Optional, Self, TypeVar, Union, overload

from Common.cache import make_cache
from Common.CEnum import FX_TYPE, KLINE_DIR  # 分型类型和K线方向枚举
from Common.ChanException import CChanException, ErrCode
from KLine.KLine_Unit import CKLine_Unit  # 基础K线单元

from .Combine_Item import CCombine_Item  # 合并项辅助类

T = TypeVar('T')  # 泛型类型，支持K线单元或笔


class CKLine_Combiner(Generic[T]):
    """K线合并器核心类，负责处理K线的合并逻辑和分型识别"""

    def __init__(self, kl_unit: T, _dir):
        """初始化合并器
        Args:
            kl_unit: 初始K线单元或笔
            _dir: 合并方向 (KLINE_DIR.UP/KLINE_DIR.DOWN)
        """
        item = CCombine_Item(kl_unit)  # 将K线单元转换为合并项
        self.__time_begin = item.time_begin  # 合并K线起始时间
        self.__time_end = item.time_end  # 合并K线结束时间
        self.__high = item.high  # 合并后的最高价
        self.__low = item.low  # 合并后的最低价

        self.__lst: List[T] = [kl_unit]  # 包含的原始K线单元列表

        self.__dir = _dir  # 当前合并方向
        self.__fx = FX_TYPE.UNKNOWN  # 分型类型（顶/底分型）
        self.__pre: Optional[Self] = None  # 前一个合并K线
        self.__next: Optional[Self] = None  # 后一个合并K线

    def clean_cache(self):
        """清空缓存计算结果"""
        self._memoize_cache = {}

    # region 属性访问器
    @property
    def time_begin(self):
        return self.__time_begin  # 合并K线起始时间（只读）

    @property
    def time_end(self):
        return self.__time_end  # 合并K线结束时间（只读）

    @property
    def high(self):
        return self.__high  # 合并后的最高价（只读）

    @property
    def low(self):
        return self.__low  # 合并后的最低价（只读）

    @property
    def lst(self):
        return self.__lst  # 包含的原始K线单元列表（只读）

    @property
    def dir(self):
        return self.__dir  # 当前合并方向（只读）

    @property
    def fx(self):
        return self.__fx  # 分型类型（只读）

    @property
    def pre(self) -> Self:
        """前驱合并K线（非空断言）"""
        assert self.__pre is not None
        return self.__pre

    @property
    def next(self):
        return self.__next  # 后继合并K线（可能为空）

    # endregion

    def get_next(self) -> Self:
        """获取非空后继合并K线"""
        assert self.next is not None
        return self.next

    def test_combine(self, item: CCombine_Item, exclude_included=False, allow_top_equal=None):
        """测试是否可以合并新K线
        Args:
            item: 待合并的K线项
            exclude_included: 是否排除包含关系
            allow_top_equal: 特殊包含处理模式
        Returns:
            KLINE_DIR: 合并后的方向或合并类型
        """
        # 完全包含情况（当前K线完全包含新K线）
        if (self.high >= item.high and self.low <= item.low):
            return KLINE_DIR.COMBINE

        # 被包含情况（新K线完全包含当前K线）
        if (self.high <= item.high and self.low >= item.low):
            # 特殊包含处理（允许顶部/底部相等）
            if allow_top_equal == 1 and self.high == item.high and self.low > item.low:
                return KLINE_DIR.DOWN
            elif allow_top_equal == -1 and self.low == item.low and self.high < item.high:
                return KLINE_DIR.UP
            return KLINE_DIR.INCLUDED if exclude_included else KLINE_DIR.COMBINE

        # 向下合并情况（新K线高低点都低于当前K线）
        if (self.high > item.high and self.low > item.low):
            return KLINE_DIR.DOWN

        # 向上合并情况（新K线高低点都高于当前K线）
        if (self.high < item.high and self.low < item.low):
            return KLINE_DIR.UP

        # 未知情况抛出异常
        raise CChanException("combine type unknown", ErrCode.COMBINER_ERR)

    def add(self, unit_kl: T):
        """直接添加K线单元（仅用于深拷贝恢复状态）"""
        self.__lst.append(unit_kl)

    def set_fx(self, fx: FX_TYPE):
        """设置分型类型（仅用于深拷贝恢复状态）"""
        self.__fx = fx

    def try_add(self, unit_kl: T, exclude_included=False, allow_top_equal=None):
        """尝试合并新K线单元
        Args:
            unit_kl: 待合并的K线单元
            exclude_included: 是否排除包含关系
            allow_top_equal: 特殊包含处理模式
        Returns:
            KLINE_DIR: 合并后的方向
        """
        combine_item = CCombine_Item(unit_kl)
        _dir = self.test_combine(combine_item, exclude_included, allow_top_equal)

        if _dir == KLINE_DIR.COMBINE:  # 执行合并
            self.__lst.append(unit_kl)
            # 设置K线单元的合并容器
            if isinstance(unit_kl, CKLine_Unit):
                unit_kl.set_klc(self)

            # 根据合并方向更新高低价
            if self.dir == KLINE_DIR.UP:
                # 处理一字涨停板特殊情况
                if combine_item.high != combine_item.low or combine_item.high != self.high:
                    self.__high = max([self.high, combine_item.high])
                    self.__low = max([self.low, combine_item.low])
            elif self.dir == KLINE_DIR.DOWN:
                # 处理一字跌停板特殊情况
                if combine_item.high != combine_item.low or combine_item.low != self.low:
                    self.__high = min([self.high, combine_item.high])
                    self.__low = min([self.low, combine_item.low])
            else:
                raise CChanException(f"KLINE_DIR = {self.dir} 错误!", ErrCode.COMBINER_ERR)

            self.__time_end = combine_item.time_end
            self.clean_cache()

        return _dir  # 返回合并后的方向

    def get_peak_klu(self, is_high) -> T:
        """获取极值点对应的原始K线单元
        Args:
            is_high: 是否获取最高点
        """
        return self.get_high_peak_klu() if is_high else self.get_low_peak_klu()

    @make_cache
    def get_high_peak_klu(self) -> T:
        """逆向查找最高点对应的原始K线单元"""
        for kl in reversed(self.lst):
            if CCombine_Item(kl).high == self.high:
                return kl
        raise CChanException("找不到最高点对应K线单元", ErrCode.COMBINER_ERR)

    @make_cache
    def get_low_peak_klu(self) -> T:
        """逆向查找最低点对应的原始K线单元"""
        for kl in reversed(self.lst):
            if CCombine_Item(kl).low == self.low:
                return kl
        raise CChanException("找不到最低点对应K线单元", ErrCode.COMBINER_ERR)

    def update_fx(self, _pre: Self, _next: Self, exclude_included=False, allow_top_equal=None):
        """更新分型类型
        Args:
            _pre: 前驱合并K线
            _next: 后继合并K线
            exclude_included: 是否排除包含关系
            allow_top_equal: 特殊包含处理模式
        """
        # 建立双向链接
        self.set_next(_next)
        self.set_pre(_pre)
        _next.set_pre(self)

        # 分型判断逻辑
        if exclude_included:
            # 顶分型判断（排除包含关系）
            if _pre.high < self.high and _next.high <= self.high and _next.low < self.low:
                if allow_top_equal == 1 or _next.high < self.high:
                    self.__fx = FX_TYPE.TOP
            # 底分型判断（排除包含关系）
            elif _next.high > self.high and _pre.low > self.low and _next.low >= self.low:
                if allow_top_equal == -1 or _next.low > self.low:
                    self.__fx = FX_TYPE.BOTTOM
        else:
            # 标准顶分型判断（前后K线都低于当前K线）
            if _pre.high < self.high and _next.high < self.high and _pre.low < self.low and _next.low < self.low:
                self.__fx = FX_TYPE.TOP
            # 标准底分型判断（前后K线都高于当前K线）
            elif _pre.high > self.high and _next.high > self.high and _pre.low > self.low and _next.low > self.low:
                self.__fx = FX_TYPE.BOTTOM

        self.clean_cache()

    # region 魔术方法
    def __str__(self):
        """字符串表示：时间范围 + 价格区间"""
        return f"{self.time_begin}~{self.time_end} {self.low}->{self.high}"

    @overload
    def __getitem__(self, index: int) -> T:
        ...

    @overload
    def __getitem__(self, index: slice) -> List[T]:
        ...

    def __getitem__(self, index: Union[slice, int]) -> Union[List[T], T]:
        """支持下标访问合并的K线单元"""
        return self.lst[index]

    def __len__(self):
        """获取包含的原始K线数量"""
        return len(self.lst)

    def __iter__(self) -> Iterable[T]:
        """迭代器支持"""
        yield from self.lst

    # endregion

    def set_pre(self, _pre: Self):
        """设置前驱合并K线"""
        self.__pre = _pre
        self.clean_cache()

    def set_next(self, _next: Self):
        """设置后继合并K线"""
        self.__next = _next
        self.clean_cache()