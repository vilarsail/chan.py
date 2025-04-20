import copy
import datetime
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Union

# 导入买卖点类
from BuySellPoint.BS_Point import CBS_Point
# 导入缠论配置类
from ChanConfig import CChanConfig
# 导入缠论枚举类型：复权类型、数据源、K线类型
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
# 导入缠论异常类和错误码
from Common.ChanException import CChanException, ErrCode
# 导入时间处理类
from Common.CTime import CTime
# 导入辅助函数：检查K线类型顺序、判断K线类型是否小于等于日线
from Common.func_util import check_kltype_order, kltype_lte_day
# 导入通用股票数据API类
from DataAPI.CommonStockAPI import CCommonStockApi
# 导入K线列表类
from KLine.KLine_List import CKLine_List
# 导入K线单位类
from KLine.KLine_Unit import CKLine_Unit


# 定义缠论主类
class CChan:
    # 类的初始化方法
    def __init__(
        self,
        code, # 股票代码
        begin_time=None, # 起始时间
        end_time=None, # 结束时间
        data_src: Union[DATA_SRC, str] = DATA_SRC.BAO_STOCK, # 数据源
        lv_list=None, # 需要分析的K线级别列表，从高到低排列
        config=None, # 缠论配置对象
        autype: AUTYPE = AUTYPE.QFQ, # 复权类型
    ):
        # 如果没有指定级别列表，默认使用日线和60分钟线
        if lv_list is None:
            lv_list = [KL_TYPE.K_DAY, KL_TYPE.K_60M]
        # 检查K线级别列表的顺序是否从高到低
        check_kltype_order(lv_list)
        # 初始化类属性
        self.code = code
        # 将 datetime.date 类型的 begin_time/end_time 转换为字符串
        self.begin_time = str(begin_time) if isinstance(begin_time, datetime.date) else begin_time
        self.end_time = str(end_time) if isinstance(end_time, datetime.date) else end_time
        self.autype = autype
        self.data_src = data_src
        self.lv_list: List[KL_TYPE] = lv_list

        # 如果没有指定配置，使用默认配置
        if config is None:
            config = CChanConfig()
        self.conf = config # 缠论配置

        # 用于记录K线时间未对齐的数量
        self.kl_misalign_cnt = 0
        # 用于记录K线数据不一致的详细信息 (key 为父级别时间，value 为子级别时间列表)
        self.kl_inconsistent_detail = defaultdict(list)

        # 用于存储各级别K线数据的迭代器列表
        self.g_kl_iter = defaultdict(list)

        # 执行初始化操作
        self.do_init()

        # 如果配置没有设置 trigger_step (非回放模式)
        if not config.trigger_step:
            # 调用 load 方法一次性加载所有数据并计算所有结构
            for _ in self.load():
                ... # 遍历迭代器，执行计算过程

    # 实现对象的深拷贝
    def __deepcopy__(self, memo):
        # 获取当前类的类型
        cls = self.__class__
        # 创建一个新对象，但不调用 __init__
        obj: CChan = cls.__new__(cls)
        # 将当前对象和新对象添加到备忘录中，防止循环引用
        memo[id(self)] = obj
        # 拷贝不可变属性
        obj.code = self.code
        obj.begin_time = self.begin_time
        obj.end_time = self.end_time
        obj.autype = self.autype
        obj.data_src = self.data_src
        # 深拷贝列表和配置对象
        obj.lv_list = copy.deepcopy(self.lv_list, memo)
        obj.conf = copy.deepcopy(self.conf, memo)
        obj.kl_misalign_cnt = self.kl_misalign_cnt
        obj.kl_inconsistent_detail = copy.deepcopy(self.kl_inconsistent_detail, memo)
        obj.g_kl_iter = copy.deepcopy(self.g_kl_iter, memo)
        # 如果存在 klu_cache 和 klu_last_t，进行深拷贝
        if hasattr(self, 'klu_cache'):
            obj.klu_cache = copy.deepcopy(self.klu_cache, memo)
        if hasattr(self, 'klu_last_t'):
            obj.klu_last_t = copy.deepcopy(self.klu_last_t, memo)
        # 深拷贝 kl_datas 中的 CKLine_List 对象
        obj.kl_datas = {}
        for kl_type, ckline in self.kl_datas.items():
            obj.kl_datas[kl_type] = copy.deepcopy(ckline, memo)
        # 修正深拷贝后 KLine_Unit 之间的父子关系引用
        for kl_type, ckline in self.kl_datas.items():
            for klc in ckline:
                for klu in klc.lst:
                    # 确保 KLine_Unit 已经在备忘录中 (已被拷贝)
                    assert id(klu) in memo
                    # 修正 sup_kl (父K线单位) 引用
                    if klu.sup_kl:
                        memo[id(klu)].sup_kl = memo[id(klu.sup_kl)]
                    # 修正 sub_kl_list (子K线单位列表) 引用
                    memo[id(klu)].sub_kl_list = [memo[id(sub_kl)] for sub_kl in klu.sub_kl_list]
        # 返回深拷贝后的对象
        return obj

    # 初始化各级别 K 线列表
    def do_init(self):
        # 创建一个字典来存储各级别的 K 线列表
        self.kl_datas: Dict[KL_TYPE, CKLine_List] = {}
        # 为每个指定级别创建一个 CKLine_List 对象，并关联配置
        for idx in range(len(self.lv_list)):
            self.kl_datas[self.lv_list[idx]] = CKLine_List(self.lv_list[idx], conf=self.conf)

    # 从股票数据API加载数据并生成 K 线单位迭代器
    def load_stock_data(self, stockapi_instance: CCommonStockApi, lv) -> Iterable[CKLine_Unit]:
        # 遍历数据API获取的 K 线数据
        for KLU_IDX, klu in enumerate(stockapi_instance.get_kl_data()):
            # 设置 K 线单位的索引
            klu.set_idx(KLU_IDX)
            # 设置 K 线单位的级别
            klu.kl_type = lv
            # 返回 K 线单位迭代器
            yield klu

    # 获取加载股票数据的迭代器
    def get_load_stock_iter(self, stockapi_cls, lv):
        # 创建股票数据API实例
        stockapi_instance = stockapi_cls(code=self.code, k_type=lv, begin_date=self.begin_time, end_date=self.end_time, autype=self.autype)
        # 调用 load_stock_data 方法获取 K 线单位迭代器
        return self.load_stock_data(stockapi_instance, lv)

    # 为指定级别添加 K 线数据迭代器
    def add_lv_iter(self, lv_idx, iter):
        # 如果 lv_idx 是整数，通过级别列表获取对应的 K 线类型
        if isinstance(lv_idx, int):
            self.g_kl_iter[self.lv_list[lv_idx]].append(iter)
        else:
            # 如果 lv_idx 是 K 线类型，直接使用
            self.g_kl_iter[lv_idx].append(iter)

    # 获取指定级别的下一个 K 线单位
    def get_next_lv_klu(self, lv_idx):
        # 如果 lv_idx 是整数，通过级别列表获取对应的 K 线类型
        if isinstance(lv_idx, int):
            lv_idx = self.lv_list[lv_idx]
        # 如果该级别没有可用的迭代器，抛出 StopIteration
        if len(self.g_kl_iter[lv_idx]) == 0:
            raise StopIteration
        try:
            # 从当前迭代器中获取下一个 K 线单位
            return self.g_kl_iter[lv_idx][0].__next__()
        except StopIteration:
            # 如果当前迭代器耗尽，移除该迭代器
            self.g_kl_iter[lv_idx] = self.g_kl_iter[lv_idx][1:]
            # 如果还有其他迭代器，继续获取下一个 K 线单位
            if len(self.g_kl_iter[lv_idx]) != 0:
                return self.get_next_lv_klu(lv_idx)
            else:
                # 如果所有迭代器都耗尽，抛出 StopIteration
                raise

    # 回放模式下的逐步加载和计算
    def step_load(self):
        # 断言：必须在回放模式下调用此方法 (conf.trigger_step 为 True)
        assert self.conf.trigger_step
        self.do_init()  # 清空数据，防止再次重跑没有数据
        yielded = False  # 标记是否曾经返回过结果
        # 遍历 load 方法生成的快照迭代器，每次计算 trigger_step 个 K 线单位
        for idx, snapshot in enumerate(self.load(self.conf.trigger_step)):
            # 跳过指定的起始步数
            if idx < self.conf.skip_step:
                continue
            # 返回当前计算状态的快照
            yield snapshot
            yielded = True
        # 如果没有返回过结果 (例如数据不足)，则返回当前对象 (空对象或只有少量数据)
        if not yielded:
            yield self

    # 触发式加载和计算 (例如实时数据推送)
    def trigger_load(self, inp):
        # 输入格式示例：{type: [klu, ...]}，key 是 K 线类型，value 是该类型 K 线单位列表
        # 初始化 klu_cache 和 klu_last_t (如果不存在)
        if not hasattr(self, 'klu_cache'):
            self.klu_cache: List[Optional[CKLine_Unit]] = [None for _ in self.lv_list]
        if not hasattr(self, 'klu_last_t'):
            self.klu_last_t = [CTime(1980, 1, 1, 0, 0) for _ in self.lv_list]
        # 为每个传入的级别数据添加 K 线单位迭代器
        for lv_idx, lv in enumerate(self.lv_list):
            if lv not in inp:
                # 如果最高级别没有传入数据，抛出异常
                if lv_idx == 0:
                    raise CChanException(f"最高级别{lv}没有传入数据", ErrCode.NO_DATA)
                continue # 跳过没有数据的级别
            for klu in inp[lv]:
                klu.kl_type = lv # 设置 K 线单位的级别
            # 断言：传入的数据必须是列表类型
            assert isinstance(inp[lv], list)
            self.add_lv_iter(lv, iter(inp[lv])) # 添加迭代器
        # 调用 load_iterator 从最高级别开始计算，非回放模式
        for _ in self.load_iterator(lv_idx=0, parent_klu=None, step=False):
            ... # 遍历迭代器，执行计算过程
        # 如果不是回放模式，在所有数据计算完之后一次性计算所有级别中枢和线段
        if not self.conf.trigger_step:
            for lv in self.lv_list:
                self.kl_datas[lv].cal_seg_and_zs()

    # 初始化各级别 K 线单位迭代器
    def init_lv_klu_iter(self, stockapi_cls):
        # 用于存储各级别 K 线单位迭代器
        lv_klu_iter = []
        # 用于存储有效 (成功获取数据) 的级别列表
        valid_lv_list = []
        # 遍历所有指定级别
        for lv in self.lv_list:
            try:
                # 获取该级别的股票数据迭代器
                lv_klu_iter.append(self.get_load_stock_iter(stockapi_cls, lv))
                # 将有效级别添加到列表中
                valid_lv_list.append(lv)
            except CChanException as e:
                # 如果数据源找不到数据，且配置允许自动跳过非法子级别
                if e.errcode == ErrCode.SRC_DATA_NOT_FOUND and self.conf.auto_skip_illegal_sub_lv:
                    # 打印警告信息
                    if self.conf.print_warning:
                        print(f"[WARNING-{self.code}]{lv}级别获取数据失败，跳过")
                    # 从 kl_datas 中删除该级别的数据
                    del self.kl_datas[lv]
                    continue # 跳过当前级别
                # 其他异常则直接抛出
                raise e
        # 更新类中的级别列表为有效级别列表
        self.lv_list = valid_lv_list
        # 返回各级别 K 线单位迭代器列表
        return lv_klu_iter

    # 获取股票数据API类
    def GetStockAPI(self):
        _dict = {} # 数据源到API类的映射字典
        # 根据数据源类型导入并添加到字典
        if self.data_src == DATA_SRC.BAO_STOCK:
            from DataAPI.BaoStockAPI import CBaoStock
            _dict[DATA_SRC.BAO_STOCK] = CBaoStock
        elif self.data_src == DATA_SRC.CCXT:
            from DataAPI.ccxt import CCXT
            _dict[DATA_SRC.CCXT] = CCXT
        elif self.data_src == DATA_SRC.CSV:
            from DataAPI.csvAPI import CSV_API
            _dict[DATA_SRC.CSV] = CSV_API
        # 如果数据源在字典中，返回对应的API类
        if self.data_src in _dict:
            return _dict[self.data_src]
        # 如果数据源是字符串，检查是否是自定义数据源
        assert isinstance(self.data_src, str)
        if self.data_src.find("custom:") < 0:
            # 如果不是自定义数据源且不在已知列表中，抛出错误
            raise CChanException("load src type error", ErrCode.SRC_DATA_TYPE_ERR)
        # 解析自定义数据源信息 (包名和类名)
        package_info = self.data_src.split(":")[1]
        package_name, cls_name = package_info.split(".")
        # 动态导入自定义数据源类
        exec(f"from DataAPI.{package_name} import {cls_name}")
        # 返回自定义数据源类
        return eval(cls_name)

    # 加载并计算缠论结构的核心方法
    def load(self, step=False):
        # 获取股票数据API类
        stockapi_cls = self.GetStockAPI()
        try:
            # 初始化数据API
            stockapi_cls.do_init()
            # 初始化各级别 K 线单位迭代器并添加到 g_kl_iter
            for lv_idx, klu_iter in enumerate(self.init_lv_klu_iter(stockapi_cls)):
                self.add_lv_iter(lv_idx, klu_iter)
            # 初始化 K 线单位缓存和上次时间
            self.klu_cache: List[Optional[CKLine_Unit]] = [None for _ in self.lv_list]
            self.klu_last_t = [CTime(1980, 1, 1, 0, 0) for _ in self.lv_list]

            # 调用 load_iterator 从最高级别开始计算，返回迭代器
            yield from self.load_iterator(lv_idx=0, parent_klu=None, step=step)  # 计算入口
            # 如果不是回放模式，在所有数据计算完之后一次性计算所有级别中枢和线段
            if not step:
                for lv in self.lv_list:
                    self.kl_datas[lv].cal_seg_and_zs()
        except Exception:
            # 发生异常时关闭数据API并重新抛出异常
            stockapi_cls.do_close()
            raise
        finally:
            # 无论是否发生异常，最终都会关闭数据API
            stockapi_cls.do_close()
        # 如果最高级别没有获得任何数据，抛出异常
        if len(self[0]) == 0:
            raise CChanException("最高级别没有获得任何数据", ErrCode.NO_DATA)

    # 设置 K 线单位的父子关系
    def set_klu_parent_relation(self, parent_klu, kline_unit, cur_lv, lv_idx):
        # 如果开启 K 线数据检查，且当前级别和父级别都小于等于日线级别
        if self.conf.kl_data_check and kltype_lte_day(cur_lv) and kltype_lte_day(self.lv_list[lv_idx-1]):
            # 检查父子级别 K 线时间是否一致
            self.check_kl_consitent(parent_klu, kline_unit)
        # 将当前 K 线单位添加到父 K 线单位的子节点列表
        parent_klu.add_children(kline_unit)
        # 设置当前 K 线单位的父节点
        kline_unit.set_parent(parent_klu)

    # 向当前级别的 K 线列表添加新的 K 线单位
    def add_new_kl(self, cur_lv: KL_TYPE, kline_unit):
        try:
            # 调用 CKLine_List 的 add_single_klu 方法添加 K 线单位
            self.kl_datas[cur_lv].add_single_klu(kline_unit)
        except Exception:
            # 如果添加过程中发生错误，打印错误时间和信息，并重新抛出异常
            if self.conf.print_err_time:
                print(f"[ERROR-{self.code}]在计算{kline_unit.time}K线时发生错误!")
            raise

    # 尝试设置 K 线单位的索引
    def try_set_klu_idx(self, lv_idx: int, kline_unit: CKLine_Unit):
        # 如果 K 线单位索引已经设置，直接返回
        if kline_unit.idx >= 0:
            return
        # 如果当前级别还没有 K 线单位，设置索引为 0
        if len(self[lv_idx]) == 0:
            kline_unit.set_idx(0)
        else:
            # 否则，设置索引为当前级别最后一个 K 线单位的索引 + 1
            self.kl_datas[self.lv_list[lv_idx]][-1][-1].idx # This line seems redundant, access last klu
            kline_unit.set_idx(self[lv_idx][-1][-1].idx + 1) # Corrected line

    # 加载和计算 K 线单位的迭代器方法 (递归调用处理多级别)
    def load_iterator(self, lv_idx, parent_klu, step):
        # K线时间天级别以下描述的是结束时间，如60M线，每天第一根是10点30的
        # 天以上是当天日期
        # 获取当前处理的 K 线级别
        cur_lv = self.lv_list[lv_idx]
        # 获取当前级别上一个 K 线单位 (如果存在)
        pre_klu = self[lv_idx][-1][-1] if len(self[lv_idx]) > 0 and len(self[lv_idx][-1]) > 0 else None

        # 循环处理当前级别的 K 线单位
        while True:
            # 如果 K 线单位缓存中存在当前级别的 K 线单位，使用缓存中的
            if self.klu_cache[lv_idx]:
                kline_unit = self.klu_cache[lv_idx]
                assert kline_unit is not None
                self.klu_cache[lv_idx] = None # 清空缓存
            else:
                try:
                    # 从当前级别的数据迭代器中获取下一个 K 线单位
                    kline_unit = self.get_next_lv_klu(lv_idx)
                    # 尝试设置 K 线单位的索引
                    self.try_set_klu_idx(lv_idx, kline_unit)
                    # 检查 K 线单位时间是否单调递增
                    if not kline_unit.time > self.klu_last_t[lv_idx]:
                        raise CChanException(f"kline time err, cur={kline_unit.time}, last={self.klu_last_t[lv_idx]}, or refer to quick_guide.md, try set auto=False in the CTime returned by your data source class", ErrCode.KL_NOT_MONOTONOUS)
                    # 更新当前级别的上次时间
                    self.klu_last_t[lv_idx] = kline_unit.time
                except StopIteration:
                    # 如果当前级别的 K 线单位耗尽，跳出循环
                    break

            # 如果存在父 K 线单位，且当前 K 线单位时间晚于父 K 线单位时间
            if parent_klu and kline_unit.time > parent_klu.time:
                # 将当前 K 线单位放入缓存，并在父 K 线单位处理完成后再处理
                self.klu_cache[lv_idx] = kline_unit
                break # 跳出循环，等待父 K 线单位处理完成

            # 设置当前 K 线单位的上一个 K 线单位
            kline_unit.set_pre_klu(pre_klu)
            # 更新 pre_klu 为当前 K 线单位
            pre_klu = kline_unit
            # 将新的 K 线单位添加到当前级别的 K 线列表
            self.add_new_kl(cur_lv, kline_unit)
            # 如果存在父 K 线单位，设置父子关系
            if parent_klu:
                self.set_klu_parent_relation(parent_klu, kline_unit, cur_lv, lv_idx)
            # 如果当前级别不是最低级别
            if lv_idx != len(self.lv_list)-1:
                # 递归调用 load_iterator 处理下一个级别，父 K 线单位为当前 K 线单位
                for _ in self.load_iterator(lv_idx+1, kline_unit, step):
                    ... # 遍历迭代器，执行计算过程
                # 检查父子级别 K 线单位数量是否对齐
                self.check_kl_align(kline_unit, lv_idx)
            # 如果是最高级别且在回放模式下
            if lv_idx == 0 and step:
                # 计算当前 K 线单位所在 K 线列表的中枢和线段 (回放模式下每步计算)
                self.kl_datas[cur_lv].cal_seg_and_zs()
                # 返回当前对象的快照
                yield self

    # 检查父子级别 K 线时间一致性
    def check_kl_consitent(self, parent_klu, sub_klu):
        # 如果父级别 K 线单位和子级别 K 线单位的年、月、日不一致
        if parent_klu.time.year != sub_klu.time.year or \
           parent_klu.time.month != sub_klu.time.month or \
           parent_klu.time.day != sub_klu.time.day:
            # 记录不一致的详细信息
            self.kl_inconsistent_detail[str(parent_klu.time)].append(sub_klu.time)
            # 如果配置开启警告打印，打印警告信息
            if self.conf.print_warning:
                print(f"[WARNING-{self.code}]父级别时间是{parent_klu.time}，次级别时间却是{sub_klu.time}")
            # 如果不一致条数超过最大限制，抛出异常
            if len(self.kl_inconsistent_detail) >= self.conf.max_kl_inconsistent_cnt:
                raise CChanException(f"父&子级别K线时间不一致条数超过{self.conf.max_kl_inconsistent_cnt}！！", ErrCode.KL_TIME_INCONSISTENT)

    # 检查父子级别 K 线数量对齐
    def check_kl_align(self, kline_unit, lv_idx):
        # 如果开启 K 线数据检查，且当前 K 线单位没有子 K 线单位
        if self.conf.kl_data_check and len(kline_unit.sub_kl_list) == 0:
            # K 线未对齐计数加一
            self.kl_misalign_cnt += 1
            # 如果配置开启警告打印，打印警告信息
            if self.conf.print_warning:
                print(f"[WARNING-{self.code}]当前{kline_unit.time}没在次级别{self.lv_list[lv_idx+1]}找到K线！！")
            # 如果未对齐条数超过最大限制，抛出异常
            if self.kl_misalign_cnt >= self.conf.max_kl_misalgin_cnt:
                raise CChanException(f"在次级别找不到K线条数超过{self.conf.max_kl_misalgin_cnt}！！", ErrCode.KL_DATA_NOT_ALIGN)

    # 实现按索引或级别类型访问 K 线列表
    def __getitem__(self, n) -> CKLine_List:
        # 如果 n 是 K 线类型，直接返回对应的 K 线列表
        if isinstance(n, KL_TYPE):
            return self.kl_datas[n]
        # 如果 n 是整数，通过级别列表获取对应的 K 线类型，然后返回 K 线列表
        elif isinstance(n, int):
            return self.kl_datas[self.lv_list[n]]
        # 其他类型抛出异常
        else:
            raise CChanException("unspoourt query type", ErrCode.COMMON_ERROR)

    # 获取指定级别 (或最高级别) 的买卖点列表，按时间顺序排序
    def get_bsp(self, idx=None) -> List[CBS_Point]:
        # 如果指定了级别索引 idx
        if idx is not None:
            # 返回该级别 K 线列表的排序买卖点列表
            return self[idx].bs_point_lst.getSortedBspList()
        # 如果没有指定级别索引，断言只分析了一个级别
        assert len(self.lv_list) == 1
        # 返回最高级别 (索引为 0) K 线列表的排序买卖点列表
        return self[0].bs_point_lst.getSortedBspList()