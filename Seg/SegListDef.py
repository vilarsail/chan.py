from Bi.BiList import CBiList
from Common.CEnum import SEG_TYPE

from .SegConfig import CSegConfig
from .SegListComm import CSegListComm


def is_up_seg(bi, pre_bi):
    """判断是否构成上升线段：当前笔高点超过前前笔高点"""
    return bi._high() > pre_bi._high()


def is_down_seg(bi, pre_bi):
    """判断是否构成下降线段：当前笔低点低于前前笔低点"""
    return bi._low() < pre_bi._low()


class CSegListDef(CSegListComm):
    """默认线段列表处理类，基于经典笔段划分规则"""
    
    def __init__(self, seg_config=CSegConfig(), lv=SEG_TYPE.BI):
        """初始化线段列表"""
        super(CSegListDef, self).__init__(seg_config=seg_config, lv=lv)
        self.sure_seg_update_end = False  # 是否允许更新已确认线段端点

    def update(self, bi_lst: CBiList):
        """更新线段列表主入口"""
        self.do_init()  # 清空临时数据
        self.cal_bi_sure(bi_lst)  # 计算确认线段
        self.collect_left_seg(bi_lst)  # 收集剩余未处理线段

    def update_last_end(self, bi_lst, new_endbi_idx: int):
        """更新最后线段的结束笔"""
        last_endbi_idx = self[-1].end_bi.idx
        assert new_endbi_idx >= last_endbi_idx + 2  # 确保新笔至少间隔两笔
        self[-1].end_bi = bi_lst[new_endbi_idx]  # 更新结束笔
        self.lst[-1].update_bi_list(bi_lst, last_endbi_idx, new_endbi_idx)  # 更新包含笔列表

    def cal_bi_sure(self, bi_lst):
        """核心方法：遍历笔列表识别确认线段"""
        peak_bi = None  # 当前候选峰值笔
        if len(bi_lst) == 0:
            return
        for idx, bi in enumerate(bi_lst):
            if idx < 2:  # 至少需要3笔才能形成线段
                continue
            # 延续当前峰值笔的情况
            if peak_bi and ((bi.is_up() and peak_bi.is_up() and bi._high() >= peak_bi._high()) or (bi.is_down() and peak_bi.is_down() and bi._low() <= peak_bi._low())):
                peak_bi = bi  # 更新峰值笔
                continue
            # 允许更新已确认线段端点的情况
            if self.sure_seg_update_end and len(self) and bi.dir == self[-1].dir and ((bi.is_up() and bi._high() >= self[-1].end_bi._high()) or (bi.is_down() and bi._low() <= self[-1].end_bi._low())):
                self.update_last_end(bi_lst, bi.idx)
                peak_bi = None
                continue
            # 检查是否满足线段形成条件
            pre_bi = bi_lst[idx-2]
            if (bi.is_up() and is_up_seg(bi, pre_bi)) or (bi.is_down() and is_down_seg(bi, pre_bi)):
                if peak_bi is None:  # 发现新线段起点
                    if len(self) == 0 or bi.dir != self[-1].dir:  # 首线段或方向变化
                        peak_bi = bi
                        continue
                elif peak_bi.dir != bi.dir:  # 方向发生改变
                    if bi.idx - peak_bi.idx <= 2:  # 间隔不足两笔跳过
                        continue
                    self.add_new_seg(bi_lst, peak_bi.idx)  # 添加新线段
                    peak_bi = bi
                    continue
        # 处理最后的候选峰值笔
        if peak_bi is not None:
            self.add_new_seg(bi_lst, peak_bi.idx, is_sure=False)  # 添加未确认线段