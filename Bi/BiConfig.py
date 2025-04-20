from Common.CEnum import FX_CHECK_METHOD
from Common.ChanException import CChanException, ErrCode


class CBiConfig:
    def __init__(
        self,
        bi_algo="normal",  # 构造笔所使用的算法，可选 normal（默认）或 fx（使用分型）
        is_strict=True,     # 是否启用严格模式（默认启用）
        bi_fx_check="half",  # 分型确认方式（half, strict, loss, totally）
        gap_as_kl=True,     # 是否将K线之间的跳空看作一根K线处理
        bi_end_is_peak=True,  # 判断一笔结束时是否要求尾部是极值点
        bi_allow_sub_peak=True,  # 是否允许替代尾部极值点（次高/次低）来更新笔尾
    ):
        self.bi_algo = bi_algo  # 笔构造算法
        self.is_strict = is_strict  # 是否启用严格笔段构造逻辑

        # 将字符串形式的分型判断方法转换为内部枚举类型
        if bi_fx_check == "strict":
            self.bi_fx_check = FX_CHECK_METHOD.STRICT
        elif bi_fx_check == "loss":
            self.bi_fx_check = FX_CHECK_METHOD.LOSS
        elif bi_fx_check == "half":
            self.bi_fx_check = FX_CHECK_METHOD.HALF
        elif bi_fx_check == 'totally':
            self.bi_fx_check = FX_CHECK_METHOD.TOTALLY
        else:
            raise CChanException(f"unknown bi_fx_check={bi_fx_check}", ErrCode.PARA_ERROR)

        self.gap_as_kl = gap_as_kl  # 是否将跳空当作K线（影响跨度计算）
        self.bi_end_is_peak = bi_end_is_peak  # 是否强制笔尾必须为极值点（TOP/BOTTOM）
        self.bi_allow_sub_peak = bi_allow_sub_peak  # 是否允许笔尾用次级极值点替代
