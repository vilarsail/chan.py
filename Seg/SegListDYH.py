from Bi.BiList import CBiList
from Common.CEnum import BI_DIR, SEG_TYPE

from .SegConfig import CSegConfig
from .SegListComm import CSegListComm


def situation1(cur_bi, next_bi, pre_bi):
    """情况1判断：当前笔未突破前前笔，但后续笔形成有效回调"""
    if cur_bi.is_down() and cur_bi._low() > pre_bi._low():
        if next_bi._high() < cur_bi._high() and next_bi._low() < cur_bi._low():
            return True
    elif cur_bi.is_up() and cur_bi._high() < pre_bi._high():
        if next_bi._low() > cur_bi._low() and next_bi._high() > cur_bi._high():
            return True
    return False


def situation2(cur_bi, next_bi, pre_bi):
    """情况2判断：当前笔突破前前笔，但后续笔延续突破方向"""
    if cur_bi.is_down() and cur_bi._low() < pre_bi._low():
        if next_bi._high() < cur_bi._high() and next_bi._low() < pre_bi._low():
            return True
    elif cur_bi.is_up() and cur_bi._high() > pre_bi._high():
        if next_bi._low() > cur_bi._low() and next_bi._high() > pre_bi._high():
            return True
    return False


class CSegListDYH(CSegListComm):
    """DYH线段处理类，实现动态演化线段算法"""
    
    def __init__(self, seg_config=CSegConfig(), lv=SEG_TYPE.BI):
        """初始化配置参数"""
        super(CSegListDYH, self).__init__(seg_config=seg_config, lv=lv)
        self.sure_seg_update_end = False  # 是否允许更新已确认线段端点

    def update(self, bi_lst: CBiList):
        """主更新入口：执行完整线段分析流程"""
        self.do_init()  # 初始化清理
        self.cal_bi_sure(bi_lst)  # 计算确认线段
        self.try_update_last_seg(bi_lst)  # 尝试更新最后线段
        if self.left_bi_break(bi_lst):  # 检测剩余笔突破
            self.cal_bi_unsure(bi_lst)  # 计算未确认线段
        self.collect_left_seg(bi_lst)  # 收集剩余线段

    def cal_bi_sure(self, bi_lst):
        """核心方法：遍历笔列表识别确认线段"""
        BI_LEN = len(bi_lst)
        next_begin_bi = bi_lst[0]  # 下一线段起始笔跟踪
        for idx, bi in enumerate(bi_lst):
            # 跳过不足形成线段的情况
            if idx + 2 >= BI_LEN or idx < 2:
                continue
            # 方向过滤：只处理与最后线段同方向的笔
            if len(self) > 0 and bi.dir != self[-1].end_bi.dir:
                continue
            # 排除中间波动干扰（针对下降/上升趋势）
            if bi.is_down() and bi_lst[idx-1]._high() < next_begin_bi._low():
                continue
            if bi.is_up() and bi_lst[idx-1]._low() > next_begin_bi._high():
                continue
            # 允许更新已确认线段端点的情况处理
            if self.sure_seg_update_end and len(self) and ((bi.is_down() and bi._low() < self[-1].end_bi._low()) or (bi.is_up() and bi._high() > self[-1].end_bi._high())):
                self[-1].end_bi = bi  # 更新线段结束笔
                if idx != BI_LEN-1:
                    next_begin_bi = bi_lst[idx+1]
                    continue
            # 满足线段形成条件（间隔4笔以上且符合特定形态）
            if (len(self) == 0 or bi.idx - self[-1].end_bi.idx >= 4) and (situation1(bi, bi_lst[idx + 2], bi_lst[idx - 2]) or situation2(bi, bi_lst[idx + 2], bi_lst[idx - 2])):
                self.add_new_seg(bi_lst, idx-1)  # 添加新线段
                next_begin_bi = bi  # 重置起始跟踪笔

    def cal_bi_unsure(self, bi_lst: CBiList):
        """计算未确认线段：在突破后寻找反向极点"""
        if len(self) == 0:
            return
        last_seg_dir = self[-1].end_bi.dir  # 最后线段方向
        end_bi = None
        peak_value = float("inf") if last_seg_dir == BI_DIR.UP else float("-inf")  # 极值初始化
        # 遍历后续笔寻找反向极点
        for bi in bi_lst[self[-1].end_bi.idx+3:]:
            if bi.dir == last_seg_dir:  # 过滤同方向笔
                continue
            cur_value = bi._low() if last_seg_dir == BI_DIR.UP else bi._high()
            # 更新极值笔
            if (last_seg_dir == BI_DIR.UP and cur_value < peak_value) or \
               (last_seg_dir == BI_DIR.DOWN and cur_value > peak_value):
                end_bi = bi
                peak_value = cur_value
        if end_bi:
            self.add_new_seg(bi_lst, end_bi.idx, is_sure=False)  # 添加未确认线段

    def try_update_last_seg(self, bi_lst: CBiList):
        """尝试更新最后线段：寻找同方向更优端点"""
        if len(self) == 0:
            return
        last_bi = self[-1].end_bi
        peak_value = last_bi.get_end_val()  # 当前端点值
        new_peak_bi = None
        # 遍历后续同方向笔寻找更优极值
        for bi in bi_lst[self[-1].end_bi.idx+1:]:
            if bi.dir != last_bi.dir:
                continue
            # 更新下降线段低点/上升线段高点
            if bi.is_down() and bi._low() < peak_value:
                peak_value = bi._low()
                new_peak_bi = bi
            elif bi.is_up() and bi._high() > peak_value:
                peak_value = bi._high()
                new_peak_bi = bi
        # 发现更优端点则更新线段
        if new_peak_bi:
            self[-1].end_bi = new_peak_bi
            self[-1].is_sure = False  # 标记为未确认状态