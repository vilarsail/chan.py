from typing import List, Union, overload

from Bi.Bi import CBi
from Bi.BiList import CBiList
from Common.func_util import revert_bi_dir
from Seg.Seg import CSeg
from Seg.SegListComm import CSegListComm
from ZS.ZSConfig import CZSConfig

from .ZS import CZS


class CZSList:
    """中枢列表管理类，负责中枢的生成、合并和更新"""
    
    def __init__(self, zs_config=CZSConfig()):
        self.zs_lst: List[CZS] = []  # 已确认的中枢列表
        self.config = zs_config      # 中枢配置参数
        self.free_item_lst = []      # 临时存储待处理笔的缓存列表
        self.last_sure_pos = -1      # 最后确认线段的起始笔索引
        self.last_seg_idx = 0        # 最后处理线段的索引位置

    def update_last_pos(self, seg_list: CSegListComm):
        """更新最后确认线段的位置信息"""
        self.last_sure_pos = -1
        self.last_seg_idx = 0
        _seg_idx = len(seg_list) - 1
        # 倒序遍历线段寻找最新确认线段
        while _seg_idx >= 0:
            seg = seg_list[_seg_idx]
            if seg.is_sure:
                self.last_sure_pos = seg.start_bi.idx
                self.last_seg_idx = seg.idx
                return
            _seg_idx -= 1

    def seg_need_cal(self, seg: CSeg):
        """判断是否需要处理当前线段"""
        return seg.start_bi.idx >= self.last_sure_pos

    def add_to_free_lst(self, item, is_sure, zs_algo):
        """将笔添加到临时列表并尝试构造中枢"""
        # 防止重复添加同一笔
        if len(self.free_item_lst) != 0 and item.idx == self.free_item_lst[-1].idx:
            self.free_item_lst = self.free_item_lst[:-1]
        self.free_item_lst.append(item)
        # 尝试构造中枢
        res = self.try_construct_zs(self.free_item_lst, is_sure, zs_algo)
        if res is not None and res.begin_bi.idx > 0:  # 跳过首笔构造的中枢
            self.zs_lst.append(res)
            self.clear_free_lst()
            self.try_combine()  # 触发合并检查

    def clear_free_lst(self):
        """清空临时笔列表"""
        self.free_item_lst = []

    def update(self, bi: CBi, is_sure=True):
        """更新中枢列表主方法"""
        # 尝试将笔添加到已有中枢
        if len(self.free_item_lst) == 0 and self.try_add_to_end(bi):
            self.try_combine()
            return
        # 无法合并时创建新中枢
        self.add_to_free_lst(bi, is_sure, "normal")

    def try_add_to_end(self, bi):
        """尝试将笔添加到最后一个中枢"""
        return False if len(self.zs_lst) == 0 else self[-1].try_add_to_end(bi)

    def add_zs_from_bi_range(self, seg_bi_lst: list, seg_dir, seg_is_sure):
        """从指定笔范围生成中枢"""
        deal_bi_cnt = 0
        for bi in seg_bi_lst:
            if bi.dir == seg_dir:  # 过滤同方向笔
                continue
            # 控制首笔处理逻辑
            if deal_bi_cnt < 1:
                self.add_to_free_lst(bi, seg_is_sure, "normal")
                deal_bi_cnt += 1
            else:
                self.update(bi, seg_is_sure)

    def try_construct_zs(self, lst, is_sure, zs_algo):
        """尝试构造中枢核心方法"""
        # 普通模式处理逻辑
        if zs_algo == "normal":
            if not self.config.one_bi_zs:
                if len(lst) == 1:  # 单笔不构成中枢
                    return None
                else:
                    lst = lst[-2:]  # 取最后两笔
        # 线段穿透模式处理
        elif zs_algo == "over_seg":
            if len(lst) < 3:  # 需要至少三笔
                return None
            lst = lst[-3:]  # 取最后三笔
            if lst[0].dir == lst[0].parent_seg.dir:  # 过滤方向一致的笔
                lst = lst[1:]
                return None
        # 计算价格重叠区间
        min_high = min(item._high() for item in lst)
        max_low = max(item._low() for item in lst)
        return CZS(lst, is_sure=is_sure) if min_high > max_low else None

    def cal_bi_zs(self, bi_lst: Union[CBiList, CSegListComm], seg_lst: CSegListComm):
        """中枢计算主入口"""
        # 清理过期中枢
        while self.zs_lst and self.zs_lst[-1].begin_bi.idx >= self.last_sure_pos:
            self.zs_lst.pop()
        
        # 不同算法分支处理
        if self.config.zs_algo == "normal":
            # 标准模式：按线段划分处理
            for seg in seg_lst[self.last_seg_idx:]:
                if not self.seg_need_cal(seg):
                    continue
                self.clear_free_lst()
                seg_bi_lst = bi_lst[seg.start_bi.idx:seg.end_bi.idx+1]
                self.add_zs_from_bi_range(seg_bi_lst, seg.dir, seg.is_sure)
            
            # 处理未形成线段的剩余笔
            if len(seg_lst):
                self.clear_free_lst()
                self.add_zs_from_bi_range(bi_lst[seg_lst[-1].end_bi.idx+1:], revert_bi_dir(seg_lst[-1].dir), False)
        
        elif self.config.zs_algo == "over_seg":
            # 线段穿透模式：直接处理笔序列
            assert self.config.one_bi_zs is False
            self.clear_free_lst()
            begin_bi_idx = self.zs_lst[-1].end_bi.idx+1 if self.zs_lst else 0
            for bi in bi_lst[begin_bi_idx:]:
                self.update_overseg_zs(bi)
        
        elif self.config.zs_algo == "auto":
            # 自动模式：混合处理逻辑
            sure_seg_appear = False
            exist_sure_seg = seg_lst.exist_sure_seg()
            for seg in seg_lst[self.last_seg_idx:]:
                if seg.is_sure:
                    sure_seg_appear = True
                if not self.seg_need_cal(seg):
                    continue
                if seg.is_sure or (not sure_seg_appear and exist_sure_seg):
                    self.clear_free_lst()
                    self.add_zs_from_bi_range(bi_lst[seg.start_bi.idx:seg.end_bi.idx+1], seg.dir, seg.is_sure)
                else:
                    self.clear_free_lst()
                    for bi in bi_lst[seg.start_bi.idx:]:
                        self.update_overseg_zs(bi)
                    break
        
        else:
            raise Exception(f"未知的中枢算法:{self.config.zs_algo}")
        
        self.update_last_pos(seg_lst)

    def update_overseg_zs(self, bi: CBi | CSeg):
        """线段穿透模式下的中枢更新"""
        # 检查是否可以延续已有中枢
        if len(self.zs_lst) and len(self.free_item_lst) == 0:
            if bi.next is None:
                return
            if bi.idx - self.zs_lst[-1].end_bi.idx <= 1 and self.zs_lst[-1].in_range(bi.next):
                if self.zs_lst[-1].try_add_to_end(bi):
                    return
        
        # 防止重复添加到已有中枢
        if len(self.zs_lst) and len(self.free_item_lst) == 0 and self.zs_lst[-1].in_range(bi):
            if bi.idx - self.zs_lst[-1].end_bi.idx <= 1:
                return
        
        # 添加到临时列表尝试构造新中枢
        self.add_to_free_lst(bi, bi.is_sure, zs_algo="over_seg")

    # 以下是容器标准方法
    def __iter__(self):
        yield from self.zs_lst

    def __len__(self):
        return len(self.zs_lst)

    @overload
    def __getitem__(self, index: int) -> CZS: ...

    @overload
    def __getitem__(self, index: slice) -> List[CZS]: ...

    def __getitem__(self, index: Union[slice, int]) -> Union[List[CZS], CZS]:
        return self.zs_lst[index]

    def try_combine(self):
        """尝试合并相邻中枢"""
        if not self.config.need_combine:
            return
        # 循环合并直到无法合并
        while len(self.zs_lst) >= 2 and self.zs_lst[-2].combine(self.zs_lst[-1], combine_mode=self.config.zs_combine_mode):
            self.zs_lst = self.zs_lst[:-1]