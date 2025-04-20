from typing import Generic, List, Optional, Self, TypeVar

from Bi.Bi import CBi
from Common.CEnum import BI_DIR, MACD_ALGO, TREND_LINE_SIDE
from Common.ChanException import CChanException, ErrCode
from KLine.KLine_Unit import CKLine_Unit
from Math.TrendLine import CTrendLine

from .EigenFX import CEigenFX

# 定义泛型类型，支持笔或线段作为基础单元
LINE_TYPE = TypeVar('LINE_TYPE', CBi, "CSeg")


class CSeg(Generic[LINE_TYPE]):
    """线段基础类，封装线段属性和分析方法"""

    def __init__(self, idx: int, start_bi: LINE_TYPE, end_bi: LINE_TYPE, is_sure=True, seg_dir=None, reason="normal"):
        """
        线段构造函数
        Args:
            idx: 线段唯一标识
            start_bi: 起始笔/线段
            end_bi: 结束笔/线段
            is_sure: 是否确认线段
            seg_dir: 指定线段方向（自动推断时传None）
            reason: 线段形成原因描述
        """
        # 验证起始单元方向一致性（非首笔时需要）
        assert start_bi.idx == 0 or start_bi.dir == end_bi.dir or not is_sure, f"{start_bi.idx} {end_bi.idx} {start_bi.dir} {end_bi.dir}"
        self.idx = idx
        self.start_bi = start_bi  # 线段起点单元
        self.end_bi = end_bi  # 线段终点单元
        self.is_sure = is_sure  # 是否确认
        self.dir = end_bi.dir if seg_dir is None else seg_dir  # 线段方向

        # 中枢相关属性
        from ZS.ZS import CZS
        self.zs_lst: List[CZS[LINE_TYPE]] = []  # 线段包含的中枢列表

        # 分型特征与层级关系
        self.eigen_fx: Optional[CEigenFX] = None  # 特征序列分型
        self.seg_idx = None  # 递归线段索引
        self.parent_seg: Optional[CSeg] = None  # 所属父线段
        self.pre: Optional[Self] = None  # 前驱线段
        self.next: Optional[Self] = None  # 后继线段

        # 买卖点关联
        from BuySellPoint.BS_Point import CBS_Point
        self.bsp: Optional[CBS_Point] = None  # 线段末端买卖点

        # 线段组成单元管理
        self.bi_list: List[LINE_TYPE] = []  # 包含的笔/线段列表
        self.reason = reason  # 线段形成原因
        # 趋势线指标
        self.support_trend_line = None  # 支撑趋势线
        self.resistance_trend_line = None  # 压力趋势线

        # 有效性校验
        if end_bi.idx - start_bi.idx < 2:
            self.is_sure = False
        self.check()

        self.ele_inside_is_sure = False  # 内部元素是否全部确认

    def set_seg_idx(self, idx):
        """设置递归线段索引"""
        self.seg_idx = idx

    def check(self):
        """线段有效性验证"""
        if not self.is_sure:
            return
        # 方向与价格关系验证
        if self.is_down():
            if self.start_bi.get_begin_val() < self.end_bi.get_end_val():
                raise CChanException(f"下降线段起始点应该高于结束点! idx={self.idx}", ErrCode.SEG_END_VALUE_ERR)
        elif self.start_bi.get_begin_val() > self.end_bi.get_end_val():
            raise CChanException(f"上升线段起始点应该低于结束点! idx={self.idx}", ErrCode.SEG_END_VALUE_ERR)
        # 最小长度验证
        if self.end_bi.idx - self.start_bi.idx < 2:
            raise CChanException(f"线段({self.start_bi.idx}-{self.end_bi.idx})长度不能小于2! idx={self.idx}",
                                 ErrCode.SEG_LEN_ERR)

    def __str__(self):
        """字符串表示：起止索引+方向+确认状态"""
        return f"{self.start_bi.idx}->{self.end_bi.idx}: {self.dir}  {self.is_sure}"

    def add_zs(self, zs):
        """添加中枢到列表前端（保持时序逆序）"""
        self.zs_lst = [zs] + self.zs_lst

    def cal_klu_slope(self):
        """计算线段在K线单元上的斜率"""
        assert self.end_bi.idx >= self.start_bi.idx
        return (self.get_end_val() - self.get_begin_val()) / (
                    self.get_end_klu().idx - self.get_begin_klu().idx) / self.get_begin_val()

    def cal_amp(self):
        """计算线段价格振幅"""
        return (self.get_end_val() - self.get_begin_val()) / self.get_begin_val()

    def cal_bi_cnt(self):
        """计算包含的基础单元数量"""
        return self.end_bi.idx - self.start_bi.idx + 1

    def clear_zs_lst(self):
        """清空中枢列表"""
        self.zs_lst = []

    def _low(self):
        """获取有效最低价（兼容方向）"""
        return self.end_bi.get_end_klu().low if self.is_down() else self.start_bi.get_begin_klu().low

    def _high(self):
        """获取有效最高价（兼容方向）"""
        return self.end_bi.get_end_klu().high if self.is_up() else self.start_bi.get_begin_klu().high

    def is_down(self):
        """判断是否下降线段"""
        return self.dir == BI_DIR.DOWN

    def is_up(self):
        """判断是否上升线段"""
        return self.dir == BI_DIR.UP

    def get_end_val(self):
        """获取线段结束价格"""
        return self.end_bi.get_end_val()

    def get_begin_val(self):
        """获取线段起始价格"""
        return self.start_bi.get_begin_val()

    def amp(self):
        """计算绝对振幅"""
        return abs(self.get_end_val() - self.get_begin_val())

    def get_end_klu(self) -> CKLine_Unit:
        """获取结束K线单元"""
        return self.end_bi.get_end_klu()

    def get_begin_klu(self) -> CKLine_Unit:
        """获取起始K线单元"""
        return self.start_bi.get_begin_klu()

    def get_klu_cnt(self):
        """获取包含的K线单元数量"""
        return self.get_end_klu().idx - self.get_begin_klu().idx + 1

    def cal_macd_metric(self, macd_algo, is_reverse):
        """
        计算MACD相关指标
        Args:
            macd_algo: 算法类型（斜率/振幅）
            is_reverse: 是否反转计算
        """
        if macd_algo == MACD_ALGO.SLOPE:
            return self.Cal_MACD_slope()
        elif macd_algo == MACD_ALGO.AMP:
            return self.Cal_MACD_amp()
        else:
            raise CChanException(f"不支持的MACD算法类型:{macd_algo}", ErrCode.PARA_ERROR)

    def Cal_MACD_slope(self):
        """斜率法计算MACD指标"""
        begin_klu = self.get_begin_klu()
        end_klu = self.get_end_klu()
        if self.is_up():
            return (end_klu.high - begin_klu.low) / end_klu.high / (end_klu.idx - begin_klu.idx + 1)
        else:
            return (begin_klu.high - end_klu.low) / begin_klu.high / (end_klu.idx - begin_klu.idx + 1)

    def Cal_MACD_amp(self):
        """振幅法计算MACD指标"""
        begin_klu = self.get_begin_klu()
        end_klu = self.get_end_klu()
        if self.is_down():
            return (begin_klu.high - end_klu.low) / begin_klu.high
        else:
            return (end_klu.high - begin_klu.low) / begin_klu.low

    def update_bi_list(self, bi_lst, idx1, idx2):
        """更新线段包含的笔列表并生成趋势线"""
        for bi_idx in range(idx1, idx2 + 1):
            bi_lst[bi_idx].parent_seg = self
            self.bi_list.append(bi_lst[bi_idx])
        # 生成支撑/压力趋势线
        if len(self.bi_list) >= 3:
            self.support_trend_line = CTrendLine(self.bi_list, TREND_LINE_SIDE.INSIDE)
            self.resistance_trend_line = CTrendLine(self.bi_list, TREND_LINE_SIDE.OUTSIDE)

    def get_first_multi_bi_zs(self):
        """获取首个多笔中枢"""
        return next((zs for zs in self.zs_lst if not zs.is_one_bi_zs()), None)

    def get_final_multi_bi_zs(self):
        """获取最后一个多笔中枢"""
        zs_idx = len(self.zs_lst) - 1
        while zs_idx >= 0:
            zs = self.zs_lst[zs_idx]
            if not zs.is_one_bi_zs():
                return zs
            zs_idx -= 1
        return None

    def get_multi_bi_zs_cnt(self):
        """统计多笔中枢数量"""
        return sum(not zs.is_one_bi_zs() for zs in self.zs_lst)