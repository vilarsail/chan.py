from typing import Self

from Bi.Bi import CBi
from Combiner.KLine_Combiner import CKLine_Combiner
from Common.CEnum import BI_DIR, FX_TYPE


class CEigen(CKLine_Combiner[CBi]):
    """特征元素类，继承自K线组合器，用于线段特征序列分析"""

    def __init__(self, bi, _dir):
        """
        Args:
            bi: 构成特征元素的笔对象
            _dir: 特征序列方向（向上/向下）
        """
        super(CEigen, self).__init__(bi, _dir)
        self.gap = False  # 是否包含缺口标记

    def update_fx(self, _pre: Self, _next: Self, exclude_included=False, allow_top_equal=None):
        """
        更新分型信息并检测缺口
        Args:
            _pre: 前一个特征元素
            _next: 后一个特征元素
            exclude_included: 是否排除包含关系
            allow_top_equal: 是否允许顶分型高点相等
        """
        super(CEigen, self).update_fx(_pre, _next, exclude_included, allow_top_equal)
        # 缺口判断逻辑：当前分型与前一个特征元素无价格重叠
        if (self.fx == FX_TYPE.TOP and _pre.high < self.low) or \
                (self.fx == FX_TYPE.BOTTOM and _pre.low > self.high):
            self.gap = True

    def __str__(self):
        """字符串表示：起止索引+缺口状态+分型类型"""
        return f"{self.lst[0].idx}~{self.lst[-1].idx} gap={self.gap} fx={self.fx}"

    def GetPeakBiIdx(self):
        """
        获取特征元素峰值对应的笔索引
        Returns:
            对应笔的索引号（调整后的位置）
        """
        assert self.fx != FX_TYPE.UNKNOWN
        bi_dir = self.lst[0].dir  # 获取首笔方向
        if bi_dir == BI_DIR.UP:  # 上升笔构成下降特征序列
            return self.get_peak_klu(is_high=False).idx - 1  # 取低点索引
        else:  # 下降笔构成上升特征序列
            return self.get_peak_klu(is_high=True).idx - 1  # 取高点索引