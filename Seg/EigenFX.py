from typing import List, Optional

from Bi.Bi import CBi
from Bi.BiList import CBiList
from Common.CEnum import BI_DIR, FX_TYPE, KLINE_DIR, SEG_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.func_util import revert_bi_dir

from .Eigen import CEigen


class CEigenFX:
    """线段特征分型检测器，用于在特征序列中寻找分型结构"""

    def __init__(self, _dir: BI_DIR, exclude_included=True, lv=SEG_TYPE.BI):
        """
        Args:
            _dir: 线段方向（决定特征序列处理方向）
            exclude_included: 是否排除包含关系（默认True）
            lv: 分析级别（笔/线段级别）
        """
        self.lv = lv  # 分析级别
        self.dir = _dir  # 线段方向（决定分型类型）
        self.ele: List[Optional[CEigen]] = [None, None, None]  # 特征序列三元素
        self.lst: List[CBi] = []  # 已处理的笔列表
        self.exclude_included = exclude_included  # 包含关系处理开关
        self.kl_dir = KLINE_DIR.UP if _dir == BI_DIR.UP else KLINE_DIR.DOWN  # 特征序列K线方向
        self.last_evidence_bi: Optional[CBi] = None  # 最后确认分型的有效笔

    def treat_first_ele(self, bi: CBi) -> bool:
        """处理第一个特征元素"""
        self.ele[0] = CEigen(bi, self.kl_dir)
        return False  # 未形成分型

    def treat_second_ele(self, bi: CBi) -> bool:
        """处理第二个特征元素"""
        assert self.ele[0] is not None
        combine_dir = self.ele[0].try_add(bi, exclude_included=self.exclude_included)
        if combine_dir != KLINE_DIR.COMBINE:  # 无法合并时创建新元素
            self.ele[1] = CEigen(bi, self.kl_dir)
            # 检查前两元素是否可能形成分型
            if (self.is_up() and self.ele[1].high < self.ele[0].high) or \
                    (self.is_down() and self.ele[1].low > self.ele[0].low):
                return self.reset()  # 重置并重新处理
        return False

    def treat_third_ele(self, bi: CBi) -> bool:
        """处理第三个特征元素"""
        assert self.ele[0] is not None
        assert self.ele[1] is not None
        self.last_evidence_bi = bi
        allow_top_equal = (1 if bi.is_down() else -1) if self.exclude_included else None
        combine_dir = self.ele[1].try_add(bi, allow_top_equal=allow_top_equal)
        if combine_dir == KLINE_DIR.COMBINE:
            return False  # 合并后仍需等待更多元素

        self.ele[2] = CEigen(bi, combine_dir)
        if not self.actual_break():  # 验证实际突破
            return self.reset()

        # 更新分型信息并验证有效性
        self.ele[1].update_fx(self.ele[0], self.ele[2], exclude_included=self.exclude_included,
                              allow_top_equal=allow_top_equal)
        fx = self.ele[1].fx
        is_fx = (self.is_up() and fx == FX_TYPE.TOP) or (self.is_down() and fx == FX_TYPE.BOTTOM)
        return True if is_fx else self.reset()

    def add(self, bi: CBi) -> bool:
        """添加笔并处理特征序列，返回是否形成有效分型"""
        assert bi.dir != self.dir  # 确保笔方向与线段方向相反
        self.lst.append(bi)
        # 分阶段处理特征元素
        if self.ele[0] is None:
            return self.treat_first_ele(bi)
        elif self.ele[1] is None:
            return self.treat_second_ele(bi)
        elif self.ele[2] is None:
            return self.treat_third_ele(bi)
        else:
            raise CChanException(f"特征序列处理异常! 当前笔:{bi.idx},当前:{str(self)}", ErrCode.SEG_EIGEN_ERR)

    def reset(self):
        """重置特征序列处理状态"""
        bi_tmp_list = list(self.lst[1:])  # 保留后续笔重新处理
        if self.exclude_included:
            self.clear()
            for bi in bi_tmp_list:
                if self.add(bi):
                    return True
        else:
            assert self.ele[1] is not None
            ele2_begin_idx = self.ele[1].lst[0].idx
            # 滑动窗口保留有效元素
            self.ele[0], self.ele[1], self.ele[2] = self.ele[1], self.ele[2], None
            self.lst = [bi for bi in bi_tmp_list if bi.idx >= ele2_begin_idx]
        return False

    def can_be_end(self, bi_lst: CBiList):
        """验证分型能否作为线段终点"""
        assert self.ele[1] is not None
        if self.ele[1].gap:  # 存在缺口时需要额外验证
            assert self.ele[0] is not None
            end_bi_idx = self.GetPeakBiIdx()
            thred_value = bi_lst[end_bi_idx].get_end_val()
            break_thred = self.ele[0].low if self.is_up() else self.ele[0].high
            return self.find_revert_fx(bi_lst, end_bi_idx + 2, thred_value, break_thred)
        else:
            return True  # 无缺口直接有效

    def is_down(self):
        """是否向下线段"""
        return self.dir == BI_DIR.DOWN

    def is_up(self):
        """是否向上线段"""
        return self.dir == BI_DIR.UP

    def GetPeakBiIdx(self):
        """获取分型顶点对应的笔索引"""
        assert self.ele[1] is not None
        return self.ele[1].GetPeakBiIdx()

    def all_bi_is_sure(self):
        """验证所有笔是否确认状态"""
        assert self.last_evidence_bi is not None
        return next((False for bi in self.lst if not bi.is_sure), self.last_evidence_bi.is_sure)

    def clear(self):
        """清空处理状态"""
        self.ele = [None, None, None]
        self.lst = []

    def __str__(self):
        """调试信息：显示三个特征元素包含的笔索引"""
        _t = [f"{[] if ele is None else ','.join([str(b.idx) for b in ele.lst])}" for ele in self.ele]
        return " | ".join(_t)

    def actual_break(self):
        """验证价格实际突破（防止包含关系导致的伪分型）"""
        if not self.exclude_included:
            return True
        assert self.ele[2] and self.ele[1]
        # 根据方向检查价格突破
        if (self.is_up() and self.ele[2].low < self.ele[1][-1]._low()) or \
                (self.is_down() and self.ele[2].high > self.ele[1][-1]._high()):
            return True
        # 检查后续笔的突破情况
        assert len(self.ele[2]) == 1
        ele2_bi = self.ele[2][0]
        if ele2_bi.next and ele2_bi.next.next:
            if ele2_bi.is_down() and ele2_bi.next.next._low() < ele2_bi._low():
                self.last_evidence_bi = ele2_bi.next.next
                return True
            elif ele2_bi.is_up() and ele2_bi.next.next._high() > ele2_bi._high():
                self.last_evidence_bi = ele2_bi.next.next
                return True
        return False

    def find_revert_fx(self, bi_list: CBiList, begin_idx: int, thred_value: float, break_thred: float):
        """递归查找反向分型确认线段结束"""
        COMMON_COMBINE = True  # 使用标准合并规则开关
        first_bi_dir = bi_list[begin_idx].dir
        egien_fx = CEigenFX(revert_bi_dir(first_bi_dir), exclude_included=not COMMON_COMBINE, lv=self.lv)
        # 遍历后续笔寻找反向分型
        for bi in bi_list[begin_idx::2]:
            if egien_fx.add(bi):
                if COMMON_COMBINE:
                    return True
                # 递归验证分型有效性
                while True:
                    _test = egien_fx.can_be_end(bi_list)
                    if _test in [True, None]:
                        self.last_evidence_bi = bi
                        return _test
                    elif not egien_fx.reset():
                        break
        return None