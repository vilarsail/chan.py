from typing import List

from Bi.Bi import CBi
from BuySellPoint.BS_Point import CBS_Point
from Common.CEnum import FX_TYPE
from KLine.KLine import CKLine
from KLine.KLine_List import CKLine_List
from Seg.Eigen import CEigen
from Seg.EigenFX import CEigenFX
from Seg.Seg import CSeg
from ZS.ZS import CZS


class Cklc_meta:
    """合并K线元数据，用于绘图数据封装"""
    def __init__(self, klc: CKLine):
        self.high = klc.high  # 合并K线最高价
        self.low = klc.low    # 合并K线最低价
        self.begin_idx = klc.lst[0].idx  # 起始K线单元索引
        self.end_idx = klc.lst[-1].idx   # 结束K线单元索引
        self.type = klc.fx if klc.fx != FX_TYPE.UNKNOWN else klc.dir  # 分型类型或合并方向
        self.klu_list = list(klc.lst)     # 包含的原始K线单元列表


class CBi_meta:
    """笔结构元数据，用于笔的可视化"""
    def __init__(self, bi: CBi):
        self.idx = bi.idx       # 笔的索引编号
        self.dir = bi.dir       # 笔的方向（向上/向下）
        self.type = bi.type     # 笔的类型（标准/虚拟等）
        self.begin_x = bi.get_begin_klu().idx  # 起始K线单元X坐标
        self.end_x = bi.get_end_klu().idx     # 结束K线单元X坐标
        self.begin_y = bi.get_begin_val()     # 起始价格Y坐标
        self.end_y = bi.get_end_val()         # 结束价格Y坐标
        self.is_sure = bi.is_sure             # 是否确认笔


class CSeg_meta:
    """线段元数据，封装线段可视化要素"""
    def __init__(self, seg: CSeg):
        # 处理线段起点终点坐标（兼容笔线段和递归线段）
        if isinstance(seg.start_bi, CBi):
            self.begin_x = seg.start_bi.get_begin_klu().idx
            self.begin_y = seg.start_bi.get_begin_val()
            self.end_x = seg.end_bi.get_end_klu().idx
            self.end_y = seg.end_bi.get_end_val()
        else:
            assert isinstance(seg.start_bi, CSeg)
            self.begin_x = seg.start_bi.start_bi.get_begin_klu().idx
            self.begin_y = seg.start_bi.start_bi.get_begin_val()
            self.end_x = seg.end_bi.end_bi.get_end_klu().idx
            self.end_y = seg.end_bi.end_bi.get_end_val()
        self.dir = seg.dir      # 线段方向
        self.is_sure = seg.is_sure  # 是否确认线段
        self.idx = seg.idx      # 线段索引

        # 趋势线存储（支撑线/压力线）
        self.tl = {}
        if seg.support_trend_line and seg.support_trend_line.line:
            self.tl["support"] = seg.support_trend_line
        if seg.resistance_trend_line and seg.resistance_trend_line.line:
            self.tl["resistance"] = seg.resistance_trend_line

    def format_tl(self, tl):
        """将趋势线转换为绘图坐标"""
        assert tl.line
        tl_slope = tl.line.slope + 1e-7  # 防止除零
        tl_x = tl.line.p.x    # 趋势线基准点X
        tl_y = tl.line.p.y    # 趋势线基准点Y
        # 计算线段起点终点对应的趋势线坐标
        tl_x0 = (self.begin_y-tl_y)/tl_slope + tl_x
        tl_x1 = (self.end_y-tl_y)/tl_slope + tl_x
        return tl_x0, self.begin_y, tl_x1, self.end_y


class CEigen_meta:
    """特征值元数据，用于中枢特征可视化"""
    def __init__(self, eigen: CEigen):
        self.begin_x = eigen.lst[0].get_begin_klu().idx  # 特征序列起始X
        self.end_x = eigen.lst[-1].get_end_klu().idx     # 特征序列结束X
        self.begin_y = eigen.low   # 特征最低价
        self.end_y = eigen.high    # 特征最高价
        self.w = self.end_x - self.begin_x  # 特征宽度
        self.h = self.end_y - self.begin_y  # 特征高度


class CEigenFX_meta:
    """分型特征元数据，用于分型结构可视化"""
    def __init__(self, eigenFX: CEigenFX):
        self.ele = [CEigen_meta(ele) for ele in eigenFX.ele if ele is not None]  # 三个特征元素
        assert len(self.ele) == 3
        assert eigenFX.ele[1] is not None
        self.gap = eigenFX.ele[1].gap  # 分型缺口标记
        self.fx = eigenFX.ele[1].fx    # 分型类型


class CZS_meta:
    """中枢元数据，封装中枢可视化要素"""
    def __init__(self, zs: CZS):
        self.low = zs.low     # 中枢最低价
        self.high = zs.high   # 中枢最高价
        self.begin = zs.begin.idx  # 起始笔索引
        self.end = zs.end.idx      # 结束笔索引
        self.w = self.end - self.begin  # 中枢时间宽度
        self.h = self.high - self.low   # 中枢价格高度
        self.is_sure = zs.is_sure      # 是否确认中枢
        self.sub_zs_lst = [CZS_meta(t) for t in zs.sub_zs_lst]  # 子中枢列表
        self.is_onebi_zs = zs.is_one_bi_zs()  # 是否单笔中枢


class CBS_Point_meta:
    """买卖点元数据，用于标注买卖信号"""
    def __init__(self, bsp: CBS_Point, is_seg):
        self.is_buy = bsp.is_buy  # 是否买入点
        self.type = bsp.type2str()  # 买卖点类型字符串
        self.is_seg = is_seg      # 是否线段级别
        self.x = bsp.klu.idx      # K线单元索引X坐标
        self.y = bsp.klu.low if self.is_buy else bsp.klu.high  # Y坐标（买点在低价，卖点在高价）

    def desc(self):
        """生成显示标签"""
        is_seg_flag = "※" if self.is_seg else ""  # 线段级别标记
        return f'{is_seg_flag}b{self.type}' if self.is_buy else f'{is_seg_flag}s{self.type}'


class CChanPlotMeta:
    """缠论绘图元数据总容器"""
    def __init__(self, kl_list: CKLine_List):
        self.data = kl_list  # 原始K线列表对象

        # K线相关数据
        self.klc_list: List[Cklc_meta] = [Cklc_meta(klc) for klc in kl_list.lst]  # 合并K线列表
        self.datetick = [klu.time.to_str() for klu in self.klu_iter()]  # 时间轴标签
        self.klu_len = sum(len(klc.klu_list) for klc in self.klc_list)  # 总K线单元数

        # 笔和线段数据
        self.bi_list = [CBi_meta(bi) for bi in kl_list.bi_list]  # 笔列表
        self.seg_list: List[CSeg_meta] = []      # 线段列表
        self.eigenfx_lst: List[CEigenFX_meta] = []  # 线段分型特征
        for seg in kl_list.seg_list:
            self.seg_list.append(CSeg_meta(seg))
            if seg.eigen_fx:
                self.eigenfx_lst.append(CEigenFX_meta(seg.eigen_fx))

        # 递归线段数据
        self.seg_eigenfx_lst: List[CEigenFX_meta] = []  # 递归线段分型
        self.segseg_list: List[CSeg_meta] = []   # 递归线段列表
        for segseg in kl_list.segseg_list:
            self.segseg_list.append(CSeg_meta(segseg))
            if segseg.eigen_fx:
                self.seg_eigenfx_lst.append(CEigenFX_meta(segseg.eigen_fx))

        # 中枢数据
        self.zs_lst: List[CZS_meta] = [CZS_meta(zs) for zs in kl_list.zs_list]  # 笔中枢
        self.segzs_lst: List[CZS_meta] = [CZS_meta(segzs) for segzs in kl_list.segzs_list]  # 线段中枢

        # 买卖点数据
        self.bs_point_lst: List[CBS_Point_meta] = [CBS_Point_meta(bs_point, is_seg=False) for bs_point in kl_list.bs_point_lst.bsp_iter()]  # 笔买卖点
        self.seg_bsp_lst: List[CBS_Point_meta] = [CBS_Point_meta(seg_bsp, is_seg=True) for seg_bsp in kl_list.seg_bs_point_lst.bsp_iter()]  # 线段买卖点

    def klu_iter(self):
        """迭代生成所有原始K线单元"""
        for klc in self.klc_list:
            yield from klc.klu_list

    def sub_last_kseg_start_idx(self, seg_cnt):
        """获取最近N线段的次级别起始索引"""
        if seg_cnt is None or len(self.data.seg_list) <= seg_cnt:
            return 0
        return self.data.seg_list[-seg_cnt].get_begin_klu().sub_kl_list[0].idx

    def sub_last_kbi_start_idx(self, bi_cnt):
        """获取最近N笔的次级别起始索引"""
        if bi_cnt is None or len(self.data.bi_list) <= bi_cnt:
            return 0
        return self.data.bi_list[-bi_cnt].begin_klc.lst[0].sub_kl_list[0].idx

    def sub_range_start_idx(self, x_range):
        """根据显示范围计算次级别起始索引"""
        for klc in self.data[::-1]:
            for klu in klc[::-1]:
                x_range -= 1
                if x_range == 0:
                    return klu.sub_kl_list[0].idx
        return 0