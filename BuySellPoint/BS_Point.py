from typing import Dict, Generic, List, Optional, TypeVar, Union

from Bi.Bi import CBi
from ChanModel.Features import CFeatures
from Common.CEnum import BSP_TYPE
from Seg.Seg import CSeg

# 泛型类型参数，用于同时支持笔（CBi）和线段（CSeg）为买卖点的载体
LINE_TYPE = TypeVar('LINE_TYPE', CBi, CSeg)


class CBS_Point(Generic[LINE_TYPE]):
    def __init__(self, bi: LINE_TYPE, is_buy, bs_type: BSP_TYPE, relate_bsp1: Optional['CBS_Point'], feature_dict=None):
        # 初始化买卖点对象

        self.bi: LINE_TYPE = bi  # 所属的笔或线段（LINE_TYPE 是 CBi 或 CSeg）
        self.klu = bi.get_end_klu()  # 获取该笔/线段的结束K线单元，用于定位买卖点位置
        self.is_buy = is_buy  # 是否为买点（True）或卖点（False）
        self.type: List[BSP_TYPE] = [bs_type]  # 买卖点的类型列表（可复合多种类型）
        self.relate_bsp1 = relate_bsp1  # 与之相关的另一个买卖点（例如买一与卖一相对应）

        self.bi.bsp = self  # 将当前买卖点挂载到所属笔或线段上（添加引用）
        self.features = CFeatures(feature_dict)  # 与买卖点相关的特征值集合（可用于进一步分析或策略）

        self.is_segbsp = False  # 标记是否属于线段级别的买卖点（默认为False）

    def add_type(self, bs_type: BSP_TYPE):
        # 添加一个买卖点类型（例如：同时属于一买和三买）
        self.type.append(bs_type)

    def type2str(self):
        # 将所有买卖点类型转换为字符串（以逗号分隔）
        return ",".join([x.value for x in self.type])

    def add_another_bsp_prop(self, bs_type: BSP_TYPE, relate_bsp1):
        # 添加额外的买卖点类型和其对应的相关买卖点
        self.add_type(bs_type)
        if self.relate_bsp1 is None:
            self.relate_bsp1 = relate_bsp1
        elif relate_bsp1 is not None:
            # 如果已有对应点，则断言两个买卖点必须对应同一个K线单元位置
            assert self.relate_bsp1.klu.idx == relate_bsp1.klu.idx

    def add_feat(self, inp1: Union[str, Dict[str, float], Dict[str, Optional[float]], 'CFeatures'], inp2: Optional[float] = None):
        # 向买卖点添加特征指标
        # 可接受单个特征名+值，或一个特征字典，或另一个CFeatures对象
        self.features.add_feat(inp1, inp2)