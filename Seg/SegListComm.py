import abc
from typing import Generic, List, TypeVar, Union, overload

from Bi.Bi import CBi
from Bi.BiList import CBiList
from Common.CEnum import BI_DIR, LEFT_SEG_METHOD, SEG_TYPE
from Common.ChanException import CChanException, ErrCode

from .Seg import CSeg
from .SegConfig import CSegConfig

# 定义泛型类型，支持笔或线段作为基础单元
SUB_LINE_TYPE = TypeVar('SUB_LINE_TYPE', CBi, "CSeg")


class CSegListComm(Generic[SUB_LINE_TYPE]):
    """线段列表通用基类，提供线段管理基础功能"""
    
    def __init__(self, seg_config=CSegConfig(), lv=SEG_TYPE.BI):
        """初始化线段列表"""
        self.lst: List[CSeg[SUB_LINE_TYPE]] = []  # 线段存储容器
        self.lv = lv          # 分析级别（笔/线段）
        self.do_init()        # 执行初始化
        self.config = seg_config  # 线段配置参数

    def do_init(self):
        """清空线段列表"""
        self.lst = []

    def __iter__(self):
        """迭代器支持"""
        yield from self.lst

    @overload
    def __getitem__(self, index: int) -> CSeg[SUB_LINE_TYPE]: ...

    @overload
    def __getitem__(self, index: slice) -> List[CSeg[SUB_LINE_TYPE]]: ...

    def __getitem__(self, index: Union[slice, int]) -> Union[List[CSeg[SUB_LINE_TYPE]], CSeg[SUB_LINE_TYPE]]:
        """索引访问支持"""
        return self.lst[index]

    def __len__(self):
        """获取线段数量"""
        return len(self.lst)

    def left_bi_break(self, bi_lst: CBiList):
        """
        检测剩余笔是否突破最后确认线段
        Returns:
            bool: 是否有笔突破最后线段的极值
        """
        if len(self) == 0:
            return False
        last_seg_end_bi = self[-1].end_bi  # 最后线段的结束笔
        # 遍历后续笔检查突破情况
        for bi in bi_lst[last_seg_end_bi.idx+1:]:
            if last_seg_end_bi.is_up() and bi._high() > last_seg_end_bi._high():
                return True
            elif last_seg_end_bi.is_down() and bi._low() < last_seg_end_bi._low():
                return True
        return False

    def collect_first_seg(self, bi_lst: CBiList):
        """收集初始线段（处理首线段特殊情况）"""
        if len(bi_lst) < 3:
            return
        if self.config.left_method == LEFT_SEG_METHOD.PEAK:
            # 峰值法：找到最大波动方向创建初始线段
            _high = max(bi._high() for bi in bi_lst)
            _low = min(bi._low() for bi in bi_lst)
            # 比较高低点波动幅度决定初始方向
            if abs(_high-bi_lst[0].get_begin_val()) >= abs(_low-bi_lst[0].get_begin_val()):
                peak_bi = FindPeakBi(bi_lst, is_high=True)
                assert peak_bi is not None
                self.add_new_seg(bi_lst, peak_bi.idx, is_sure=False, seg_dir=BI_DIR.UP, split_first_seg=False, reason="0seg_find_high")
            else:
                peak_bi = FindPeakBi(bi_lst, is_high=False)
                assert peak_bi is not None
                self.add_new_seg(bi_lst, peak_bi.idx, is_sure=False, seg_dir=BI_DIR.DOWN, split_first_seg=False, reason="0seg_find_low")
            self.collect_left_as_seg(bi_lst)
        elif self.config.left_method == LEFT_SEG_METHOD.ALL:
            # 全包含法：根据整体趋势方向创建初始线段
            _dir = BI_DIR.UP if bi_lst[-1].get_end_val() >= bi_lst[0].get_begin_val() else BI_DIR.DOWN
            self.add_new_seg(bi_lst, bi_lst[-1].idx, is_sure=False, seg_dir=_dir, split_first_seg=False, reason="0seg_collect_all")
        else:
            raise CChanException(f"unknown seg left_method = {self.config.left_method}", ErrCode.PARA_ERROR)

    def collect_left_seg_peak_method(self, last_seg_end_bi, bi_lst):
        """使用峰值法收集剩余线段"""
        if last_seg_end_bi.is_down():
            # 下降线段后寻找上升峰值
            peak_bi = FindPeakBi(bi_lst[last_seg_end_bi.idx+3:], is_high=True)
            if peak_bi and peak_bi.idx - last_seg_end_bi.idx >= 3:
                self.add_new_seg(bi_lst, peak_bi.idx, is_sure=False, seg_dir=BI_DIR.UP, reason="collectleft_find_high")
        else:
            # 上升线段后寻找下降峰值
            peak_bi = FindPeakBi(bi_lst[last_seg_end_bi.idx+3:], is_high=False)
            if peak_bi and peak_bi.idx - last_seg_end_bi.idx >= 3:
                self.add_new_seg(bi_lst, peak_bi.idx, is_sure=False, seg_dir=BI_DIR.DOWN, reason="collectleft_find_low")
        last_seg_end_bi = self[-1].end_bi
        self.collect_left_as_seg(bi_lst)

    def collect_segs(self, bi_lst):
        """收集剩余线段主逻辑"""
        last_bi = bi_lst[-1]
        last_seg_end_bi = self[-1].end_bi
        if last_bi.idx-last_seg_end_bi.idx < 3:
            return
        # 根据最后线段方向强制寻找反向峰值
        if last_seg_end_bi.is_down() and last_bi.get_end_val() <= last_seg_end_bi.get_end_val():
            if peak_bi := FindPeakBi(bi_lst[last_seg_end_bi.idx+3:], is_high=True):
                self.add_new_seg(bi_lst, peak_bi.idx, is_sure=False, seg_dir=BI_DIR.UP, reason="collectleft_find_high_force")
                self.collect_left_seg(bi_lst)
        elif last_seg_end_bi.is_up() and last_bi.get_end_val() >= last_seg_end_bi.get_end_val():
            if peak_bi := FindPeakBi(bi_lst[last_seg_end_bi.idx+3:], is_high=False):
                self.add_new_seg(bi_lst, peak_bi.idx, is_sure=False, seg_dir=BI_DIR.DOWN, reason="collectleft_find_low_force")
                self.collect_left_seg(bi_lst)
        # 根据配置选择不同收集策略
        elif self.config.left_method == LEFT_SEG_METHOD.ALL:
            self.collect_left_as_seg(bi_lst)
        elif self.config.left_method == LEFT_SEG_METHOD.PEAK:
            self.collect_left_seg_peak_method(last_seg_end_bi, bi_lst)
        else:
            raise CChanException(f"unknown seg left_method = {self.config.left_method}", ErrCode.PARA_ERROR)

    def collect_left_seg(self, bi_lst: CBiList):
        """收集剩余线段入口"""
        if len(self) == 0:
            self.collect_first_seg(bi_lst)
        else:
            self.collect_segs(bi_lst)

    def collect_left_as_seg(self, bi_lst: CBiList):
        """直接收集剩余笔为线段"""
        last_bi = bi_lst[-1]
        last_seg_end_bi = self[-1].end_bi
        if last_seg_end_bi.idx+1 >= len(bi_lst):
            return
        # 根据笔方向差异调整结束位置
        if last_seg_end_bi.dir == last_bi.dir:
            self.add_new_seg(bi_lst, last_bi.idx-1, is_sure=False, reason="collect_left_1")
        else:
            self.add_new_seg(bi_lst, last_bi.idx, is_sure=False, reason="collect_left_0")

    def try_add_new_seg(self, bi_lst, end_bi_idx: int, is_sure=True, seg_dir=None, split_first_seg=True, reason="normal"):
        """尝试添加新线段（核心方法）"""
        # 处理首线段分割逻辑
        if len(self) == 0 and split_first_seg and end_bi_idx >= 3:
            if peak_bi := FindPeakBi(bi_lst[end_bi_idx-3::-1], bi_lst[end_bi_idx].is_down()):
                # 验证峰值有效性后分割首线段
                if (peak_bi.is_down() and (peak_bi._low() < bi_lst[0]._low() or peak_bi.idx == 0)) or \
                   (peak_bi.is_up() and (peak_bi._high() > bi_lst[0]._high() or peak_bi.idx == 0)):
                    self.add_new_seg(bi_lst, peak_bi.idx, is_sure=False, seg_dir=peak_bi.dir, reason="split_first_1st")
                    self.add_new_seg(bi_lst, end_bi_idx, is_sure=False, reason="split_first_2nd")
                    return
        # 计算新线段起止位置
        bi1_idx = 0 if len(self) == 0 else self[-1].end_bi.idx+1
        bi1 = bi_lst[bi1_idx]
        bi2 = bi_lst[end_bi_idx]
        # 创建新线段对象
        self.lst.append(CSeg(len(self.lst), bi1, bi2, is_sure=is_sure, seg_dir=seg_dir, reason=reason))
        # 维护双向链表关系
        if len(self.lst) >= 2:
            self.lst[-2].next = self.lst[-1]
            self.lst[-1].pre = self.lst[-2]
        # 更新线段包含的笔列表
        self.lst[-1].update_bi_list(bi_lst, bi1_idx, end_bi_idx)

    def add_new_seg(self, bi_lst: CBiList, end_bi_idx: int, is_sure=True, seg_dir=None, split_first_seg=True, reason="normal"):
        """添加新线段（含异常处理）"""
        try:
            self.try_add_new_seg(bi_lst, end_bi_idx, is_sure, seg_dir, split_first_seg, reason)
        except CChanException as e:
            if e.errcode == ErrCode.SEG_END_VALUE_ERR and len(self.lst) == 0:
                return False
            raise e
        except Exception as e:
            raise e
        return True

    @abc.abstractmethod
    def update(self, bi_lst: CBiList):
        """抽象方法：子类需实现线段更新逻辑"""
        ...

    def exist_sure_seg(self):
        """检查是否存在确认线段"""
        return any(seg.is_sure for seg in self.lst)


def FindPeakBi(bi_lst: Union[CBiList, List[CBi]], is_high):
    """
    寻找指定方向的峰值笔
    Args:
        is_high: True找最高点，False找最低点
    Returns:
        CBi: 符合条件的笔对象
    """
    peak_val = float("-inf") if is_high else float("inf")
    peak_bi = None
    for bi in bi_lst:
        # 根据方向筛选候选笔
        if (is_high and bi.get_end_val() >= peak_val and bi.is_up()) or (not is_high and bi.get_end_val() <= peak_val and bi.is_down()):
            # 排除中间波动干扰
            if bi.pre and bi.pre.pre and ((is_high and bi.pre.pre.get_end_val() > bi.get_end_val()) or (not is_high and bi.pre.pre.get_end_val() < bi.get_end_val())):
                continue
            peak_val = bi.get_end_val()
            peak_bi = bi
    return peak_bi