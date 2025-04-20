from typing import Generic, List, Optional, TypeVar

from Bi.Bi import CBi
from BuySellPoint.BSPointConfig import CPointConfig
from Common.ChanException import CChanException, ErrCode
from Common.func_util import has_overlap
from KLine.KLine_Unit import CKLine_Unit
from Seg.Seg import CSeg

# 定义泛型类型，支持笔或线段作为基础单元
LINE_TYPE = TypeVar('LINE_TYPE', CBi, "CSeg")


class CZS(Generic[LINE_TYPE]):
    """缠论中枢核心类，封装中枢分析逻辑"""
    
    def __init__(self, lst: Optional[List[LINE_TYPE]], is_sure=True):
        """
        中枢构造函数
        Args:
            lst: 构成中枢的笔/线段列表（None时需后续初始化）
            is_sure: 是否确认中枢
        """
        # 中枢基础属性
        self.__is_sure = is_sure  # 中枢确认状态
        self.__sub_zs_lst: List[CZS] = []  # 子中枢列表

        if lst is None:  # 空构造用于复制场景
            return

        # 初始化起始单元和K线
        self.__begin: CKLine_Unit = lst[0].get_begin_klu()  # 中枢起始K线
        self.__begin_bi: LINE_TYPE = lst[0]  # 中枢起始笔/线段

        # 计算中枢价格区间
        self.update_zs_range(lst)

        # 初始化结束单元和极值
        self.__peak_high = float("-inf")  # 中枢波动最高价
        self.__peak_low = float("inf")     # 中枢波动最低价
        for item in lst:  # 遍历所有单元更新极值
            self.update_zs_end(item)

        # 进出中枢的笔记录
        self.__bi_in: Optional[LINE_TYPE] = None  # 进入中枢的笔
        self.__bi_out: Optional[LINE_TYPE] = None  # 离开中枢的笔
        self.__bi_lst: List[LINE_TYPE] = []  # 中枢包含的笔列表

    def clean_cache(self):
        """清空缓存数据（用于属性变更后刷新状态）"""
        self._memoize_cache = {}

    # 以下是属性访问器，保持原有结构不变
    @property
    def is_sure(self): return self.__is_sure

    @property
    def sub_zs_lst(self): return self.__sub_zs_lst

    @property
    def begin(self): return self.__begin

    @property
    def begin_bi(self): return self.__begin_bi

    @property
    def low(self): return self.__low  # 中枢最低价（重叠区间）

    @property
    def high(self): return self.__high  # 中枢最高价（重叠区间）

    @property
    def mid(self): return self.__mid  # 中枢中轴价

    @property
    def end(self): return self.__end  # 中枢结束K线

    @property
    def end_bi(self): return self.__end_bi  # 中枢结束笔

    @property
    def peak_high(self): return self.__peak_high  # 中枢涉及的最高价

    @property
    def peak_low(self): return self.__peak_low  # 中枢涉及的最低价

    @property
    def bi_in(self): return self.__bi_in  # 进入中枢的笔

    @property
    def bi_out(self): return self.__bi_out  # 离开中枢的笔

    @property
    def bi_lst(self): return self.__bi_lst  # 中枢包含的笔列表

    def update_zs_range(self, lst):
        """更新中枢价格区间（核心方法）"""
        self.__low: float = max(bi._low() for bi in lst)  # 重叠区间最低价
        self.__high: float = min(bi._high() for bi in lst)  # 重叠区间最高价
        self.__mid: float = (self.__low + self.__high) / 2  # 中枢中轴
        self.clean_cache()

    def is_one_bi_zs(self):
        """判断是否是单笔中枢（特殊形态）"""
        assert self.end_bi is not None
        return self.begin_bi.idx == self.end_bi.idx

    def update_zs_end(self, item):
        """更新中枢结束信息并维护极值"""
        self.__end: CKLine_Unit = item.get_end_klu()
        self.__end_bi: CBi = item
        # 更新波动极值
        if item._low() < self.peak_low:
            self.__peak_low = item._low()
        if item._high() > self.peak_high:
            self.__peak_high = item._high()
        self.clean_cache()

    def __str__(self):
        """字符串表示：起止索引+子中枢结构"""
        _str = f"{self.begin_bi.idx}->{self.end_bi.idx}"
        if _str2 := ",".join([str(sub_zs) for sub_zs in self.sub_zs_lst]):
            return f"{_str}({_str2})"  # 显示嵌套子中枢
        else:
            return _str

    def combine(self, zs2: 'CZS', combine_mode) -> bool:
        """合并中枢（支持两种合并模式）"""
        if zs2.is_one_bi_zs():  # 不合并单笔中枢
            return False
        if self.begin_bi.seg_idx != zs2.begin_bi.seg_idx:  # 跨线段不合并
            return False
        # 重叠合并模式
        if combine_mode == 'zs':
            if not has_overlap(self.low, self.high, zs2.low, zs2.high, equal=True):
                return False
            self.do_combine(zs2)
            return True
        # 极值重叠模式
        elif combine_mode == 'peak':
            if has_overlap(self.peak_low, self.peak_high, zs2.peak_low, zs2.peak_high):
                self.do_combine(zs2)
                return True
            else:
                return False
        else:
            raise CChanException(f"不支持的合并模式:{combine_mode}", ErrCode.PARA_ERROR)

    def do_combine(self, zs2: 'CZS'):
        """执行实际合并操作"""
        if len(self.sub_zs_lst) == 0:  # 首次合并时保存自身副本
            self.__sub_zs_lst.append(self.make_copy())
        self.__sub_zs_lst.append(zs2)  # 添加被合并中枢

        # 更新区间和极值
        self.__low = min([self.low, zs2.low])
        self.__high = max([self.high, zs2.high])
        self.__peak_low = min([self.peak_low, zs2.peak_low])
        self.__peak_high = max([self.peak_high, zs2.peak_high])
        
        # 更新结束信息
        self.__end = zs2.end
        self.__bi_out = zs2.bi_out
        self.__end_bi = zs2.end_bi
        self.clean_cache()

    def try_add_to_end(self, item):
        """尝试将新笔加入当前中枢"""
        if not self.in_range(item):  # 检查价格重叠
            return False
        if self.is_one_bi_zs():  # 单笔中枢特殊处理
            self.update_zs_range([self.begin_bi, item])
        self.update_zs_end(item)  # 更新结束信息
        return True

    def in_range(self, item):
        """判断笔是否与中枢有价格重叠"""
        return has_overlap(self.low, self.high, item._low(), item._high())

    def is_inside(self, seg: CSeg):
        """判断中枢是否在线段范围内"""
        return seg.start_bi.idx <= self.begin_bi.idx <= seg.end_bi.idx

    def is_divergence(self, config: CPointConfig, out_bi=None):
        """背驰判断（核心方法）"""
        if not self.end_bi_break(out_bi):  # 末端笔必须突破中枢
            return False, None
        # 计算进出笔的MACD指标
        in_metric = self.get_bi_in().cal_macd_metric(config.macd_algo, is_reverse=False)
        out_metric = self.get_bi_out().cal_macd_metric(config.macd_algo, is_reverse=True) if out_bi is None else out_bi.cal_macd_metric(config.macd_algo, is_reverse=True)
        
        # 特殊保送逻辑
        if config.divergence_rate > 100:
            return True, out_metric/in_metric
        else:
            return out_metric <= config.divergence_rate*in_metric, out_metric/in_metric

    def init_from_zs(self, zs: 'CZS'):
        """从已有中枢复制数据（用于创建副本）"""
        self.__begin = zs.begin
        self.__end = zs.end
        self.__low = zs.low
        self.__high = zs.high
        self.__peak_high = zs.peak_high
        self.__peak_low = zs.peak_low
        self.__begin_bi = zs.begin_bi
        self.__end_bi = zs.end_bi
        self.__bi_in = zs.bi_in
        self.__bi_out = zs.bi_out

    def make_copy(self) -> 'CZS':
        """创建当前中枢的深拷贝"""
        copy = CZS(lst=None, is_sure=self.is_sure)
        copy.init_from_zs(zs=self)
        return copy

    def end_bi_break(self, end_bi=None) -> bool:
        """判断结束笔是否突破中枢范围"""
        if end_bi is None:
            end_bi = self.get_bi_out()
        assert end_bi is not None
        return (end_bi.is_down() and end_bi._low() < self.low) or (end_bi.is_up() and end_bi._high() > self.high)

    def out_bi_is_peak(self, end_bi_idx: int):
        """判断出中枢笔是否为区间极值"""
        assert len(self.bi_lst) > 0
        if self.bi_out is None:
            return False, None
        peak_rate = float("inf")
        # 遍历所有笔寻找最近极值
        for bi in self.bi_lst:
            if bi.idx > end_bi_idx:
                break
            if (self.bi_out.is_down() and bi._low() < self.bi_out._low()) or (self.bi_out.is_up() and bi._high() > self.bi_out._high()):
                return False, None
            # 计算价格差异率
            r = abs(bi.get_end_val()-self.bi_out.get_end_val())/self.bi_out.get_end_val()
            if r < peak_rate:
                peak_rate = r
        return True, peak_rate

    def get_bi_in(self) -> LINE_TYPE:
        """获取进入中枢的笔（必须存在）"""
        assert self.bi_in is not None
        return self.bi_in

    def get_bi_out(self) -> LINE_TYPE:
        """获取离开中枢的笔（必须存在）"""
        assert self.__bi_out is not None
        return self.__bi_out

    def set_bi_in(self, bi):
        """设置进入中枢的笔（维护缓存）"""
        self.__bi_in = bi
        self.clean_cache()

    def set_bi_out(self, bi):
        """设置离开中枢的笔（维护缓存）"""
        self.__bi_out = bi
        self.clean_cache()

    def set_bi_lst(self, bi_lst):
        """设置中枢包含的笔列表（维护缓存）"""
        self.__bi_lst = bi_lst
        self.clean_cache()