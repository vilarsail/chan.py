import copy
from typing import List, Union, overload

# 导入基础模块
from Bi.Bi import CBi
from Bi.BiList import CBiList
from BuySellPoint.BSPointList import CBSPointList
from ChanConfig import CChanConfig
from Common.CEnum import KLINE_DIR, SEG_TYPE  # K线方向和线段类型枚举
from Common.ChanException import CChanException, ErrCode
from Seg.Seg import CSeg
from Seg.SegConfig import CSegConfig
from Seg.SegListComm import CSegListComm  # 线段列表基类
from ZS.ZSList import CZSList  # 中枢列表

# 导入当前包模块
from .KLine import CKLine
from .KLine_Unit import CKLine_Unit


def get_seglist_instance(seg_config: CSegConfig, lv) -> CSegListComm:
    """线段列表工厂函数，根据配置创建不同的线段算法实例"""
    if seg_config.seg_algo == "chan":
        # 缠论标准线段算法
        from Seg.SegListChan import CSegListChan
        return CSegListChan(seg_config, lv)
    elif seg_config.seg_algo == "1+1":
        # 已弃用的旧版算法
        print(f'Please avoid using seg_algo={seg_config.seg_algo} as it is deprecated and no longer maintained.')
        from Seg.SegListDYH import CSegListDYH
        return CSegListDYH(seg_config, lv)
    elif seg_config.seg_algo == "break":
        # 基于突破的线段算法
        print(f'Please avoid using seg_algo={seg_config.seg_algo} as it is deprecated and no longer maintained.')
        from Seg.SegListDef import CSegListDef
        return CSegListDef(seg_config, lv)
    else:
        raise CChanException(f"unsupport seg algoright:{seg_config.seg_algo}", ErrCode.PARA_ERROR)


class CKLine_List:
    """K线容器类，管理多级别K线合并及衍生结构计算"""

    def __init__(self, kl_type, conf: CChanConfig):
        """初始化K线容器
        Args:
            kl_type: K线类型（如1分钟、5分钟等）
            conf: 全局配置对象
        """
        self.kl_type = kl_type  # K线级别类型
        self.config = conf  # 全局配置

        # K线存储结构
        self.lst: List[CKLine] = []  # 合并后的K线列表（元素为CKLine类型）

        # 衍生结构列表
        self.bi_list = CBiList(bi_conf=conf.bi_conf)  # 笔列表
        self.seg_list: CSegListComm[CBi] = get_seglist_instance(seg_config=conf.seg_conf, lv=SEG_TYPE.BI)  # 笔级别线段
        self.segseg_list: CSegListComm[CSeg[CBi]] = get_seglist_instance(seg_config=conf.seg_conf,
                                                                         lv=SEG_TYPE.SEG)  # 线段级别线段

        # 中枢结构
        self.zs_list = CZSList(zs_config=conf.zs_conf)  # 笔中枢列表
        self.segzs_list = CZSList(zs_config=conf.zs_conf)  # 线段中枢列表

        # 买卖点系统
        self.bs_point_lst = CBSPointList[CBi, CBiList](bs_point_config=conf.bs_point_conf)  # 笔买卖点
        self.seg_bs_point_lst = CBSPointList[CSeg, CSegListComm](bs_point_config=conf.seg_bs_point_conf)  # 线段买卖点

        # 指标计算模型
        self.metric_model_lst = conf.GetMetricModel()  # 获取指标计算模型

        # 计算模式控制
        self.step_calculation = self.need_cal_step_by_step()  # 逐步计算开关

        # 最后确认位置标记
        self.last_sure_seg_start_bi_idx = -1  # 最后确认线段的起始笔索引
        self.last_sure_segseg_start_bi_idx = -1  # 最后确认线段线段的起始索引

    def __deepcopy__(self, memo):
        """深拷贝实现，用于回测系统状态保存"""
        new_obj = CKLine_List(self.kl_type, self.config)
        memo[id(self)] = new_obj

        # 深度复制K线单元
        for klc in self.lst:
            klus_new = []
            for klu in klc.lst:
                new_klu = copy.deepcopy(klu, memo)
                memo[id(klu)] = new_klu
                if klu.pre is not None:  # 维护前后关系
                    new_klu.set_pre_klu(memo[id(klu.pre)])
                klus_new.append(new_klu)

            # 重建合并K线
            new_klc = CKLine(klus_new[0], idx=klc.idx, _dir=klc.dir)
            new_klc.set_fx(klc.fx)  # 复制分型信息
            new_klc.kl_type = klc.kl_type
            for idx, klu in enumerate(klus_new):
                klu.set_klc(new_klc)  # 设置K线单元所属容器
                if idx != 0:
                    new_klc.add(klu)  # 添加剩余单元
            memo[id(klc)] = new_klc

            # 维护K线链表关系
            if new_obj.lst:
                new_obj.lst[-1].set_next(new_klc)
                new_klc.set_pre(new_obj.lst[-1])
            new_obj.lst.append(new_klc)

        # 复制衍生结构
        new_obj.bi_list = copy.deepcopy(self.bi_list, memo)
        new_obj.seg_list = copy.deepcopy(self.seg_list, memo)
        new_obj.segseg_list = copy.deepcopy(self.segseg_list, memo)
        new_obj.zs_list = copy.deepcopy(self.zs_list, memo)
        new_obj.segzs_list = copy.deepcopy(self.segzs_list, memo)
        new_obj.bs_point_lst = copy.deepcopy(self.bs_point_lst, memo)
        new_obj.metric_model_lst = copy.deepcopy(self.metric_model_lst, memo)
        new_obj.step_calculation = copy.deepcopy(self.step_calculation, memo)
        new_obj.seg_bs_point_lst = copy.deepcopy(self.seg_bs_point_lst, memo)
        return new_obj

    @overload
    def __getitem__(self, index: int) -> CKLine:
        ...

    @overload
    def __getitem__(self, index: slice) -> List[CKLine]:
        ...

    def __getitem__(self, index: Union[slice, int]) -> Union[List[CKLine], CKLine]:
        """支持下标访问合并后的K线"""
        return self.lst[index]

    def __len__(self):
        """获取合并后的K线数量"""
        return len(self.lst)

    def cal_seg_and_zs(self):
        """核心计算方法：触发线段和中枢的更新"""
        # 非逐步计算模式时尝试添加虚拟笔
        if not self.step_calculation:
            self.bi_list.try_add_virtual_bi(self.lst[-1])

        # 更新笔级别线段
        self.last_sure_seg_start_bi_idx = cal_seg(self.bi_list, self.seg_list, self.last_sure_seg_start_bi_idx)
        self.zs_list.cal_bi_zs(self.bi_list, self.seg_list)  # 计算笔中枢
        update_zs_in_seg(self.bi_list, self.seg_list, self.zs_list)  # 关联中枢到线段

        # 更新线段级别线段
        self.last_sure_segseg_start_bi_idx = cal_seg(self.seg_list, self.segseg_list,
                                                     self.last_sure_segseg_start_bi_idx)
        self.segzs_list.cal_bi_zs(self.seg_list, self.segseg_list)  # 计算线段中枢
        update_zs_in_seg(self.seg_list, self.segseg_list, self.segzs_list)  # 关联中枢到线段线段

        # 计算买卖点
        self.seg_bs_point_lst.cal(self.seg_list, self.segseg_list)  # 线段级别买卖点
        self.bs_point_lst.cal(self.bi_list, self.seg_list)  # 笔级别买卖点

    def need_cal_step_by_step(self):
        """判断是否需要逐步计算模式"""
        return self.config.trigger_step  # 从配置获取计算模式

    def add_single_klu(self, klu: CKLine_Unit):
        """添加单个K线单元并触发计算
        Args:
            klu: 基础K线单元
        """
        # 设置技术指标
        klu.set_metric(self.metric_model_lst)
        # print(klu)

        if len(self.lst) == 0:  # 首个K线
            self.lst.append(CKLine(klu, idx=0))
        else:
            # 尝试合并到当前K线
            _dir = self.lst[-1].try_add(klu)
            if _dir != KLINE_DIR.COMBINE:  # 需要创建新合并K线
                new_klc = CKLine(klu, idx=len(self.lst), _dir=_dir)
                self.lst.append(new_klc)

                # 更新分型（至少3根K线后）
                if len(self.lst) >= 3:
                    self.lst[-2].update_fx(self.lst[-3], self.lst[-1])

                # 触发笔更新
                if self.bi_list.update_bi(self.lst[-2], self.lst[-1], self.step_calculation) and self.step_calculation:
                    self.cal_seg_and_zs()
            elif self.step_calculation and self.bi_list.try_add_virtual_bi(self.lst[-1], need_del_end=True):
                # 处理虚拟笔的特殊情况（参见issue#175）
                self.cal_seg_and_zs()

    def klu_iter(self, klc_begin_idx=0):
        """迭代器：遍历原始K线单元"""
        for klc in self.lst[klc_begin_idx:]:
            yield from klc.lst


def cal_seg(bi_list, seg_list: CSegListComm, last_sure_seg_start_bi_idx):
    """更新线段结构并返回最后确认线段的起始笔索引"""
    seg_list.update(bi_list)  # 调用线段列表的更新方法

    if len(seg_list) == 0:  # 空线段列表初始化
        for bi in bi_list:
            bi.set_seg_idx(0)
        return -1

    cur_seg: CSeg = seg_list[-1]  # 当前处理的线段

    # 逆向遍历笔列表设置线段索引
    bi_idx = len(bi_list) - 1
    while bi_idx >= 0:
        bi = bi_list[bi_idx]
        # 跳过已处理的确认线段
        if bi.seg_idx is not None and bi.idx < last_sure_seg_start_bi_idx:
            break
        # 处理超出当前线段范围的笔
        if bi.idx > cur_seg.end_bi.idx:
            bi.set_seg_idx(cur_seg.idx + 1)
            bi_idx -= 1
            continue
        # 切换到前驱线段
        if bi.idx < cur_seg.start_bi.idx:
            assert cur_seg.pre
            cur_seg = cur_seg.pre
        bi.set_seg_idx(cur_seg.idx)
        bi_idx -= 1

    # 寻找最后确认线段的起始笔
    last_sure_seg_start_bi_idx = -1
    seg = seg_list[-1]
    while seg:
        if seg.is_sure:
            last_sure_seg_start_bi_idx = seg.start_bi.idx
            break
        seg = seg.pre
    return last_sure_seg_start_bi_idx


def update_zs_in_seg(bi_list, seg_list, zs_list):
    """将中枢关联到对应的线段"""
    sure_seg_cnt = 0  # 已确认线段计数器
    seg_idx = len(seg_list) - 1

    # 逆向遍历线段列表
    while seg_idx >= 0:
        seg = seg_list[seg_idx]
        if seg.ele_inside_is_sure:  # 跳过已确认内部元素的线段
            break

        # 清空线段中的旧中枢
        seg.clear_zs_lst()

        # 逆向遍历中枢列表进行关联
        _zs_idx = len(zs_list) - 1
        while _zs_idx >= 0:
            zs = zs_list[_zs_idx]
            # 中枢结束位置早于线段开始位置时终止
            if zs.end.idx < seg.start_bi.get_begin_klu().idx:
                break
            # 中枢在线段范围内则添加
            if zs.is_inside(seg):
                seg.add_zs(zs)
            # 设置中枢的进出笔
            assert zs.begin_bi.idx > 0
            zs.set_bi_in(bi_list[zs.begin_bi.idx - 1])
            if zs.end_bi.idx + 1 < len(bi_list):
                zs.set_bi_out(bi_list[zs.end_bi.idx + 1])
            # 关联中枢包含的笔列表
            zs.set_bi_lst(list(bi_list[zs.begin_bi.idx:zs.end_bi.idx + 1]))
            _zs_idx -= 1

        # 更新线段内部元素确认状态
        if sure_seg_cnt > 2:
            if not seg.ele_inside_is_sure:
                seg.ele_inside_is_sure = True
        seg_idx -= 1