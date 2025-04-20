from typing import Dict, Generic, Iterable, List, Optional, Tuple, TypeVar

# 导入构成笔、线段、中枢的基础类
from Bi.Bi import CBi
# 导入笔列表类
from Bi.BiList import CBiList
# 导入买卖点类型枚举
from Common.CEnum import BSP_TYPE
# 导入辅助函数，例如判断区间是否有重叠
from Common.func_util import has_overlap
# 导入线段类
from Seg.Seg import CSeg
# 导入线段列表通用类
from Seg.SegListComm import CSegListComm
# 导入中枢类
from ZS.ZS import CZS

# 导入买卖点类
from .BS_Point import CBS_Point
# 导入买卖点配置类
from .BSPointConfig import CBSPointConfig, CPointConfig

# 定义类型变量 LINE_TYPE，可以是 CBi (笔) 或 CSeg[CBi] (由笔构成的线段)
LINE_TYPE = TypeVar('LINE_TYPE', CBi, CSeg[CBi])
# 定义类型变量 LINE_LIST_TYPE，可以是 CBiList (笔列表) 或 CSegListComm[CBi] (线段列表)
LINE_LIST_TYPE = TypeVar('LINE_LIST_TYPE', CBiList, CSegListComm[CBi])


# 定义买卖点列表类，使用泛型，适应不同级别的笔或线段
class CBSPointList(Generic[LINE_TYPE, LINE_LIST_TYPE]):
    # 类的初始化方法
    def __init__(self, bs_point_config: CBSPointConfig):
        # 存储不同类型买卖点的字典
        # 键为 BSP_TYPE (买卖点类型)，值为一个元组
        # 元组第一个元素是买点列表 (is_buy=True)，第二个元素是卖点列表 (is_buy=False)
        self.bsp_store_dict: Dict[BSP_TYPE, Tuple[List[CBS_Point[LINE_TYPE]], List[CBS_Point[LINE_TYPE]]]] = {}
        # 存储所有买卖点的扁平化字典，键为构成买卖点的笔或线段的idx，值为买卖点对象
        self.bsp_store_flat_dict: Dict[int, CBS_Point[LINE_TYPE]] = {}

        # 专门存储第一类买卖点 (BSP_TYPE.T1 或 BSP_TYPE.T1P) 的列表
        self.bsp1_list: List[CBS_Point[LINE_TYPE]] = []
        # 专门存储第一类买卖点 (BSP_TYPE.T1 或 BSP_TYPE.T1P) 的字典，键为笔或线段的idx
        self.bsp1_dict: Dict[int, CBS_Point[LINE_TYPE]] = {}

        # 买卖点配置对象
        self.config = bs_point_config
        # 上一个确定位置的K线索引
        self.last_sure_pos = -1
        # 上一个确定线段的索引
        self.last_sure_seg_idx = 0

    # 将买卖点添加到存储字典和扁平化字典中
    def store_add_bsp(self, bsp_type: BSP_TYPE, bsp: CBS_Point[LINE_TYPE]):
        # 如果该买卖点类型不在存储字典中，初始化对应的列表
        if bsp_type not in self.bsp_store_dict:
            self.bsp_store_dict[bsp_type] = ([], [])
        # 断言：确保当前添加的买卖点所基于的笔或线段索引大于同类型同买卖方向的最后一个买卖点
        # 这保证了同一类型买卖点的顺序是按照其基于的笔/线段索引递增的
        if len(self.bsp_store_dict[bsp_type][bsp.is_buy]) > 0:
            assert self.bsp_store_dict[bsp_type][bsp.is_buy][-1].bi.idx < bsp.bi.idx, f"{bsp_type}, {bsp.is_buy} {self.bsp_store_dict[bsp_type][bsp.is_buy][-1].bi.idx} {bsp.bi.idx}"
        # 将买卖点添加到对应的买卖方向列表中
        self.bsp_store_dict[bsp_type][bsp.is_buy].append(bsp)
        # 将买卖点添加到扁平化字典中
        self.bsp_store_flat_dict[bsp.bi.idx] = bsp

    # 添加第一类买卖点到专门的列表和字典中
    def add_bsp1(self, bsp: CBS_Point[LINE_TYPE]):
        # 断言：确保当前添加的第一类买卖点所基于的笔或线段索引大于列表中最后一个
        if len(self.bsp1_list) > 0:
            assert self.bsp1_list[-1].bi.idx < bsp.bi.idx
        # 添加到列表中
        self.bsp1_list.append(bsp)
        # 添加到字典中
        self.bsp1_dict[bsp.bi.idx] = bsp

    # 清理存储字典中位于 last_sure_pos 之后的买卖点 (未确认部分)
    def clear_store_end(self):
        # 遍历所有买卖点类型
        for bsp_list in self.bsp_store_dict.values():
            # 遍历买点和卖点方向
            for is_buy in [True, False]:
                # 从后往前清理
                while len(bsp_list[is_buy]) > 0:
                    # 如果最后一个买卖点所基于的笔/线段的结束K线索引小于等于 last_sure_pos，则停止清理
                    if bsp_list[is_buy][-1].bi.get_end_klu().idx <= self.last_sure_pos:
                        break
                    # 从扁平化字典中删除
                    del self.bsp_store_flat_dict[bsp_list[is_buy][-1].bi.idx]
                    # 从列表中删除
                    bsp_list[is_buy].pop()

    # 清理第一类买卖点列表中位于 last_sure_pos 之后的买卖点 (未确认部分)
    def clear_bsp1_end(self):
        # 从后往前清理
        while len(self.bsp1_list) > 0:
            # 如果最后一个第一类买卖点所基于的笔/线段的结束K线索引小于等于 last_sure_pos，则停止清理
            if self.bsp1_list[-1].bi.get_end_klu().idx <= self.last_sure_pos:
                break
            # 从字典中删除
            del self.bsp1_dict[self.bsp1_list[-1].bi.idx]
            # 从列表中删除
            self.bsp1_list.pop()

    # 迭代器，用于遍历所有存储的买卖点
    def bsp_iter(self) -> Iterable[CBS_Point[LINE_TYPE]]:
        # 遍历所有买卖点类型
        for bsp_list in self.bsp_store_dict.values():
            # 先 yielding 所有买点
            yield from bsp_list[True]
            # 再 yielding 所有卖点
            yield from bsp_list[False]

    # 返回买卖点总数 (通过扁平化字典的长度)
    def __len__(self):
        return len(self.bsp_store_flat_dict)

    # 计算买卖点的核心方法
    def cal(self, bi_list: LINE_LIST_TYPE, seg_list: CSegListComm[LINE_TYPE]):
        # 清理未确定部分的存储买卖点
        self.clear_store_end()
        # 清理未确定部分的第一类买卖点
        self.clear_bsp1_end()
        # 计算线段上的第一类买卖点
        self.cal_seg_bs1point(seg_list, bi_list)
        # 计算线段上的第二类买卖点
        self.cal_seg_bs2point(seg_list, bi_list)
        # 计算线段上的第三类买卖点
        self.cal_seg_bs3point(seg_list, bi_list)

        # 更新最后一个确定位置的K线索引和线段索引
        self.update_last_pos(seg_list)

    # 更新最后一个确定位置的K线索引和线段索引
    def update_last_pos(self, seg_list: CSegListComm):
        # 初始化为 -1 和 0
        self.last_sure_pos = -1
        self.last_sure_seg_idx = 0
        # 从最后一个线段开始向前查找
        seg_idx = len(seg_list)-1
        while seg_idx >= 0:
            seg = seg_list[seg_idx]
            # 如果线段是确定的
            if seg.is_sure:
                # 更新 last_sure_pos 为该线段开始笔的开始K线索引
                self.last_sure_pos = seg.end_bi.get_begin_klu().idx
                # 更新 last_sure_seg_idx 为该线段的索引
                self.last_sure_seg_idx = seg.idx
                return
            seg_idx -= 1

    # 判断线段是否需要计算买卖点
    # 如果线段的结束笔的结束K线索引大于 last_sure_pos，则需要计算
    def seg_need_cal(self, seg: CSeg):
        return seg.end_bi.get_end_klu().idx > self.last_sure_pos

    # 添加买卖点到列表中，这是一个通用的添加函数
    def add_bs(
        self,
        bs_type: BSP_TYPE,  # 买卖点类型
        bi: LINE_TYPE,  # 构成买卖点的笔或线段
        relate_bsp1: Optional[CBS_Point],  # 关联的第一类买卖点 (主要用于第二、三类)
        is_target_bsp: bool = True,  # 是否是目标买卖点类型 (由配置决定)
        feature_dict=None,  # 特征字典，可以存储背驰率等信息
    ):
        # 判断是买点 (基于下笔/线段) 还是卖点 (基于上笔/线段)
        is_buy = bi.is_down()
        # 检查该笔/线段是否已经有一个买卖点被记录
        if exist_bsp := self.bsp_store_flat_dict.get(bi.idx):
            # 如果存在，断言方向一致
            assert exist_bsp.is_buy == is_buy
            # 为已存在的买卖点添加新的买卖点属性 (例如，一个点可能是 T1 也是 T1P)
            exist_bsp.add_another_bsp_prop(bs_type, relate_bsp1)
            return # 已经处理，直接返回
        # 如果当前买卖点类型不在配置的目标类型中，标记为非目标买卖点
        if bs_type not in self.config.GetBSConfig(is_buy).target_types:
            is_target_bsp = False

        # 如果是目标买卖点或者第一类买卖点 (T1 或 T1P)
        if is_target_bsp or bs_type in [BSP_TYPE.T1, BSP_TYPE.T1P]:
            # 创建新的买卖点对象
            bsp = CBS_Point[LINE_TYPE](
                bi=bi,
                is_buy=is_buy,
                bs_type=bs_type,
                relate_bsp1=relate_bsp1,
                feature_dict=feature_dict,
            )
        else:
            # 如果既不是目标买卖点也不是第一类买卖点，则不创建对象，直接返回
            return
        # 如果是目标买卖点，添加到存储字典和扁平化字典
        if is_target_bsp:
            self.store_add_bsp(bs_type, bsp)
        # 如果是第一类买卖点 (T1 或 T1P)，添加到专门的第一类买卖点列表和字典
        if bs_type in [BSP_TYPE.T1, BSP_TYPE.T1P]:
            self.add_bsp1(bsp)

    # 计算线段上的第一类买卖点
    def cal_seg_bs1point(self, seg_list: CSegListComm[LINE_TYPE], bi_list: LINE_LIST_TYPE):
        # 从 last_sure_seg_idx 开始遍历线段
        for seg in seg_list[self.last_sure_seg_idx:]:
            # 如果线段不需要计算，跳过
            if not self.seg_need_cal(seg):
                continue
            # 对单个线段计算第一类买卖点
            self.cal_single_bs1point(seg, bi_list)

    # 对单个线段计算第一类买卖点
    def cal_single_bs1point(self, seg: CSeg[LINE_TYPE], bi_list: LINE_LIST_TYPE):
        # 获取该线段方向对应的买卖点配置
        BSP_CONF = self.config.GetBSConfig(seg.is_down())
        # 计算线段内的中枢数量，根据配置决定是否只计算多笔构成的中枢
        zs_cnt = seg.get_multi_bi_zs_cnt() if BSP_CONF.bsp1_only_multibi_zs else len(seg.zs_lst)
        # 判断是否是目标买卖点 (根据配置的最小中枢数量)
        is_target_bsp = (BSP_CONF.min_zs_cnt <= 0 or zs_cnt >= BSP_CONF.min_zs_cnt)
        # 判断是否满足标准的第一类买卖点条件：
        # 线段有中枢，且最后一个中枢不是单笔中枢
        # 最后一个中枢的出笔 >= 线段的结束笔
        # 最后一个中枢的入笔到线段结束笔之间至少有3笔 (idx 差 > 2)
        if len(seg.zs_lst) > 0 and \
           not seg.zs_lst[-1].is_one_bi_zs() and \
           ((seg.zs_lst[-1].bi_out and seg.zs_lst[-1].bi_out.idx >= seg.end_bi.idx) or seg.zs_lst[-1].bi_lst[-1].idx >= seg.end_bi.idx) \
           and seg.end_bi.idx - seg.zs_lst[-1].get_bi_in().idx > 2:
            # 满足标准第一类买卖点条件，调用 treat_bsp1 处理
            self.treat_bsp1(seg, BSP_CONF, is_target_bsp)
        else:
            # 不满足标准第一类买卖点条件，可能是盘整背驰引起的第一类买卖点，调用 treat_pz_bsp1 处理
            self.treat_pz_bsp1(seg, BSP_CONF, bi_list, is_target_bsp)

    # 处理标准的第一类买卖点 (T1)
    def treat_bsp1(self, seg: CSeg[LINE_TYPE], BSP_CONF: CPointConfig, is_target_bsp: bool):
        # 获取线段的最后一个中枢
        last_zs = seg.zs_lst[-1]
        # 判断最后一个中枢的出笔是否是顶/底分型 (相对于线段结束笔的下一个位置)
        break_peak, _ = last_zs.out_bi_is_peak(seg.end_bi.idx)
        # 如果配置要求顶/底分型但未形成，则标记为非目标买卖点
        if BSP_CONF.bs1_peak and not break_peak:
            is_target_bsp = False
        # 判断最后一个中枢是否与线段结束笔构成背驰，并计算背驰率
        is_diver, divergence_rate = last_zs.is_divergence(BSP_CONF, out_bi=seg.end_bi)
        # 如果不构成背驰，则标记为非目标买卖点
        if not is_diver:
            is_target_bsp = False
        # 存储背驰率作为特征
        feature_dict = {'divergence_rate': divergence_rate}
        # 添加该买卖点，类型为 T1
        self.add_bs(bs_type=BSP_TYPE.T1, bi=seg.end_bi, relate_bsp1=None, is_target_bsp=is_target_bsp, feature_dict=feature_dict)

    # 处理盘整背驰引起的第一类买卖点 (T1P)
    def treat_pz_bsp1(self, seg: CSeg[LINE_TYPE], BSP_CONF: CPointConfig, bi_list: LINE_LIST_TYPE, is_target_bsp):
        # 获取线段的结束笔
        last_bi = seg.end_bi
        # 获取倒数第三笔 (结束笔的前两笔)
        pre_bi = bi_list[last_bi.idx-2]
        # 如果倒数第三笔和结束笔不在同一个线段，或者方向不一致，则不构成 T1P 条件，返回
        if last_bi.seg_idx != pre_bi.seg_idx:
            return
        if last_bi.dir != seg.dir:
            return
        # 对于下笔，如果结束笔的低点没有创新低，返回 (买点条件)
        if last_bi.is_down() and last_bi._low() > pre_bi._low():  # 创新低
            return
        # 对于上笔，如果结束笔的高点没有创新高，返回 (卖点条件)
        if last_bi.is_up() and last_bi._high() < pre_bi._high():  # 创新高
            return
        # 计算倒数第三笔的 MACD 指标值 (入)
        in_metric = pre_bi.cal_macd_metric(BSP_CONF.macd_algo, is_reverse=False)
        # 计算结束笔的 MACD 指标值 (出)，反向计算
        out_metric = last_bi.cal_macd_metric(BSP_CONF.macd_algo, is_reverse=True)
        # 判断是否构成背驰，并计算背驰率
        is_diver, divergence_rate = out_metric <= BSP_CONF.divergence_rate*in_metric, out_metric/(in_metric+1e-7)
        # 如果不构成背驰，则标记为非目标买卖点
        if not is_diver:
            is_target_bsp = False
        # 如果是笔列表，断言 last_bi 和 pre_bi 都是 CBi 类型
        if isinstance(bi_list, CBiList):
            assert isinstance(last_bi, CBi) and isinstance(pre_bi, CBi)
        # 存储背驰率作为特征
        feature_dict = {'divergence_rate': divergence_rate}
        # 添加该买卖点，类型为 T1P
        self.add_bs(bs_type=BSP_TYPE.T1P, bi=last_bi, relate_bsp1=None, is_target_bsp=is_target_bsp, feature_dict=feature_dict)

    # 计算线段上的第二类买卖点
    def cal_seg_bs2point(self, seg_list: CSegListComm[LINE_TYPE], bi_list: LINE_LIST_TYPE):
        # 从 last_sure_seg_idx 开始遍历线段
        for seg in seg_list[self.last_sure_seg_idx:]:
            # 获取该线段方向对应的买卖点配置
            config = self.config.GetBSConfig(seg.is_down())
            # 如果配置中不包含 T2 或 T2S 类型，跳过
            if BSP_TYPE.T2 not in config.target_types and BSP_TYPE.T2S not in config.target_types:
                continue
            # 如果线段不需要计算，跳过
            if not self.seg_need_cal(seg):
                continue
            # 处理第二类买卖点
            self.treat_bsp2(seg, seg_list, bi_list)

    # 处理第二类买卖点 (T2 和 T2S)
    def treat_bsp2(self, seg: CSeg, seg_list: CSegListComm[LINE_TYPE], bi_list: LINE_LIST_TYPE):
        # 如果线段列表长度大于1 (即当前处理的是线段列表中的线段)
        if len(seg_list) > 1:
            # 获取该线段方向对应的买卖点配置
            BSP_CONF = self.config.GetBSConfig(seg.is_down())
            # 第二类买卖点通常基于第一类买卖点所在的笔/线段
            bsp1_bi = seg.end_bi
            # 查找对应的第一类买卖点对象
            real_bsp1 = self.bsp1_dict.get(bsp1_bi.idx)
            # 如果 bsp1_bi 后面的 K 线不足两根，返回
            if bsp1_bi.idx + 2 >= len(bi_list):
                return
            # 突破笔 (第一类买卖点后第一笔)
            break_bi = bi_list[bsp1_bi.idx + 1]
            # 第二类买卖点所在的笔 (第一类买卖点后第二笔)
            bsp2_bi = bi_list[bsp1_bi.idx + 2]
        else: # 如果线段列表长度为1 (即线段本身就是处理对象)
            # 获取线段反方向的买卖点配置 (例如，处理向上线段的卖点)
            BSP_CONF = self.config.GetBSConfig(seg.is_up())
            # 此时没有关联的第一类买卖点笔
            bsp1_bi, real_bsp1 = None, None
            # 如果笔列表长度不足2，返回
            if len(bi_list) == 1:
                return
            # 第二类买卖点所在的笔是第二笔
            bsp2_bi = bi_list[1]
            # 突破笔是第一笔
            break_bi = bi_list[0]
        # 如果配置要求第二类买卖点必须跟随第一类买卖点，且第一类买卖点不存在或未被存储，返回
        if BSP_CONF.bsp2_follow_1 and (not bsp1_bi or bsp1_bi.idx not in self.bsp_store_flat_dict):
            return
        # 计算回撤率 (bsp2_bi 的幅度 / break_bi 的幅度)
        retrace_rate = bsp2_bi.amp()/break_bi.amp()
        # 判断是否满足第二类买卖点条件 (回撤率小于等于最大允许的回撤率)
        bsp2_flag = retrace_rate <= BSP_CONF.max_bs2_rate
        # 如果满足条件，添加类型为 T2 的买卖点
        if bsp2_flag:
            self.add_bs(bs_type=BSP_TYPE.T2, bi=bsp2_bi, relate_bsp1=real_bsp1)  # type: ignore
        # 如果配置要求类二买卖点必须跟随第二类买卖点且第二类买卖点不满足，返回
        elif BSP_CONF.bsp2s_follow_2:
            return
        # 如果配置中不包含 T2S 类型，返回
        if BSP_TYPE.T2S not in self.config.GetBSConfig(seg.is_down()).target_types:
            return
        # 处理类二买卖点 (T2S)
        self.treat_bsp2s(seg_list, bi_list, bsp2_bi, break_bi, real_bsp1, BSP_CONF)  # type: ignore

    # 处理类二买卖点 (T2S)
    def treat_bsp2s(
        self,
        seg_list: CSegListComm,
        bi_list: LINE_LIST_TYPE,
        bsp2_bi: LINE_TYPE,  # 第二类买卖点所在的笔
        break_bi: LINE_TYPE, # 突破笔
        real_bsp1: Optional[CBS_Point], # 关联的第一类买卖点
        BSP_CONF: CPointConfig, # 买卖点配置
    ):
        bias = 2 # 从 bsp2_bi 后面的第二笔开始检查
        _low, _high = None, None # 初始化重叠区间

        # 循环检查后续的笔，间隔为2 (构成新的笔)
        while bsp2_bi.idx + bias < len(bi_list):  # 计算类二
            # 类二买卖点所在的笔
            bsp2s_bi = bi_list[bsp2_bi.idx + bias]
            # 断言 bsp2s_bi 和 bsp2_bi 的线段索引不为空
            assert bsp2s_bi.seg_idx is not None and bsp2_bi.seg_idx is not None
            # 如果配置限制了最大的类二级别 (bias/2 对应级别)，超过限制则中断
            if BSP_CONF.max_bsp2s_lv is not None and bias/2 > BSP_CONF.max_bsp2s_lv:
                break
            # 如果类二所在的笔和第二类买卖点所在的笔不在同一个线段，且类二所在的线段不是最后一个线段，
            # 或者线段索引相差大于等于2，或者第二类买卖点所在的线段已经确定，则中断 (避免跨线段形成类二)
            if bsp2s_bi.seg_idx != bsp2_bi.seg_idx and (bsp2s_bi.seg_idx < len(seg_list)-1 or bsp2s_bi.seg_idx - bsp2_bi.seg_idx >= 2 or seg_list[bsp2_bi.seg_idx].is_sure):
                break
            # 如果是第一次检查 (bias == 2)
            if bias == 2:
                # 如果 bsp2_bi 和 bsp2s_bi 没有价格重叠，中断
                if not has_overlap(bsp2_bi._low(), bsp2_bi._high(), bsp2s_bi._low(), bsp2s_bi._high()):
                    break
                # 计算重叠区间
                _low = max([bsp2_bi._low(), bsp2s_bi._low()])
                _high = min([bsp2_bi._high(), bsp2s_bi._high()])
            # 如果不是第一次检查，如果 bsp2s_bi 和当前的重叠区间没有价格重叠，中断
            elif not has_overlap(_low, _high, bsp2s_bi._low(), bsp2s_bi._high()):
                break

            # 如果 bsp2s_bi 突破了 break_bi 的高点/低点，中断
            if bsp2s_break_bsp1(bsp2s_bi, break_bi):
                break
            # 计算回撤率 (bsp2s_bi 结束价与 break_bi 结束价的差值绝对值 / break_bi 的幅度)
            retrace_rate = abs(bsp2s_bi.get_end_val()-break_bi.get_end_val())/break_bi.amp()
            # 如果回撤率超过最大允许的回撤率，中断
            if retrace_rate > BSP_CONF.max_bs2_rate:
                break

            # 满足条件，添加类型为 T2S 的买卖点
            self.add_bs(bs_type=BSP_TYPE.T2S, bi=bsp2s_bi, relate_bsp1=real_bsp1)  # type: ignore
            # 检查下一组笔， bias 增加2
            bias += 2

    # 计算线段上的第三类买卖点
    def cal_seg_bs3point(self, seg_list: CSegListComm[LINE_TYPE], bi_list: LINE_LIST_TYPE):
        # 从 last_sure_seg_idx 开始遍历线段
        for seg in seg_list[self.last_sure_seg_idx:]:
            # 如果线段不需要计算，跳过
            if not self.seg_need_cal(seg):
                continue
            # 获取该线段方向对应的买卖点配置
            config = self.config.GetBSConfig(seg.is_down())
            # 如果配置中不包含 T3A 或 T3B 类型，跳过
            if BSP_TYPE.T3A not in config.target_types and BSP_TYPE.T3B not in config.target_types:
                continue
            # 如果线段列表长度大于1
            if len(seg_list) > 1:
                # 第三类买卖点通常基于线段的结束笔
                bsp1_bi = seg.end_bi
                bsp1_bi_idx = bsp1_bi.idx
                # 获取该线段方向对应的买卖点配置
                BSP_CONF = self.config.GetBSConfig(seg.is_down())
                # 查找关联的第一类买卖点对象
                real_bsp1 = self.bsp1_dict.get(bsp1_bi.idx)
                # 下一个线段的索引
                next_seg_idx = seg.idx+1
                # 下一个线段对象 (可能为 None)
                next_seg = seg.next  # 可能为None, 所以并不一定可以保证next_seg_idx == next_seg.idx
            else: # 如果线段列表长度为1
                # 下一个线段就是当前线段 (处理线段本身的买卖点)
                next_seg = seg
                next_seg_idx = seg.idx
                # 没有关联的第一类买卖点笔
                bsp1_bi, real_bsp1 = None, None
                bsp1_bi_idx = -1
                # 获取线段反方向的买卖点配置
                BSP_CONF = self.config.GetBSConfig(seg.is_up())
            # 如果配置要求第三类买卖点必须跟随第一类买卖点，且第一类买卖点不存在或未被存储，跳过
            if BSP_CONF.bsp3_follow_1 and (not bsp1_bi or bsp1_bi.idx not in self.bsp_store_flat_dict):
                continue
            # 如果存在下一个线段
            if next_seg:
                # 处理第三类 A 买卖点 (突破下一个线段第一个中枢的买卖点)
                self.treat_bsp3_after(seg_list, next_seg, BSP_CONF, bi_list, real_bsp1, bsp1_bi_idx, next_seg_idx)
            # 处理第三类 B 买卖点 (回抽当前线段最后一个中枢的买卖点)
            self.treat_bsp3_before(seg_list, seg, next_seg, bsp1_bi, BSP_CONF, bi_list, real_bsp1, next_seg_idx)

    # 处理第三类 A 买卖点 (T3A)
    def treat_bsp3_after(
        self,
        seg_list: CSegListComm[LINE_TYPE],
        next_seg: CSeg[LINE_TYPE], # 下一个线段
        BSP_CONF: CPointConfig, # 买卖点配置
        bi_list: LINE_LIST_TYPE, # 笔/线段列表
        real_bsp1, # 关联的第一类买卖点
        bsp1_bi_idx, # 第一类买卖点基于的笔/线段索引
        next_seg_idx # 下一个线段的索引
    ):
        # 获取下一个线段的第一个多笔构成的中枢
        first_zs = next_seg.get_first_multi_bi_zs()
        # 如果不存在，返回
        if first_zs is None:
            return
        # 如果配置要求严格的第三类买卖点，且第一个中枢的入笔不是 bsp1_bi_idx 的下一笔，返回
        if BSP_CONF.strict_bsp3 and first_zs.get_bi_in().idx != bsp1_bi_idx+1:
            return
        # 如果第一个中枢没有出笔，或者出笔后没有下一笔，返回
        if first_zs.bi_out is None or first_zs.bi_out.idx+1 >= len(bi_list):
            return
        # 第三类 A 买卖点所在的笔 (第一个中枢出笔的下一笔)
        bsp3_bi = bi_list[first_zs.bi_out.idx+1]
        # 如果 bsp3_bi 没有父线段
        if bsp3_bi.parent_seg is None:
            # 且 next_seg 不是最后一个线段，返回
            if next_seg.idx != len(seg_list)-1:
                return
        # 如果 bsp3_bi 的父线段不是 next_seg
        elif bsp3_bi.parent_seg.idx != next_seg.idx:
            # 且 bsp3_bi 的父线段笔数量大于等于3，返回 (避免跨线段且不是线段的起始笔)
            if len(bsp3_bi.parent_seg.bi_list) >= 3:
                return
        # 如果 bsp3_bi 的方向和 next_seg 的方向相同，返回
        if bsp3_bi.dir == next_seg.dir:
            return
        # 如果 bsp3_bi 的线段索引不是 next_seg_idx，且 next_seg_idx 不是倒数第二个线段，返回
        if bsp3_bi.seg_idx != next_seg_idx and next_seg_idx < len(seg_list)-2:
            return
        # 如果 bsp3_bi 回抽到了第一个中枢的区间内，返回
        if bsp3_back2zs(bsp3_bi, first_zs):
            return
        # 判断 bsp3_bi 是否突破了第一个中枢的顶/底
        bsp3_peak_zs = bsp3_break_zspeak(bsp3_bi, first_zs)
        # 如果配置要求突破中枢顶/底但未突破，返回
        if BSP_CONF.bsp3_peak and not bsp3_peak_zs:
            return
        # 满足条件，添加类型为 T3A 的买卖点
        self.add_bs(bs_type=BSP_TYPE.T3A, bi=bsp3_bi, relate_bsp1=real_bsp1)  # type: ignore

    # 处理第三类 B 买卖点 (T3B)
    def treat_bsp3_before(
        self,
        seg_list: CSegListComm[LINE_TYPE],
        seg: CSeg[LINE_TYPE], # 当前线段
        next_seg: Optional[CSeg[LINE_TYPE]], # 下一个线段 (可能为 None)
        bsp1_bi: Optional[LINE_TYPE], # 关联的第一类买卖点基于的笔/线段 (可能为 None)
        BSP_CONF: CPointConfig, # 买卖点配置
        bi_list: LINE_LIST_TYPE, # 笔/线段列表
        real_bsp1, # 关联的第一类买卖点
        next_seg_idx # 下一个线段的索引
    ):
        # 获取当前线段的最后一个多笔构成的中枢
        cmp_zs = seg.get_final_multi_bi_zs()
        # 如果不存在，返回
        if cmp_zs is None:
            return
        # 如果没有关联的第一类买卖点笔，返回
        if not bsp1_bi:
            return
        # 如果配置要求严格的第三类买卖点，且最后一个中枢没有出笔，或者出笔不是 bsp1_bi，返回
        if BSP_CONF.strict_bsp3 and (cmp_zs.bi_out is None or cmp_zs.bi_out.idx != bsp1_bi.idx):
            return
        # 计算第三类 B 买卖点检查的结束笔索引
        end_bi_idx = cal_bsp3_bi_end_idx(next_seg)
        # 从 bsp1_bi 后面的第二笔开始，间隔为2遍历后续的笔
        for bsp3_bi in bi_list[bsp1_bi.idx+2::2]:
            # 如果当前笔的索引超过了检查结束索引，中断
            if bsp3_bi.idx > end_bi_idx:
                break
            # 断言 bsp3_bi 的线段索引不为空
            assert bsp3_bi.seg_idx is not None
            # 如果 bsp3_bi 的线段索引不是 next_seg_idx，且 bsp3_bi 所在的线段不是最后一个线段，中断
            if bsp3_bi.seg_idx != next_seg_idx and bsp3_bi.seg_idx < len(seg_list)-1:
                break
            # 如果 bsp3_bi 回抽到了最后一个中枢的区间内，继续检查下一笔
            if bsp3_back2zs(bsp3_bi, cmp_zs):  # type: ignore
                continue
            # 满足条件，添加类型为 T3B 的买卖点
            self.add_bs(bs_type=BSP_TYPE.T3B, bi=bsp3_bi, relate_bsp1=real_bsp1)  # type: ignore
            # 找到一个就停止 (第三类 B 通常只取第一个回抽不破中枢的笔)
            break

    # 获取所有存储的买卖点，并按基于的笔/线段索引排序
    def getSortedBspList(self) -> List[CBS_Point[LINE_TYPE]]:
        # 使用 bsp_iter 获取所有买卖点，然后按 bi.idx 排序
        return sorted(self.bsp_iter(), key=lambda bsp: bsp.bi.idx)


# -------------------- 辅助函数 --------------------

# 判断类二买卖点候选笔是否突破了第一类买卖点形成时的突破笔
# 对于买点 (bsp2s_bi 是下笔)，如果其 low 小于 break_bi 的 low，表示创新低，突破了
# 对于卖点 (bsp2s_bi 是上笔)，如果其 high 大于 break_bi 的 high，表示创新高，突破了
def bsp2s_break_bsp1(bsp2s_bi: LINE_TYPE, bsp2_break_bi: LINE_TYPE) -> bool:
    return (bsp2s_bi.is_down() and bsp2s_bi._low() < bsp2_break_bi._low()) or \
           (bsp2s_bi.is_up() and bsp2s_bi._high() > bsp2_break_bi._high())


# 判断第三类买卖点候选笔是否回抽到了中枢区间内
# 对于买点 (bsp3_bi 是下笔)，如果其 low 小于中枢的 high，表示回抽进入中枢
# 对于卖点 (bsp3_bi 是上笔)，如果其 high 大于中枢的 low，表示回抽进入中枢
def bsp3_back2zs(bsp3_bi: LINE_TYPE, zs: CZS) -> bool:
    return (bsp3_bi.is_down() and bsp3_bi._low() < zs.high) or (bsp3_bi.is_up() and bsp3_bi._high() > zs.low)


# 判断第三类买卖点候选笔是否突破了中枢的顶/底 (峰值/谷值)
# 对于买点 (bsp3_bi 是下笔)，如果其 high 大于等于中枢的峰值 high，表示突破
# 对于卖点 (bsp3_bi 是上笔)，如果其 low 小于等于中枢的谷值 low，表示突破
def bsp3_break_zspeak(bsp3_bi: LINE_TYPE, zs: CZS) -> bool:
    return (bsp3_bi.is_down() and bsp3_bi._high() >= zs.peak_high) or (bsp3_bi.is_up() and bsp3_bi._low() <= zs.peak_low)


# 计算第三类 B 买卖点检查的结束笔索引
# 如果没有下一个线段，或者下一个线段没有多笔中枢且不是最后一个线段，则返回无穷大
# 否则，返回下一个线段的第一个多笔中枢的出笔索引 (如果存在) 或线段结束笔的前一笔索引
def cal_bsp3_bi_end_idx(seg: Optional[CSeg[LINE_TYPE]]):
    # 如果没有线段，返回无穷大
    if not seg:
        return float("inf")
    # 如果线段没有多笔中枢且没有下一个线段，返回无穷大
    if seg.get_multi_bi_zs_cnt() == 0 and seg.next is None:
        return float("inf")
    # 默认结束笔索引为线段结束笔的前一笔索引
    end_bi_idx = seg.end_bi.idx-1
    # 遍历线段的中枢列表
    for zs in seg.zs_lst:
        # 如果是单笔中枢，跳过
        if zs.is_one_bi_zs():
            continue
        # 如果中枢有出笔
        if zs.bi_out is not None:
            # 更新结束笔索引为该中枢的出笔索引
            end_bi_idx = zs.bi_out.idx
            # 找到第一个多笔中枢的出笔即可停止
            break
    # 返回计算出的结束笔索引
    return end_bi_idx