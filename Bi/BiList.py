from typing import List, Optional, Union, overload

from Common.CEnum import FX_TYPE, KLINE_DIR
from KLine.KLine import CKLine

from .Bi import CBi
from .BiConfig import CBiConfig


class CBiList:
    def __init__(self, bi_conf=CBiConfig()):
        # 初始化CBiList对象，bi_conf是构造笔的配置参数
        self.bi_list: List[CBi] = []  # 存储所有构造好的笔对象
        self.last_end = None  # 当前已构造笔中最后一笔的尾部K线
        self.config = bi_conf  # 生成笔的配置

        self.free_klc_lst = []  # 初始时用于临时缓存K线（主要用于第一笔未形成前）

    def __str__(self):
        return "\n".join([str(bi) for bi in self.bi_list])

    def __iter__(self):
        yield from self.bi_list

    @overload
    def __getitem__(self, index: int) -> CBi: ...

    @overload
    def __getitem__(self, index: slice) -> List[CBi]: ...

    def __getitem__(self, index: Union[slice, int]) -> Union[List[CBi], CBi]:
        # 支持通过索引获取某一笔或多笔
        return self.bi_list[index]

    def __len__(self):
        # 返回已构造的笔数量
        return len(self.bi_list)

    def try_create_first_bi(self, klc: CKLine) -> bool:
        # 尝试使用当前K线和之前缓存的K线，创建第一笔
        for exist_free_klc in self.free_klc_lst:
            if exist_free_klc.fx == klc.fx:
                continue  # 两个K线的分型类型一样则跳过
            if self.can_make_bi(klc, exist_free_klc):
                # 如果满足条件可以组成笔，则创建新笔
                self.add_new_bi(exist_free_klc, klc)
                self.last_end = klc
                return True
        # 若无法组成第一笔，则缓存当前K线供后续组合
        self.free_klc_lst.append(klc)
        self.last_end = klc
        return False

    def update_bi(self, klc: CKLine, last_klc: CKLine, cal_virtual: bool) -> bool:
        # 用新的K线更新笔，支持更新实际笔和虚拟笔
        # klc 是倒数第二根K线（用于构造确定笔）
        # last_klc 是最新K线（用于更新虚拟笔）
        flag1 = self.update_bi_sure(klc)
        if cal_virtual:
            flag2 = self.try_add_virtual_bi(last_klc)
            return flag1 or flag2
        else:
            return flag1

    def can_update_peak(self, klc: CKLine):
        # 判断当前K线是否可以作为上一笔的替代极值点来更新其终点
        if self.config.bi_allow_sub_peak or len(self.bi_list) < 2:
            return False
        if self.bi_list[-1].is_down() and klc.high < self.bi_list[-1].get_begin_val():
            return False
        if self.bi_list[-1].is_up() and klc.low > self.bi_list[-1].get_begin_val():
            return False
        if not end_is_peak(self.bi_list[-2].begin_klc, klc):
            return False
        if self[-1].is_down() and self[-1].get_end_val() < self[-2].get_begin_val():
            return False
        if self[-1].is_up() and self[-1].get_end_val() > self[-2].get_begin_val():
            return False
        return True

    def update_peak(self, klc: CKLine, for_virtual=False):
        # 如果当前K线可用于替代上一个笔的结束K线（极值），则更新该笔
        if not self.can_update_peak(klc):
            return False
        _tmp_last_bi = self.bi_list[-1]  # 暂存当前最后一笔
        self.bi_list.pop()  # 删除这笔
        if not self.try_update_end(klc, for_virtual=for_virtual):
            self.bi_list.append(_tmp_last_bi)  # 如果更新失败则恢复
            return False
        else:
            if for_virtual:
                self.bi_list[-1].append_sure_end(_tmp_last_bi.end_klc)
            return True

    def update_bi_sure(self, klc: CKLine) -> bool:
        # 使用当前K线更新构造中的“确定笔”部分
        _tmp_end = self.get_last_klu_of_last_bi()
        self.delete_virtual_bi()  # 先移除当前笔中的虚拟部分

        # 如果K线没有分型，不能构成笔
        if klc.fx == FX_TYPE.UNKNOWN:
            return _tmp_end != self.get_last_klu_of_last_bi()

        # 构造第一笔
        if self.last_end is None or len(self.bi_list) == 0:
            return self.try_create_first_bi(klc)

        # 如果当前分型与上一分型相同，尝试更新最后一笔尾部
        if klc.fx == self.last_end.fx:
            return self.try_update_end(klc)

        # 可以构成新笔
        elif self.can_make_bi(klc, self.last_end):
            self.add_new_bi(self.last_end, klc)
            self.last_end = klc
            return True

        # 否则尝试更新极值点
        elif self.update_peak(klc):
            return True

        # 无法构成新笔，也不能更新尾部，可能改变了结束位置
        return _tmp_end != self.get_last_klu_of_last_bi()

    def delete_virtual_bi(self):
        # 删除虚拟笔，或将其恢复为确定笔
        if len(self) > 0 and not self.bi_list[-1].is_sure:
            sure_end_list = [klc for klc in self.bi_list[-1].sure_end]
            if len(sure_end_list):
                self.bi_list[-1].restore_from_virtual_end(sure_end_list[0])
                self.last_end = self[-1].end_klc
                for sure_end in sure_end_list[1:]:
                    self.add_new_bi(self.last_end, sure_end, is_sure=True)
                    self.last_end = self[-1].end_klc
            else:
                del self.bi_list[-1]  # 没有真实确认的结束K线，则删除该虚笔
        self.last_end = self[-1].end_klc if len(self) > 0 else None
        if len(self) > 0:
            self[-1].next = None

    def try_add_virtual_bi(self, klc: CKLine, need_del_end=False):
        # 尝试加入一笔“虚拟笔”
        if need_del_end:
            self.delete_virtual_bi()
        if len(self) == 0:
            return False
        if klc.idx == self[-1].end_klc.idx:
            return False

        # 如果方向一致且更高/更低，则更新尾部
        if (self[-1].is_up() and klc.high >= self[-1].end_klc.high) or \
           (self[-1].is_down() and klc.low <= self[-1].end_klc.low):
            self.bi_list[-1].update_virtual_end(klc)
            return True

        # 否则从尾部往前尝试找是否可以构成新笔
        _tmp_klc = klc
        while _tmp_klc and _tmp_klc.idx > self[-1].end_klc.idx:
            if self.can_make_bi(_tmp_klc, self[-1].end_klc, for_virtual=True):
                self.add_new_bi(self.last_end, _tmp_klc, is_sure=False)
                return True
            elif self.update_peak(_tmp_klc, for_virtual=True):
                return True
            _tmp_klc = _tmp_klc.pre
        return False

    def add_new_bi(self, pre_klc, cur_klc, is_sure=True):
        # 添加一笔新笔，同时连接前后笔
        self.bi_list.append(CBi(pre_klc, cur_klc, idx=len(self.bi_list), is_sure=is_sure))
        if len(self.bi_list) >= 2:
            self.bi_list[-2].next = self.bi_list[-1]
            self.bi_list[-1].pre = self.bi_list[-2]

    def satisfy_bi_span(self, klc: CKLine, last_end: CKLine):
        # 判断两个K线之间是否满足最小笔跨度
        bi_span = self.get_klc_span(klc, last_end)
        if self.config.is_strict:
            return bi_span >= 4
        uint_kl_cnt = 0
        tmp_klc = last_end.next
        while tmp_klc:
            uint_kl_cnt += len(tmp_klc.lst)
            if not tmp_klc.next:
                return False
            if tmp_klc.next.idx < klc.idx:
                tmp_klc = tmp_klc.next
            else:
                break
        return bi_span >= 3 and uint_kl_cnt >= 3

    def get_klc_span(self, klc: CKLine, last_end: CKLine) -> int:
        # 获取K线跨度，考虑跳空缺口
        span = klc.idx - last_end.idx
        if not self.config.gap_as_kl:
            return span
        if span >= 4:
            return span
        tmp_klc = last_end
        while tmp_klc and tmp_klc.idx < klc.idx:
            if tmp_klc.has_gap_with_next():
                span += 1
            tmp_klc = tmp_klc.next
        return span

    def can_make_bi(self, klc: CKLine, last_end: CKLine, for_virtual: bool = False):
        # 判断当前K线是否能和前一个尾部构成新的一笔
        satisify_span = True if self.config.bi_algo == 'fx' else self.satisfy_bi_span(klc, last_end)
        if not satisify_span:
            return False
        if not last_end.check_fx_valid(klc, self.config.bi_fx_check, for_virtual):
            return False
        if self.config.bi_end_is_peak and not end_is_peak(last_end, klc):
            return False
        return True

    def try_update_end(self, klc: CKLine, for_virtual=False) -> bool:
        # 更新最后一笔的结束K线
        def check_top(klc: CKLine, for_virtual):
            return klc.dir == KLINE_DIR.UP if for_virtual else klc.fx == FX_TYPE.TOP

        def check_bottom(klc: CKLine, for_virtual):
            return klc.dir == KLINE_DIR.DOWN if for_virtual else klc.fx == FX_TYPE.BOTTOM

        if len(self.bi_list) == 0:
            return False
        last_bi = self.bi_list[-1]
        if (last_bi.is_up() and check_top(klc, for_virtual) and klc.high >= last_bi.get_end_val()) or \
           (last_bi.is_down() and check_bottom(klc, for_virtual) and klc.low <= last_bi.get_end_val()):
            if for_virtual:
                last_bi.update_virtual_end(klc)
            else:
                last_bi.update_new_end(klc)
            self.last_end = klc
            return True
        else:
            return False

    def get_last_klu_of_last_bi(self) -> Optional[int]:
        # 获取最后一笔的尾部K线单元索引
        return self.bi_list[-1].get_end_klu().idx if len(self) > 0 else None


def end_is_peak(last_end: CKLine, cur_end: CKLine) -> bool:
    # 判断当前K线是否为极值点
    if last_end.fx == FX_TYPE.BOTTOM:
        cmp_thred = cur_end.high
        klc = last_end.get_next()
        while True:
            if klc.idx >= cur_end.idx:
                return True
            if klc.high > cmp_thred:
                return False
            klc = klc.get_next()
    elif last_end.fx == FX_TYPE.TOP:
        cmp_thred = cur_end.low
        klc = last_end.get_next()
        while True:
            if klc.idx >= cur_end.idx:
                return True
            if klc.low < cmp_thred:
                return False
            klc = klc.get_next()
    return True
