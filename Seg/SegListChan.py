from Bi.BiList import CBiList
from Common.CEnum import BI_DIR, SEG_TYPE

from .EigenFX import CEigenFX
from .SegConfig import CSegConfig
from .SegListComm import CSegListComm


class CSegListChan(CSegListComm):
    """缠论线段列表处理核心类，继承自线段列表通用基类"""
    
    def __init__(self, seg_config=CSegConfig(), lv=SEG_TYPE.BI):
        """初始化线段列表"""
        super(CSegListChan, self).__init__(seg_config=seg_config, lv=lv)

    def do_init(self):
        """初始化处理：清除未确认线段和无效分型"""
        # 删除末尾不确定的线段（防止未完成线段影响后续计算）
        while len(self) and not self.lst[-1].is_sure:
            _seg = self[-1]
            # 解除笔与线段的关联
            for bi in _seg.bi_list:
                bi.parent_seg = None
            # 维护双向链表关系
            if _seg.pre:
                _seg.pre.next = None
            self.lst.pop()
        # 处理分型元素不确定的情况
        if len(self):
            assert self.lst[-1].eigen_fx and self.lst[-1].eigen_fx.ele[-1]
            if not self.lst[-1].eigen_fx.ele[-1].lst[-1].is_sure:
                # 当分型第三元素包含未确认笔时，移除该线段
                self.lst.pop()

    def update(self, bi_lst: CBiList):
        """更新线段列表主入口"""
        self.do_init()  # 执行初始化清理
        # 根据当前线段状态选择起始分析位置
        if len(self) == 0:
            self.cal_seg_sure(bi_lst, begin_idx=0)
        else:
            self.cal_seg_sure(bi_lst, begin_idx=self[-1].end_bi.idx+1)
        self.collect_left_seg(bi_lst)  # 收集剩余未处理线段

    def cal_seg_sure(self, bi_lst: CBiList, begin_idx: int):
        """核心方法：计算确认线段"""
        # 初始化特征序列分析器
        up_eigen = CEigenFX(BI_DIR.UP, lv=self.lv)  # 上升线段需要处理下降笔序列
        down_eigen = CEigenFX(BI_DIR.DOWN, lv=self.lv)  # 下降线段需要处理上升笔序列
        last_seg_dir = None if len(self) == 0 else self[-1].dir  # 最后确认线段方向
        
        # 遍历指定起始位置后的所有笔
        for bi in bi_lst[begin_idx:]:
            fx_eigen = None  # 当前检测到的有效分型
            # 根据笔方向和线段方向过滤处理
            if bi.is_down() and last_seg_dir != BI_DIR.UP:
                if up_eigen.add(bi):  # 向上升特征序列添加下降笔
                    fx_eigen = up_eigen
            elif bi.is_up() and last_seg_dir != BI_DIR.DOWN:
                if down_eigen.add(bi):  # 向下降特征序列添加上升笔
                    fx_eigen = down_eigen
            
            # 处理首线段方向确定问题（防误判逻辑）
            if len(self) == 0:
                if up_eigen.ele[1] is not None and bi.is_down():
                    last_seg_dir = BI_DIR.DOWN  # 临时指定方向为下
                    down_eigen.clear()
                elif down_eigen.ele[1] is not None and bi.is_up():
                    last_seg_dir = BI_DIR.UP    # 临时指定方向为上
                    up_eigen.clear()
                # 方向误判恢复机制
                if up_eigen.ele[1] is None and last_seg_dir == BI_DIR.DOWN and bi.dir == BI_DIR.DOWN:
                    last_seg_dir = None
                elif down_eigen.ele[1] is None and last_seg_dir == BI_DIR.UP and bi.dir == BI_DIR.UP:
                    last_seg_dir = None
            
            # 发现有效分型后处理
            if fx_eigen:
                self.treat_fx_eigen(fx_eigen, bi_lst)
                break

    def treat_fx_eigen(self, fx_eigen, bi_lst: CBiList):
        """处理检测到的分型特征"""
        _test = fx_eigen.can_be_end(bi_lst)  # 验证分型有效性
        end_bi_idx = fx_eigen.GetPeakBiIdx()  # 获取分型顶点对应笔索引
        
        if _test in [True, None]:  # 有效分型或无反向分型
            is_true = _test is not None  # 是否确认分型
            # 添加新线段（处理首线段方向异常情况）
            if not self.add_new_seg(bi_lst, end_bi_idx, is_sure=is_true and fx_eigen.all_bi_is_sure()):
                self.cal_seg_sure(bi_lst, end_bi_idx+1)
                return
            # 关联分型特征并继续后续分析
            self.lst[-1].eigen_fx = fx_eigen
            if is_true:
                self.cal_seg_sure(bi_lst, end_bi_idx + 1)
        else:  # 无效分型，重新从第二元素开始分析
            self.cal_seg_sure(bi_lst, fx_eigen.lst[1].idx)