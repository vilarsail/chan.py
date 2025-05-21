import inspect
from typing import Dict, List, Literal, Optional, Tuple, Union

# 导入 matplotlib 绘图库
import matplotlib.pyplot as plt
# 导入 matplotlib 轴对象和图形对象
plt.rcParams['font.sans-serif'] = ['Songti SC']  # 苹果系统自带宋体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
from matplotlib.axes import Axes
from matplotlib.figure import Figure
# 导入用于绘制矩形的 Patch 对象
from matplotlib.patches import Rectangle

# 导入 Chan 对象，包含不同级别的缠论结构
from Chan import CChan
# 导入缠论枚举类型：笔方向、分型类型、K线类型、K线方向、趋势类型
from Common.CEnum import BI_DIR, FX_TYPE, KL_TYPE, KLINE_DIR, TREND_TYPE
# 导入缠论异常类和错误码
from Common.ChanException import CChanException, ErrCode
# 导入时间处理类
from Common.CTime import CTime
# 导入 Demark 指标引擎和索引类型
from Math.Demark import T_DEMARK_INDEX, CDemarkEngine

# 导入绘图元数据类：笔元数据、缠论绘图元数据、中枢元数据
from .PlotMeta import CBi_meta, CChanPlotMeta, CZS_meta


# 辅助函数：格式化绘图配置，兼容不带 `plot_` 前缀的情况
def reformat_plot_config(plot_config: Dict[str, bool]):
    """
    兼容不填写`plot_`前缀的情况
    将字典中所有键加上 "plot_" 前缀，如果它们还没有的话
    """
    def _format(s):
        # 如果字符串 s 不以 "plot_" 开头，则在其前面加上 "plot_"
        return s if s.startswith("plot_") else f"plot_{s}"

    # 创建一个新的字典，键是格式化后的原键，值保持不变
    return {_format(k): v for k, v in plot_config.items()}


# 辅助函数：解析单个级别的绘图配置
def parse_single_lv_plot_config(plot_config: Union[str, dict, list]) -> Dict[str, bool]:
    """
    返回单一级别的plot_config配置
    支持字符串（逗号分隔），字典，列表作为输入
    """
    # 如果输入是字典，直接格式化后返回
    if isinstance(plot_config, dict):
        return reformat_plot_config(plot_config)
    # 如果输入是字符串，按逗号分割，创建字典，格式化后返回
    elif isinstance(plot_config, str):
        # 将字符串分割成列表，去除首尾空白，转为小写，创建字典，值为 True
        return reformat_plot_config(dict([(k.strip().lower(), True) for k in plot_config.split(",")]))
    # 如果输入是列表，创建字典，值为 True，格式化后返回
    elif isinstance(plot_config, list):
        # 遍历列表元素，去除首尾空白，转为小写，创建字典，值为 True
        return reformat_plot_config(dict([(k.strip().lower(), True) for k in plot_config]))
    # 如果输入类型不支持，抛出异常
    else:
        raise CChanException("plot_config only support list/str/dict", ErrCode.PLOT_ERR)


# 辅助函数：解析多级别的绘图配置
def parse_plot_config(plot_config: Union[str, dict, list], lv_list: List[KL_TYPE]) -> Dict[KL_TYPE, Dict[str, bool]]:
    """
    支持多种输入格式的plot_config，解析为Dict[KL_TYPE, Dict[str, bool]]格式
    支持：
        - 传入字典: key为级别KL_TYPE或字符串，value为该级别的plot_config (str/dict/list)
        - 传入字符串或数组: 所有级别使用相同的配置
    """
    # 如果输入是字典
    if isinstance(plot_config, dict):
        # 检查字典的所有键是否都是字符串 (单层字典，所有级别使用相同的配置)
        if all(isinstance(_key, str) for _key in plot_config.keys()):
            # 为每个级别应用相同的配置
            return {lv: parse_single_lv_plot_config(plot_config) for lv in lv_list}
        # 检查字典的所有键是否都是 KL_TYPE (按级别配置)
        elif all(isinstance(_key, KL_TYPE) for _key in plot_config.keys()):
            # 断言：所有级别必须在配置中
            for lv in lv_list:
                assert lv in plot_config
            # 为每个级别解析其对应的配置
            return {lv: parse_single_lv_plot_config(plot_config[lv]) for lv in lv_list}
        # 字典键类型不支持，抛出异常
        else:
            raise CChanException("plot_config if is dict, key must be str/KL_TYPE", ErrCode.PLOT_ERR)
    # 如果输入是字符串或列表 (所有级别使用相同的配置)
    # 为每个级别解析相同的配置
    return {lv: parse_single_lv_plot_config(plot_config) for lv in lv_list}


# 辅助函数：设置 X 轴刻度
def set_x_tick(ax, x_limits, tick, x_tick_num: int):
    # 断言：X 轴刻度数量必须大于1
    assert x_tick_num > 1
    # 设置 X 轴的显示范围
    ax.set_xlim(x_limits[0], x_limits[1]+1)
    # 设置 X 轴的刻度位置
    # 刻度位置从 x_limits[0] 到 x_limits[1]，步长根据范围和刻度数量计算
    ax.set_xticks(range(x_limits[0], x_limits[1], max([1, int((x_limits[1]-x_limits[0])/float(x_tick_num))])))
    # 设置 X 轴刻度标签，使用 tick 列表中的日期字符串，并旋转标签
    ax.set_xticklabels([tick[i] for i in ax.get_xticks()], rotation=20)


# 辅助函数：计算 Y 轴显示范围
def cal_y_range(meta: CChanPlotMeta, ax):
    # 获取当前 X 轴的起始位置
    x_begin = ax.get_xlim()[0]
    # 初始化 Y 轴最小/最大值
    y_min = float("inf")
    y_max = float("-inf")
    # 遍历 K 线组合元数据列表
    for klc_meta in meta.klc_list:
        # 如果 K 线组合的最后一个 K 线索引小于 X 轴起始位置，则不绘制范围外的数据，跳过
        if klc_meta.klu_list[-1].idx < x_begin:
            continue
        # 更新 Y 轴最大值
        if klc_meta.high > y_max:
            y_max = klc_meta.high
        # 更新 Y 轴最小值
        if klc_meta.low < y_min:
            y_min = klc_meta.low
    # 返回计算出的 Y 轴范围
    return (y_min, y_max)


# 辅助函数：创建 Matplotlib Figure 和 Axes 对象
def create_figure(plot_macd: Dict[KL_TYPE, bool], figure_config, lv_lst: List[KL_TYPE]) -> Tuple[Figure, Dict[KL_TYPE, List[Axes]]]:
    """
    根据配置创建Figure和Axes对象，并返回按级别组织的Axes字典
    返回：
        - Figure 对象
        - Dict[KL_TYPE, List[Axes]]: 如果Axes长度为1, 说明不需要画macd, 否则需要
    """
    # 默认 Figure 宽度和高度
    default_w, default_h = 24, 10
    # MACD 子图的高度比例
    macd_h_ration = figure_config.get('macd_h', 0.3)
    # Figure 宽度和高度 (从配置获取，否则使用默认值)
    w = figure_config.get('w', default_w)
    h = figure_config.get('h', default_h)

    # 计算总高度和子图高度比例列表
    total_h = 0
    gridspec_kw = []
    sub_pic_cnt = 0 # 子图总数量
    # 遍历所有需要绘制的级别
    for lv in lv_lst:
        # 如果该级别需要绘制 MACD
        if plot_macd[lv]:
            # 总高度增加 K线/结构图 高度 + MACD 图高度
            total_h += h*(1+macd_h_ration)
            # 添加 K线/结构图 和 MACD 图的高度比例
            gridspec_kw.extend((1, macd_h_ration))
            sub_pic_cnt += 2 # 子图数量增加2
        else:
            # 如果不需要绘制 MACD
            total_h += h
            # 添加 K线/结构图 的高度比例
            gridspec_kw.append(1)
            sub_pic_cnt += 1 # 子图数量增加1
    # 创建 Figure 和 Axes 对象
    figure, axes = plt.subplots(
        sub_pic_cnt, # 子图总行数
        1, # 子图总列数
        figsize=(w, total_h), # Figure 大小
        gridspec_kw={'height_ratios': gridspec_kw} # 子图高度比例设置
    )
    # 处理只有一个子图的情况 (例如只有一个级别且不需要画 MACD)
    try:
        axes[0]
    except Exception: # 只有一个级别，且不需要画macd
        # 将 axes 转换为列表，以便后续迭代
        axes = [axes]

    # 将 Axes 对象按级别组织到字典中
    axes_dict: Dict[KL_TYPE, List[Axes]] = {}
    idx = 0 # 当前 Axes 索引
    for lv in lv_lst:
        # 如果该级别需要绘制 MACD
        if plot_macd[lv]:
            # 将当前 Axes 和下一个 Axes 分配给该级别 (K线/结构图 + MACD 图)
            axes_dict[lv] = axes[idx: idx+2]  # type: ignore
            idx += 2 # 索引前进2
        else:
            # 如果不需要绘制 MACD
            # 将当前 Axes 分配给该级别 (K线/结构图)
            axes_dict[lv] = [axes[idx]]  # type: ignore
            idx += 1 # 索引前进1
    # 断言：确保所有 Axes 都被分配到字典中
    assert idx == len(axes)
    # 返回 Figure 和 Axes 字典
    return figure, axes_dict


# 辅助函数：计算 X 轴显示范围的起始和结束索引
def cal_x_limit(meta: CChanPlotMeta, x_range):
    # 获取 K 线单位的总数量
    X_LEN = meta.klu_len
    # 如果指定了 x_range (要显示的 K 线数量) 且总 K 线数量大于 x_range
    if x_range and X_LEN > x_range:
        # X 轴范围从倒数 x_range 个 K 线开始
        return [X_LEN - x_range, X_LEN - 1]
    else:
        # 否则，显示所有 K 线
        return [0, X_LEN - 1]


# 辅助函数：设置网格线
def set_grid(ax, config):
    # 如果 config 为 None，不设置网格线
    if config is None:
        return
    # 如果 config 为 "xy"，设置主网格线
    if config == "xy":
        ax.grid(True)
        return
    # 如果 config 为 "x" 或 "y"，设置指定轴向的网格线
    if config in ("x", "y"):
        ax.grid(True, axis=config)
        return
    # 如果 config 不支持，抛出异常
    raise CChanException(f"unsupport grid config={config}", ErrCode.PLOT_ERR)


# 辅助函数：获取需要绘制的缠论元数据列表
def GetPlotMeta(chan: CChan, figure_config) -> List[CChanPlotMeta]:
    # 为 Chan 对象中的每个级别创建一个 CChanPlotMeta 对象
    plot_metas = [CChanPlotMeta(chan[kl_type]) for kl_type in chan.lv_list]
    # 如果配置只绘制顶层级别，则只保留第一个元数据对象
    if figure_config.get("only_top_lv", False):
        plot_metas = [plot_metas[0]]
    # 返回需要绘制的缠论元数据列表
    return plot_metas


# 绘图驱动类
class CPlotDriver:
    # 类的初始化方法
    def __init__(self, chan: CChan, plot_config: Union[str, dict, list] = '', plot_para=None):
        # 初始化 plot_para
        if plot_para is None:
            plot_para = {}
        # 从 plot_para 中获取 figure 配置
        figure_config: dict = plot_para.get('figure', {})

        # 解析绘图配置
        plot_config = parse_plot_config(plot_config, chan.lv_list)
        # 获取需要绘制的缠论元数据列表
        plot_metas = GetPlotMeta(chan, figure_config)
        # 获取需要绘制的级别列表 (可能因为 only_top_lv 而减少)
        self.lv_lst = chan.lv_list[:len(plot_metas)]

        # 计算实际的 X 轴范围
        x_range = self.GetRealXrange(figure_config, plot_metas[0])
        # 判断每个级别是否需要绘制 MACD
        plot_macd: Dict[KL_TYPE, bool] = {kl_type: conf.get("plot_macd", False) for kl_type, conf in plot_config.items()}
        # 创建 Figure 和 Axes 对象
        self.figure, axes = create_figure(plot_macd, figure_config, self.lv_lst)

        # 子级别绘图起始索引的控制变量
        sseg_begin = 0 # 子级别线段起始索引
        # 从 plot_para 获取线段子级别绘制数量配置
        slv_seg_cnt = plot_para.get('seg', {}).get('sub_lv_cnt', None)
        sbi_begin = 0 # 子级别笔起始索引
        # 从 plot_para 获取笔子级别绘制数量配置
        slv_bi_cnt = plot_para.get('bi', {}).get('sub_lv_cnt', None)
        srange_begin = 0 # 子级别范围起始索引
        # 断言：seg_sub_lv_cnt 和 bi_sub_lv_cnt 不能同时设置
        assert slv_seg_cnt is None or slv_bi_cnt is None, "you can set at most one of seg_sub_lv_cnt/bi_sub_lv_cnt"

        # 遍历需要绘制的缠论元数据和对应的级别
        for meta, lv in zip(plot_metas, self.lv_lst):  # type: ignore
            # 获取当前级别的 K线/结构图 Axes
            ax = axes[lv][0]
            # 获取当前级别的 MACD Axes (如果需要绘制)
            ax_macd = None if len(axes[lv]) == 1 else axes[lv][1]
            # 设置网格线
            set_grid(ax, figure_config.get("grid", "xy"))
            # 设置 Axes 标题
            ax.set_title(f"{chan.code}-{chan.get_stock_name()}/{lv.name.split('K_')[1]}", fontsize=16, loc='left', color='r')

            # 计算当前 Axes 的 X 轴范围
            x_limits = cal_x_limit(meta, x_range)
            # 如果当前级别不是最高级别，根据子级别配置调整 X 轴起始位置
            if lv != self.lv_lst[0]:
                if sseg_begin != 0 or sbi_begin != 0:
                    x_limits[0] = max(sseg_begin, sbi_begin)
                elif srange_begin != 0:
                    x_limits[0] = srange_begin
            # 设置 X 轴刻度
            set_x_tick(ax, x_limits, meta.datetick, figure_config.get('x_tick_num', 10))
            # 如果存在 MACD Axes，也设置其 X 轴刻度
            if ax_macd:
                set_x_tick(ax_macd, x_limits, meta.datetick, figure_config.get('x_tick_num', 10))
            # 计算当前 Axes 的 Y 轴范围 (需要在设置 X 轴刻度后计算)
            self.y_min, self.y_max = cal_y_range(meta, ax)  # 需要先设置 x_tick后计算

            # 调用 DrawElement 方法绘制各个图表元素
            self.DrawElement(plot_config[lv], meta, ax, lv, plot_para, ax_macd, x_limits)

            # 如果当前级别不是最低级别，计算下一级别的子级别起始索引
            if lv != self.lv_lst[-1]:
                # 如果设置了线段子级别数量，计算下一级别线段的起始索引
                if slv_seg_cnt is not None:
                    sseg_begin = meta.sub_last_kseg_start_idx(slv_seg_cnt)
                # 如果设置了笔子级别数量，计算下一级别笔的起始索引
                if slv_bi_cnt is not None:
                    sbi_begin = meta.sub_last_kbi_start_idx(slv_bi_cnt)
                # 如果设置了 X 轴范围，计算下一级别的范围起始索引
                if x_range != 0:
                    srange_begin = meta.sub_range_start_idx(x_range)

            # 设置当前 Axes 的 Y 轴显示范围
            ax.set_ylim(self.y_min, self.y_max)

    # 获取实际的 X 轴显示范围 (K线数量)
    def GetRealXrange(self, figure_config, meta: CChanPlotMeta):
        # 从 figure_config 获取各种 X 轴范围设置
        x_range = figure_config.get("x_range", 0) # 直接指定 K 线数量
        bi_cnt = figure_config.get("x_bi_cnt", 0) # 按笔数量指定
        seg_cnt = figure_config.get("x_seg_cnt", 0) # 按线段数量指定
        x_begin_date = figure_config.get("x_begin_date", 0) # 按起始日期指定
        # 断言：这些 X 轴范围设置只能设置其中一个
        if x_range != 0:
            assert bi_cnt == 0 and seg_cnt == 0 and x_begin_date == 0, "x_range/x_bi_cnt/x_seg_cnt/x_begin_date can not be set at the same time"
            return x_range
        if bi_cnt != 0:
            assert x_range == 0 and seg_cnt == 0 and x_begin_date == 0, "x_range/x_bi_cnt/x_seg_cnt/x_begin_date can not be set at the same time"
            X_LEN = meta.klu_len
            # 如果笔数量小于指定的 bi_cnt，返回 0 (表示显示所有)
            if len(meta.bi_list) < bi_cnt:
                return 0
            # 计算 X 轴范围：总 K 线数量 - 倒数 bi_cnt 个笔的起始 K 线索引
            x_range = X_LEN-meta.bi_list[-bi_cnt].begin_x
            return x_range
        if seg_cnt != 0:
            assert x_range == 0 and bi_cnt == 0 and x_begin_date == 0, "x_range/x_bi_cnt/x_seg_cnt/x_begin_date can not be set at the same time"
            X_LEN = meta.klu_len
            # 如果线段数量小于指定的 seg_cnt，返回 0
            if len(meta.seg_list) < seg_cnt:
                return 0
            # 计算 X 轴范围：总 K 线数量 - 倒数 seg_cnt 个线段的起始 K 线索引
            x_range = X_LEN-meta.seg_list[-seg_cnt].begin_x
            return x_range
        if x_begin_date != 0:
            assert x_range == 0 and bi_cnt == 0 and seg_cnt == 0, "x_range/x_bi_cnt/x_seg_cnt/x_begin_date can not be set at the same time"
            x_range = 0
            # 从日期刻度列表中倒序查找起始日期，计算需要显示的 K 线数量
            for date_tick in meta.datetick[::-1]:
                if date_tick >= x_begin_date:
                    x_range += 1
                else:
                    break
            return x_range
        # 如果没有设置任何范围，返回 0 (表示显示所有)
        return x_range

    # 绘制图表元素的核心方法
    def DrawElement(self, plot_config: Dict[str, bool], meta: CChanPlotMeta, ax: Axes, lv, plot_para, ax_macd: Optional[Axes], x_limits):
        # 根据 plot_config 字典调用对应的绘制方法
        if plot_config.get("plot_kline", False):
            self.draw_klu(meta, ax, **plot_para.get('kl', {}))
        if plot_config.get("plot_kline_combine", False):
            self.draw_klc(meta, ax, **plot_para.get('klc', {}))
        if plot_config.get("plot_bi", False):
            self.draw_bi(meta, ax, lv, **plot_para.get('bi', {}))
        if plot_config.get("plot_seg", False):
            self.draw_seg(meta, ax, lv, **plot_para.get('seg', {}))
        if plot_config.get("plot_segseg", False):
            self.draw_segseg(meta, ax, **plot_para.get('segseg', {}))
        if plot_config.get("plot_eigen", False):
            self.draw_eigen(meta, ax, **plot_para.get('eigen', {}))
        if plot_config.get("plot_segeigen", False):
            self.draw_segeigen(meta, ax, **plot_para.get('segeigen', {}))
        if plot_config.get("plot_zs", False):
            self.draw_zs(meta, ax, **plot_para.get('zs', {}))
        if plot_config.get("plot_segzs", False):
            self.draw_segzs(meta, ax, **plot_para.get('segzs', {}))
        if plot_config.get("plot_macd", False):
            # 断言：如果需要绘制 MACD，则 ax_macd 必须存在
            assert ax_macd is not None
            self.draw_macd(meta, ax_macd, x_limits, **plot_para.get('macd', {}))
        if plot_config.get("plot_mean", False):
            self.draw_mean(meta, ax, **plot_para.get('mean', {}))
        if plot_config.get("plot_channel", False):
            self.draw_channel(meta, ax, **plot_para.get('channel', {}))
        if plot_config.get("plot_boll", False):
            self.draw_boll(meta, ax, **plot_para.get('boll', {}))
        if plot_config.get("plot_bsp", False):
            self.draw_bs_point(meta, ax, **plot_para.get('bsp', {}))
        if plot_config.get("plot_segbsp", False):
            self.draw_seg_bs_point(meta, ax, **plot_para.get('seg_bsp', {}))
        if plot_config.get("plot_demark", False):
            self.draw_demark(meta, ax, **plot_para.get('demark', {}))
        if plot_config.get("plot_marker", False):
            self.draw_marker(meta, ax, **plot_para.get('marker', {'markers': {}}))
        if plot_config.get("plot_rsi", False):
            # 在副坐标轴上绘制 RSI
            self.draw_rsi(meta, ax.twinx(), **plot_para.get('rsi', {}))
        if plot_config.get("plot_kdj", False):
            # 在副坐标轴上绘制 KDJ
            self.draw_kdj(meta, ax.twinx(), **plot_para.get('kdj', {}))

    # 显示所有绘制函数的帮助信息 (用于生成文档)
    def ShowDrawFuncHelper(self):
        # 写README的时候显示所有画图函数的参数和默认值
        # 遍历类中的所有方法
        for func in dir(self):
            # 如果方法名不以 "draw_" 开头，跳过
            if not func.startswith("draw_"):
                continue
            # 对以 "draw_" 开头的方法调用 show_func_helper
            show_func_helper(eval(f'self.{func}'))

    # 将 Figure 保存到图片文件
    def save2img(self, path):
        # 保存 Figure 到指定路径，bbox_inches='tight' 确保保存时不留白边
        plt.savefig(path, bbox_inches='tight')

    # 绘制 K 线单位 (KLU)
    def draw_klu(self, meta: CChanPlotMeta, ax: Axes, width=0.4, rugd=True, plot_mode="kl"):
        # rugd: red up green down (上涨红色，下跌绿色)
        up_color = 'r' if rugd else 'g' # 上涨颜色
        down_color = 'g' if rugd else 'r' # 下跌颜色

        # 获取当前 X 轴的起始位置
        x_begin = ax.get_xlim()[0]
        _x, _y = [], [] # 存储绘制点模式的坐标

        # 遍历 K 线单位
        for kl in meta.klu_iter():
            i = kl.idx # K 线单位索引
            # 如果 K 线单位的结束位置 (索引 + 宽度) 小于 X 轴起始位置，则不绘制范围外的，跳过
            if i+width < x_begin:
                continue  # 不绘制范围外的
            # 根据 plot_mode 绘制不同类型的 K 线图
            if plot_mode == "kl": # 绘制蜡烛图
                # 如果收盘价大于开盘价 (阳线)
                if kl.close > kl.open:
                    # 绘制矩形 (实体)
                    ax.add_patch(
                        Rectangle((i - width / 2, kl.open), width, kl.close - kl.open, fill=False, color=up_color))
                    # 绘制下影线
                    ax.plot([i, i], [kl.low, kl.open], up_color)
                    # 绘制上影线
                    ax.plot([i, i], [kl.close, kl.high], up_color)
                else:  # 绘制阴线
                    # 绘制矩形 (实体)
                    ax.add_patch(Rectangle((i - width / 2, kl.open), width, kl.close - kl.open, color=down_color))
                    # 绘制影线 (阴线影线颜色与实体颜色一致)
                    ax.plot([i, i], [kl.low, kl.high], color=down_color)
            # 绘制收盘价线
            elif plot_mode in "close":
                _y.append(kl.close)
                _x.append(i)
            # 绘制最高价线
            elif plot_mode == "high":
                _y.append(kl.high)
                _x.append(i)
            # 绘制最低价线
            elif plot_mode == "low":
                _y.append(kl.low)
                _x.append(i)
            # 绘制开盘价线
            elif plot_mode == "open":
                _y.append(kl.low)
                _x.append(i)
            # 不支持的 plot_mode 抛出异常
            else:
                raise CChanException(f"unknow plot mode={plot_mode}, must be one of kl/close/open/high/low", ErrCode.PLOT_ERR)
        # 如果以点模式绘制了数据，则连接这些点形成线
        if _x:
            ax.plot(_x, _y)

    # 绘制 K 线组合 (KLC)
    def draw_klc(self, meta: CChanPlotMeta, ax: Axes, width=0.4, plot_single_kl=True):
        # 定义不同类型 K 线组合的颜色
        color_type = {FX_TYPE.TOP: 'red', FX_TYPE.BOTTOM: 'blue', KLINE_DIR.UP: 'green', KLINE_DIR.DOWN: 'green'}
        # 获取当前 X 轴的起始位置
        x_begin = ax.get_xlim()[0]

        # 遍历 K 线组合元数据
        for klc_meta in meta.klc_list:
            # 如果 K 线组合的结束位置 (最后一个 K 线索引 + 宽度) 小于 X 轴起始位置，跳过
            if klc_meta.klu_list[-1].idx+width < x_begin:
                continue  # 不绘制范围外的
            # 如果是单根 K 线组成的 K 线组合，且配置不绘制单根 K 线，跳过
            if klc_meta.end_idx == klc_meta.begin_idx and not plot_single_kl:
                continue
            # 绘制代表 K 线组合的矩形
            ax.add_patch(
                Rectangle(
                    (klc_meta.begin_idx - width, klc_meta.low), # 矩形左下角坐标
                    klc_meta.end_idx - klc_meta.begin_idx + width*2, # 矩形宽度 (包括左右各 width 的边距)
                    klc_meta.high - klc_meta.low, # 矩形高度
                    fill=False, # 不填充
                    color=color_type[klc_meta.type])) # 颜色根据 K 线组合类型确定

    # 绘制笔
    def draw_bi(
        self,
        meta: CChanPlotMeta,
        ax: Axes,
        lv, # 级别
        color='black', # 笔的颜色
        show_num=False, # 是否显示笔的序号
        num_fontsize=15, # 笔序号字体大小
        num_color="red", # 笔序号颜色
        sub_lv_cnt=None, # 子级别绘制笔的数量
        facecolor='green', # 子级别区域填充颜色
        alpha=0.1, # 子级别区域填充透明度
        disp_end=False, # 是否显示笔的结束价格
        end_color='black', # 结束价格颜色
        end_fontsize=10, # 结束价格字体大小
    ):
        # 获取当前 X 轴的起始位置
        x_begin = ax.get_xlim()[0]
        # 遍历笔列表
        for bi_idx, bi in enumerate(meta.bi_list):
            # 如果笔的结束位置小于 X 轴起始位置，跳过
            if bi.end_x < x_begin:
                continue
            # 绘制笔的线条
            plot_bi_element(bi, ax, color)
            # 如果需要显示笔的序号且笔的起始位置在 X 轴范围内
            if show_num and bi.begin_x >= x_begin:
                # 在笔的中心位置绘制序号
                ax.text((bi.begin_x+bi.end_x)/2, (bi.begin_y+bi.end_y)/2, f'{bi.idx}', fontsize=num_fontsize, color=num_color)

            # 如果需要显示笔的结束价格
            if disp_end:
                # 调用 bi_text 辅助函数绘制结束价格文本
                bi_text(bi_idx, ax, bi, end_fontsize, end_color)
        # 如果设置了子级别绘制笔的数量，且当前级别不是最低级别
        if sub_lv_cnt is not None and len(self.lv_lst) > 1 and lv != self.lv_lst[-1]:
            # 如果子级别数量大于等于总笔数量，则不限制
            if sub_lv_cnt >= len(meta.bi_list):
                return
            else:
                # 计算子级别区域的起始 K 线索引
                begin_idx = meta.bi_list[-sub_lv_cnt].begin_x
            # 获取 Y 轴范围和 X 轴结束位置
            y_begin, y_end = ax.get_ylim()
            x_end = int(ax.get_xlim()[1])
            # 填充子级别区域的背景
            ax.fill_between(range(begin_idx, x_end + 1), y_begin, y_end, facecolor=facecolor, alpha=alpha)

    # 绘制线段
    def draw_seg(
        self,
        meta: CChanPlotMeta,
        ax: Axes,
        lv, # 级别
        width=5, # 线段线条宽度
        color="g", # 线段颜色
        sub_lv_cnt=None, # 子级别绘制线段的数量
        facecolor='green', # 子级别区域填充颜色
        alpha=0.1, # 子级别区域填充透明度
        disp_end=False, # 是否显示线段的结束价格
        end_color='g', # 结束价格颜色
        end_fontsize=13, # 结束价格字体大小
        plot_trendline=False, # 是否绘制线段的趋势线
        trendline_color='r', # 趋势线颜色
        trendline_width=3, # 趋势线宽度
        show_num=False, # 是否显示线段序号
        num_fontsize=25, # 线段序号字体大小
        num_color="blue", # 线段序号颜色
    ):
        # 获取当前 X 轴的起始位置
        x_begin = ax.get_xlim()[0]

        # 遍历线段元数据列表
        for seg_idx, seg_meta in enumerate(meta.seg_list):
            # 如果线段的结束位置小于 X 轴起始位置，跳过
            if seg_meta.end_x < x_begin:
                continue
            # 根据线段是否确定选择实线或虚线绘制
            if seg_meta.is_sure:
                ax.plot([seg_meta.begin_x, seg_meta.end_x], [seg_meta.begin_y, seg_meta.end_y], color=color, linewidth=width)
            else:
                ax.plot([seg_meta.begin_x, seg_meta.end_x], [seg_meta.begin_y, seg_meta.end_y], color=color, linewidth=width, linestyle='dashed')
            # 如果需要显示线段结束价格
            if disp_end:
                # 调用 bi_text 辅助函数绘制结束价格文本
                bi_text(seg_idx, ax, seg_meta, end_fontsize, end_color)
            # 如果需要绘制趋势线
            if plot_trendline:
                # 如果存在支撑趋势线，格式化后绘制
                if seg_meta.tl.get('support'):
                    tl_meta = seg_meta.format_tl(seg_meta.tl['support'])
                    ax.plot([tl_meta[0], tl_meta[2]], [tl_meta[1], tl_meta[3]], color=trendline_color, linewidth=trendline_width)
                # 如果存在阻力趋势线，格式化后绘制
                if seg_meta.tl.get('resistance'):
                    tl_meta = seg_meta.format_tl(seg_meta.tl['resistance'])
                    ax.plot([tl_meta[0], tl_meta[2]], [tl_meta[1], tl_meta[3]], color=trendline_color, linewidth=trendline_width)
            # 如果需要显示线段序号且线段起始位置在 X 轴范围内
            if show_num and seg_meta.begin_x >= x_begin:
                # 在线段中心位置绘制序号
                ax.text((seg_meta.begin_x+seg_meta.end_x)/2, (seg_meta.begin_y+seg_meta.end_y)/2, f'{seg_meta.idx}', fontsize=num_fontsize, color=num_color)
        # 如果设置了子级别绘制线段数量，且当前级别不是最低级别
        if sub_lv_cnt is not None and len(self.lv_lst) > 1 and lv != self.lv_lst[-1]:
            # 如果子级别数量大于等于总线段数量，不限制
            if sub_lv_cnt >= len(meta.seg_list):
                return
            else:
                # 计算子级别区域的起始 K 线索引
                begin_idx = meta.seg_list[-sub_lv_cnt].begin_x
            # 获取 Y 轴范围和 X 轴结束位置
            y_begin, y_end = ax.get_ylim()
            x_end = int(ax.get_xlim()[1])
            # 填充子级别区域背景
            ax.fill_between(range(begin_idx, x_end+1), y_begin, y_end, facecolor=facecolor, alpha=alpha)

    # 绘制线段中枢
    def draw_segseg(
        self,
        meta: CChanPlotMeta,
        ax: Axes,
        width=7, # 线段中枢线条宽度
        color="brown", # 线段中枢颜色
        disp_end=False, # 是否显示线段中枢的结束价格
        end_color='brown', # 结束价格颜色
        end_fontsize=15, # 结束价格字体大小
        show_num=False, # 是否显示线段中枢序号
        num_fontsize=30, # 线段中枢序号字体大小
        num_color="blue", # 线段中枢序号颜色
    ):
        # 获取当前 X 轴的起始位置
        x_begin = ax.get_xlim()[0]

        # 遍历线段中枢列表 (实际上是更高一级别的线段列表，这里命名有点误导)
        for seg_idx, seg_meta in enumerate(meta.segseg_list):
            # 如果线段中枢结束位置小于 X 轴起始位置，跳过
            if seg_meta.end_x < x_begin:
                continue
            # 根据线段中枢是否确定选择实线或虚线绘制
            if seg_meta.is_sure:
                ax.plot([seg_meta.begin_x, seg_meta.end_x], [seg_meta.begin_y, seg_meta.end_y], color=color, linewidth=width)
            else:
                ax.plot([seg_meta.begin_x, seg_meta.end_x], [seg_meta.begin_y, seg_meta.end_y], color=color, linewidth=width, linestyle='dashed')
            # 如果需要显示结束价格
            if disp_end:
                # 如果是第一个线段中枢，显示起始价格
                if seg_idx == 0:
                    ax.text(
                        seg_meta.begin_x,
                        seg_meta.begin_y,
                        f'{seg_meta.begin_y:.2f}',
                        fontsize=end_fontsize,
                        color=end_color,
                        verticalalignment="top" if seg_meta.dir == BI_DIR.UP else "bottom", # 根据方向调整垂直对齐
                        horizontalalignment='center')
                # 显示结束价格
                ax.text(
                    seg_meta.end_x,
                    seg_meta.end_y,
                    f'{seg_meta.end_y:.2f}',
                    fontsize=end_fontsize,
                    color=end_color,
                    verticalalignment="top" if seg_meta.dir == BI_DIR.DOWN else "bottom", # 根据方向调整垂直对齐
                    horizontalalignment='center')
            # 如果需要显示序号且线段中枢起始位置在 X 轴范围内
            if show_num and seg_meta.begin_x >= x_begin:
                # 在线段中枢中心位置绘制序号
                ax.text((seg_meta.begin_x+seg_meta.end_x)/2, (seg_meta.begin_y+seg_meta.end_y)/2, f'{seg_meta.idx}', fontsize=num_fontsize, color=num_color)

    # 辅助函数：绘制单个特征序列分型
    def plot_single_eigen(self, eigenfx_meta, ax, color_top, color_bottom, aplha, only_peak):
        # 获取当前 X 轴起始位置
        x_begin = ax.get_xlim()[0]
        # 根据分型类型选择颜色
        color = color_top if eigenfx_meta.fx == FX_TYPE.TOP else color_bottom
        # 遍历特征序列分型的组成元素
        for idx, eigen_meta in enumerate(eigenfx_meta.ele):
            # 如果元素结束位置小于 X 轴起始位置，跳过
            if eigen_meta.begin_x+eigen_meta.w < x_begin:
                continue
            # 如果只绘制峰值/谷值元素且当前元素不是第二个 (通常第二个元素是峰值/谷值)，跳过
            if only_peak and idx != 1:
                continue
            # 绘制代表特征序列分型元素的矩形
            ax.add_patch(
                Rectangle(
                    (eigen_meta.begin_x, eigen_meta.begin_y), # 矩形左下角坐标
                    eigen_meta.w, # 矩形宽度
                    eigen_meta.h, # 矩形高度
                    fill=True, # 填充矩形
                    alpha=aplha, # 透明度
                    color=color # 颜色
                )
            )

    # 绘制笔的特征序列分型
    def draw_eigen(self, meta: CChanPlotMeta, ax: Axes, color_top="r", color_bottom="b", aplha=0.5, only_peak=False):
        # 遍历笔的特征序列分型列表
        for eigenfx_meta in meta.eigenfx_lst:
            # 调用 plot_single_eigen 绘制单个特征序列分型
            self.plot_single_eigen(eigenfx_meta, ax, color_top, color_bottom, aplha, only_peak)

    # 绘制线段的特征序列分型
    def draw_segeigen(self, meta: CChanPlotMeta, ax: Axes, color_top="r", color_bottom="b", aplha=0.5, only_peak=False):
        # 遍历线段的特征序列分型列表
        for eigenfx_meta in meta.seg_eigenfx_lst:
            # 调用 plot_single_eigen 绘制单个特征序列分型
            self.plot_single_eigen(eigenfx_meta, ax, color_top, color_bottom, aplha, only_peak)

    # 绘制笔中枢
    def draw_zs(
        self,
        meta: CChanPlotMeta,
        ax: Axes,
        color='orange', # 中枢颜色
        linewidth=2, # 中枢边框线宽
        sub_linewidth=0.5, # 子中枢边框线宽
        show_text=False, # 是否显示中枢文本信息
        fontsize=14, # 文本字体大小
        text_color='orange', # 文本颜色
        draw_one_bi_zs=False, # 是否绘制单笔构成的中枢
    ):
        # 确保线宽至少为2
        linewidth = max(linewidth, 2)
        # 获取当前 X 轴起始位置
        x_begin = ax.get_xlim()[0]
        # 遍历中枢元数据列表
        for zs_meta in meta.zs_lst:
            # 如果不绘制单笔中枢且当前是单笔中枢，跳过
            if not draw_one_bi_zs and zs_meta.is_onebi_zs:
                continue
            # 如果中枢结束位置小于 X 轴起始位置，跳过
            if zs_meta.begin+zs_meta.w < x_begin:
                continue
            # 根据中枢是否确定选择实线或虚线绘制边框
            line_style = '-' if zs_meta.is_sure else '--'
            # 绘制中枢矩形边框
            ax.add_patch(Rectangle((zs_meta.begin, zs_meta.low), zs_meta.w, zs_meta.h, fill=False, color=color, linewidth=linewidth, linestyle=line_style))
            # 遍历子中枢并绘制边框
            for sub_zs_meta in zs_meta.sub_zs_lst:
                ax.add_patch(Rectangle((sub_zs_meta.begin, sub_zs_meta.low), sub_zs_meta.w, sub_zs_meta.h, fill=False, color=color, linewidth=sub_linewidth, linestyle=line_style))
            # 如果需要显示中枢文本信息
            if show_text:
                # 调用 add_zs_text 辅助函数绘制中枢文本
                add_zs_text(ax, zs_meta, fontsize, text_color)
                # 绘制子中枢文本
                for sub_zs_meta in zs_meta.sub_zs_lst:
                    add_zs_text(ax, sub_zs_meta, fontsize, text_color)

    # 绘制线段中枢 (segzs) - 注意这里的 segzs 应该是指更高一级别的中枢，通常是线段构成的新中枢
    def draw_segzs(self, meta: CChanPlotMeta, ax: Axes, color='red', linewidth=10, sub_linewidth=4):
        # 确保线宽至少为2
        linewidth = max(linewidth, 2)
        # 获取当前 X 轴起始位置
        x_begin = ax.get_xlim()[0]
        # 遍历线段中枢列表
        for zs_meta in meta.segzs_lst:
            # 如果线段中枢结束位置小于 X 轴起始位置，跳过
            if zs_meta.begin+zs_meta.w < x_begin:
                continue
            # 根据线段中枢是否确定选择实线或虚线绘制边框
            line_style = '-' if zs_meta.is_sure else '--'
            # 绘制线段中枢矩形边框
            ax.add_patch(Rectangle((zs_meta.begin, zs_meta.low), zs_meta.w, zs_meta.h, fill=False, color=color, linewidth=linewidth, linestyle=line_style))
            # 遍历子线段中枢并绘制边框
            for sub_zs_meta in zs_meta.sub_zs_lst:
                ax.add_patch(Rectangle((sub_zs_meta.begin, sub_zs_meta.low), sub_zs_meta.w, sub_zs_meta.h, fill=False, color=color, linewidth=sub_linewidth, linestyle=line_style))

    # 绘制 MACD 指标
    def draw_macd(self, meta: CChanPlotMeta, ax: Axes, x_limits, width=0.4):
        # 获取 K 线单位列表的 MACD 数据
        macd_lst = [klu.macd for klu in meta.klu_iter()]
        # 断言：MACD 数据必须存在 (即 CChanConfig 中 macd_metric 不能设置为 False)
        assert macd_lst[0] is not None, "you can't draw macd until you delete macd_metric=False"

        # 获取 X 轴范围的起始索引
        x_begin = x_limits[0]
        # 需要绘制的 X 轴索引范围
        x_idx = range(len(macd_lst))[x_begin:]
        # 获取需要绘制的 DIF 线数据
        dif_line = [macd.DIF for macd in macd_lst[x_begin:]]
        # 获取需要绘制的 DEA 线数据
        dea_line = [macd.DEA for macd in macd_lst[x_begin:]]
        # 获取需要绘制的 MACD 柱状图数据
        macd_bar = [macd.macd for macd in macd_lst[x_begin:]]
        # 计算 MACD 图的 Y 轴范围
        y_min = min([min(dif_line), min(dea_line), min(macd_bar)])
        y_max = max([max(dif_line), max(dea_line), max(macd_bar)])
        # 绘制 DIF 线
        ax.plot(x_idx, dif_line, "#FFA500") # 橙色
        # 绘制 DEA 线
        ax.plot(x_idx, dea_line, "#0000ff") # 蓝色
        # 绘制 MACD 柱状图，默认为红色
        _bar = ax.bar(x_idx, macd_bar, color="r", width=width)
        # 根据 MACD 值正负设置柱状图颜色 (大于0红色，小于0深绿色)
        for idx, macd in enumerate(macd_bar):
            if macd < 0:
                _bar[idx].set_color("#006400") # 深绿色
        # 设置 MACD 图的 Y 轴范围
        ax.set_ylim(y_min, y_max)

    # 绘制均线
    def draw_mean(self, meta: CChanPlotMeta, ax: Axes):
        # 获取 K 线单位列表的均线数据
        mean_lst = [klu.trend[TREND_TYPE.MEAN] for klu in meta.klu_iter()]
        # 获取所有均线周期 T
        Ts = list(mean_lst[0].keys())
        # 获取颜色映射
        cmap = plt.cm.get_cmap('hsv', max([10, len(Ts)]))  # type: ignore
        # 遍历每个均线周期
        for cmap_idx, T in enumerate(Ts):
            # 获取该周期的均线数值数组
            mean_arr = [mean_dict[T] for mean_dict in mean_lst]
            # 绘制均线，使用颜色映射，并添加标签
            ax.plot(range(len(mean_arr)), mean_arr, c=cmap(cmap_idx), label=f'{T} meanline')
        # 添加图例
        ax.legend()

    # 绘制趋势通道
    def draw_channel(self, meta: CChanPlotMeta, ax: Axes, T=None, top_color="r", bottom_color="b", linewidth=3, linestyle="solid"):
        # 获取 K 线单位列表的最大值通道和最小值通道数据
        max_lst = [klu.trend[TREND_TYPE.MAX] for klu in meta.klu_iter()]
        min_lst = [klu.trend[TREND_TYPE.MIN] for klu in meta.klu_iter()]
        # 获取所有配置的通道周期 T
        config_T_lst = sorted(list(max_lst[0].keys()))
        # 如果没有指定周期 T，使用最后一个配置的周期
        if T is None:
            T = config_T_lst[-1]
        # 如果指定的周期 T 未配置，抛出异常
        elif T not in max_lst[0]:
            raise CChanException(f"plot channel of T={T} is not setted in CChanConfig.trend_metrics = {config_T_lst}", ErrCode.PLOT_ERR)
        # 获取该周期的顶部通道数值数组
        top_array = [_d[T] for _d in max_lst]
        # 获取该周期的底部通道数值数组
        bottom_array = [_d[T] for _d in min_lst]
        # 绘制顶部通道线
        ax.plot(range(len(top_array)), top_array, c=top_color, linewidth=linewidth, linestyle=linestyle, label=f'{T}-TOP-channel')
        # 绘制底部通道线
        ax.plot(range(len(bottom_array)), bottom_array, c=bottom_color, linewidth=linewidth, linestyle=linestyle, label=f'{T}-BUTTOM-channel')
        # 添加图例
        ax.legend()

    # 绘制布林带 (BOLL)
    def draw_boll(self, meta: CChanPlotMeta, ax: Axes, mid_color="black", up_color="blue", down_color="purple"):
        # 获取当前 X 轴起始索引
        x_begin = int(ax.get_xlim()[0])
        try:
            # 获取 K 线单位列表的布林带数据
            ma = [klu.boll.MID for klu in meta.klu_iter()][x_begin:] # 中轨
            up = [klu.boll.UP for klu in meta.klu_iter()][x_begin:] # 上轨
            down = [klu.boll.DOWN for klu in meta.klu_iter()][x_begin:] # 下轨
        except AttributeError as e:
            # 如果没有配置布林带参数 (boll_n)，抛出异常
            raise CChanException("you can't draw boll until you set boll_n in CChanConfig", ErrCode.PLOT_ERR) from e

        # 绘制布林带中轨线
        ax.plot(range(x_begin, x_begin+len(ma)), ma, c=mid_color)
        # 绘制布林带上轨线
        ax.plot(range(x_begin, x_begin+len(up)), up, c=up_color)
        # 绘制布林带下轨线
        ax.plot(range(x_begin, x_begin+len(down)), down, c=down_color)
        # 更新 Y 轴范围以包含布林带上下轨
        self.y_min = min([self.y_min, min(down)])
        self.y_max = max([self.y_max, max(up)])

    # 绘制买卖点的通用方法
    def bsp_common_draw(self, bsp_list, ax: Axes, buy_color, sell_color, fontsize, arrow_l, arrow_h, arrow_w):
        # 获取当前 X 轴起始位置
        x_begin = ax.get_xlim()[0]
        # 计算 Y 轴范围
        y_range = self.y_max-self.y_min
        # 遍历买卖点列表
        for bsp in bsp_list:
            # 如果买卖点所在的 X 轴位置小于起始位置，跳过
            if bsp.x < x_begin:
                continue
            # 根据买卖点方向选择颜色
            color = buy_color if bsp.is_buy else sell_color
            # 根据买卖点方向调整垂直对齐方式
            verticalalignment = 'top' if bsp.is_buy else 'bottom'

            # 计算箭头方向和长度
            arrow_dir = 1 if bsp.is_buy else -1 # 买点箭头向上 (+1)，卖点箭头向下 (-1)
            arrow_len = arrow_l*y_range # 箭头总长度 (占 Y 轴范围的比例)
            arrow_head = arrow_len*arrow_h # 箭头头部长度 (占箭头总长度的比例)
            # 绘制买卖点文本 (描述)
            ax.text(bsp.x, # X 坐标
                    bsp.y-arrow_len*arrow_dir, # Y 坐标 (偏移一个箭头长度)
                    f'{bsp.desc()}', # 文本内容
                    fontsize=fontsize, # 字体大小
                    color=color, # 颜色
                    verticalalignment=verticalalignment, # 垂直对齐
                    horizontalalignment='center') # 水平居中对齐
            # 绘制买卖点箭头
            ax.arrow(bsp.x, # 起始 X 坐标
                     bsp.y-arrow_len*arrow_dir, # 起始 Y 坐标 (文本下方)
                     0, # X 方向位移为0
                     (arrow_len-arrow_head)*arrow_dir, # Y 方向位移 (箭头实体部分长度)
                     head_width=arrow_w, # 箭头头部宽度
                     head_length=arrow_head, # 箭头头部长度
                     color=color) # 颜色
            # 更新 Y 轴范围以包含文本和箭头
            if bsp.y-arrow_len*arrow_dir < self.y_min:
                self.y_min = bsp.y-arrow_len*arrow_dir
            if bsp.y-arrow_len*arrow_dir > self.y_max:
                self.y_max = bsp.y-arrow_len*arrow_dir

    # 绘制笔的买卖点
    def draw_bs_point(self, meta: CChanPlotMeta, ax: Axes, buy_color='r', sell_color='g', fontsize=15, arrow_l=0.15, arrow_h=0.2, arrow_w=1):
        # 调用通用买卖点绘制方法绘制笔的买卖点
        self.bsp_common_draw(
            bsp_list=meta.bs_point_lst, # 笔的买卖点列表
            ax=ax,
            buy_color=buy_color,
            sell_color=sell_color,
            fontsize=fontsize,
            arrow_l=arrow_l,
            arrow_h=arrow_h,
            arrow_w=arrow_w,
        )

    # 绘制线段的买卖点
    def draw_seg_bs_point(self, meta: CChanPlotMeta, ax: Axes, buy_color='r', sell_color='g', fontsize=18, arrow_l=0.2, arrow_h=0.25, arrow_w=1.2):
        # 调用通用买卖点绘制方法绘制线段的买卖点
        self.bsp_common_draw(
            bsp_list=meta.seg_bsp_lst, # 线段的买卖点列表
            ax=ax,
            buy_color=buy_color,
            sell_color=sell_color,
            fontsize=fontsize,
            arrow_l=arrow_l,
            arrow_h=arrow_h,
            arrow_w=arrow_w,
        )

    # 更新 Y 轴范围以包含文本框
    def update_y_range(self, text_box, text_y):
        # 计算文本框高度
        text_height = text_box.y1 - text_box.y0
        # 更新 Y 轴最小值
        self.y_min = min([self.y_min, text_y-text_height])
        # 更新 Y 轴最大值
        self.y_max = max([self.y_max, text_y+text_height])

    # 绘制买卖点平仓动作的辅助函数
    def plot_closeAction(self, plot_cover, cbsp, ax: Axes, text_y, arrow_len, arrow_dir, color):
        # 如果不绘制平仓动作，返回
        if not plot_cover:
            return
        # 遍历买卖点的平仓动作
        for closeAction in cbsp.close_action:
            # 绘制从买卖点到平仓点的箭头
            ax.arrow(
                cbsp.x, # 起始 X 坐标 (买卖点 X)
                text_y, # 起始 Y 坐标 (文本 Y)
                closeAction.x-cbsp.x, # X 方向位移
                arrow_len*arrow_dir + (closeAction.y-cbsp.y), # Y 方向位移 (偏移一个箭头长度，并加上平仓点与买卖点 Y 坐标差)
                color=color, # 颜色
            )

    # 绘制标记 (自定义文本和箭头标记)
    def draw_marker(
        self,
        meta: CChanPlotMeta,
        ax: Axes,
        markers: Dict[CTime | str, Tuple[str, Literal['up', 'down'], str] | Tuple[str, Literal['up', 'down']]], # 标记字典
        arrow_l=0.15, # 箭头总长度比例
        arrow_h_r=0.2, # 箭头头部长度比例
        arrow_w=1, # 箭头头部宽度
        fontsize=14, # 字体大小
        default_color='b', # 默认颜色
    ):
        # 标记字典格式示例：{'2022/03/01': ('xxx', 'up', 'red'), '2022/03/02': ('yyy', 'down')}
        # 获取当前 X 轴范围
        x_begin, x_end = ax.get_xlim()
        # 创建日期字符串到 K 线索引的映射字典
        datetick_dict = {date: idx for idx, date in enumerate(meta.datetick)}

        # 处理包含子级别时间的标记，将其转换为顶层级别的时间
        new_marker = {}
        for klu in meta.klu_iter():
            for date, marker in markers.items():
                date_str = date.to_str() if isinstance(date, CTime) else date
                # 如果 K 线单位包含该日期且该日期不是 K 线单位自身的日期
                if klu.include_sub_lv_time(date_str) and klu.time.to_str() != date_str:
                    # 将标记添加到 new_marker 中，键为 K 线单位日期字符串
                    new_marker[klu.time.to_str()] = marker
        # 将原始标记合并到 new_marker 中 (覆盖相同日期)
        new_marker.update(markers)

        # 创建 K 线索引到 K 线单位的映射字典
        kl_dict = dict(enumerate(meta.klu_iter()))
        # 计算 Y 轴范围和箭头长度
        y_range = self.y_max-self.y_min
        arror_len = arrow_l*y_range
        arrow_h = arror_len*arrow_h_r
        # 遍历处理后的标记字典
        for date, marker in new_marker.items():
            # 如果日期是 CTime 类型，转换为字符串
            if isinstance(date, CTime):
                date = date.to_str()
            # 如果日期不在日期刻度字典中，跳过
            if date not in datetick_dict:
                continue
            # 获取标记所在的 K 线索引
            x = datetick_dict[date]
            # 如果标记所在的 K 线索引不在 X 轴范围内，跳过
            if x < x_begin or x > x_end:
                continue
            # 解析标记信息
            if len(marker) == 2:
                # 如果只有文本和位置，颜色使用默认颜色
                color = default_color
                marker_content, position = marker
            else:
                # 如果有文本、位置和颜色
                assert len(marker) == 3
                marker_content, position, color = marker
            # 断言位置必须是 'up' 或 'down'
            assert position in ['up', 'down']
            # 计算箭头方向和基准价格
            _dir = -1 if position == 'up' else 1 # 'up' 箭头向上，基准最高价，_dir = -1； 'down' 箭头向下，基准最低价，_dir = 1
            bench = kl_dict[x].high if position == 'up' else kl_dict[x].low # 基准价格 (up 用最高价，down 用最低价)
            # 绘制箭头
            ax.arrow(
                x, # 起始 X 坐标
                bench-arror_len*_dir, # 起始 Y 坐标 (从基准价格偏移一个箭头长度)
                0, # X 方向位移为0
                (arror_len-arrow_h)*_dir,  # Y 方向位移 (箭头实体长度，减去头部长度避免重叠)
                head_width=arrow_w, # 箭头头部宽度
                head_length=arrow_h, # 箭头头部长度
                color=color # 颜色
            )
            # 绘制标记文本
            ax.text(
                x, # X 坐标
                bench-arror_len*_dir, # Y 坐标 (文本位置与箭头起始位置一致)
                marker_content, # 文本内容
                fontsize=fontsize, # 字体大小
                color=color, # 颜色
                verticalalignment='top' if position == 'down' else 'bottom', # 垂直对齐方式 (down 文本在箭头上方，up 文本在箭头下方)
                horizontalalignment='center' # 水平居中对齐
            )

    # 绘制 Demark TDST 线 (起始线)
    def draw_demark_begin_line(self, ax, begin_line_color, plot_begin_set: set, linestyle: str, demark_idx: T_DEMARK_INDEX):
        # 如果指定了起始线颜色，且 Demark 指标有 TDST 峰值，且该 Demark 系列未被绘制过起始线
        if begin_line_color is not None and demark_idx['series'].TDST_peak is not None and id(demark_idx['series']) not in plot_begin_set:
            # 如果存在 Countdown，结束索引为 Countdown 的最后一个 K 线索引
            if demark_idx['series'].countdown is not None:
                end_idx = demark_idx['series'].countdown.kl_list[-1].idx
            else:
                # 否则，结束索引为 Setup 的最后一个 K 线索引
                end_idx = demark_idx['series'].kl_list[-1].idx
            # 绘制 TDST 峰值线 (水平线)
            ax.plot(
                [demark_idx['series'].kl_list[CDemarkEngine.SETUP_BIAS].idx, end_idx], # X 坐标 (从 Setup 起始 K 线偏移量开始到结束索引)
                [demark_idx['series'].TDST_peak, demark_idx['series'].TDST_peak], # Y 坐标 (TDST 峰值价格)
                c=begin_line_color, # 颜色
                linestyle=linestyle # 线型
            )
            # 将该 Demark 系列的 ID 添加到已绘制起始线的集合中
            plot_begin_set.add(id(demark_idx['series']))

    # 绘制 RSI 指标 (注意：此方法不完整)
    def draw_rsi(
        self,
        meta: CChanPlotMeta,
        ax,
        color='b', # RSI 颜色
    ):
        # 获取 K 线单位列表的 RSI 数据
        data = [klu.rsi for klu in meta.klu_iter()]
        # 获取 X 轴范围的起始和结束索引
        x_begin, x_end = int(ax.get_xlim()[0]), int(ax.get_xlim()[1])
        # 绘制 RSI 线 (注意：此处代码被截断，未完成绘制逻辑)
        ax.plot(range(x_begin, x_end), data[x_begin: x_end], c=color)
    # 绘制 KDJ 指标 (注意：此方法不完整)
    def draw_kdj(
        self,
        meta: CChanPlotMeta,
        ax,
        # 此处代码被截断，未完成 KDJ 绘制逻辑
    ):
        # Note: This method is incomplete based on the provided code snippet.
        pass # Placeholder for the rest of the method

# -------------------- 辅助函数 (类外部) --------------------

# 绘制笔的线条
def plot_bi_element(bi: CBi_meta, ax: Axes, color='black'):
    ax.plot([bi.begin_x, bi.end_x], [bi.begin_y, bi.end_y], color)

# 绘制笔或线段的结束价格文本
def bi_text(bi_idx: int, ax: Axes, bi: Union[CBi_meta, CZS_meta], fontsize=10, color='black'):
    # 垂直对齐方式：如果笔/线段是向上的，文本在结束点上方 (bottom)；否则在下方 (top)
    verticalalignment = "bottom" if bi.dir == BI_DIR.UP else "top"
    ax.text(
        bi.end_x, # X 坐标 (结束点的 X 坐标)
        bi.end_y, # Y 坐标 (结束点的 Y 坐标)
        f'{bi.end_y:.2f}', # 文本内容 (结束价格，保留两位小数)
        fontsize=fontsize, # 字体大小
        color=color, # 颜色
        verticalalignment=verticalalignment, # 垂直对齐
        horizontalalignment='center') # 水平居中对齐

# 绘制中枢文本信息
def add_zs_text(ax: Axes, zs: CZS_meta, fontsize=14, color='orange'):
    # 在中枢顶部绘制最高价
    ax.text(zs.begin + zs.w / 2, zs.high, f'{zs.high:.2f}', fontsize=fontsize, color=color, horizontalalignment='center', verticalalignment='bottom')
    # 在中枢底部绘制最低价
    ax.text(zs.begin + zs.w / 2, zs.low, f'{zs.low:.2f}', fontsize=fontsize, color=color, horizontalalignment='center', verticalalignment='top')
    # 在中枢中心位置绘制中枢类型和索引
    ax.text(
        zs.begin + zs.w / 2,
        zs.low + zs.h / 2,
        f'ZS{zs.idx}({zs.zs_type.name})', # 文本内容：ZS + 索引 + 类型名称
        fontsize=fontsize,
        color=color,
        horizontalalignment='center',
        verticalalignment='center'
    )

# 显示函数的参数和默认值 (用于生成文档)
def show_func_helper(func):
    # 获取函数的签名
    sig = inspect.signature(func)
    # 获取函数名
    func_name = func.__name__
    print(f"def {func_name}{sig}:")
    # 打印函数的文档字符串 (如果存在)
    if func.__doc__:
        print(f'    """{func.__doc__}"""')
    # 打印 pass (占位符)
    print("    pass")
    print() # 打印空行分隔不同函数
