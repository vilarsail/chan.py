from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime, time

from Common.file_util import FileOperator
file_operator = FileOperator()
file_operator.load_init_files_to_redis()

from ScheduleTask.FullStockHighLevelBspCheck import full_etf_high_level_bsp_check_main, \
    full_stock_high_level_bsp_check_main
from ScheduleTask.LimitStockHighLevelBspCheck import limit_stock_high_level_bsp_check_main
from ScheduleTask.LimitStockLowLevelBspCheck import limit_stock_low_level_bsp_check_main



# 创建调度器
scheduler = BlockingScheduler()

# 添加每分钟触发的任务（仅在 09:30-15:30 执行）
scheduler.add_job(
    limit_stock_low_level_bsp_check_main,
    'cron',
    hour='9-15',
    minute='*/1',
    max_instances=1,
    timezone='Asia/Shanghai'
)

scheduler.add_job(
    limit_stock_high_level_bsp_check_main,
    'cron',
    hour=18,
    minute=0,
    timezone='Asia/Shanghai'
)

scheduler.add_job(
    full_etf_high_level_bsp_check_main,
    'cron',
    hour=18,
    minute=0,
    timezone='Asia/Shanghai'
)

scheduler.add_job(
    full_stock_high_level_bsp_check_main,
    'cron',
    hour=21,
    minute=0,
    timezone='Asia/Shanghai'
)

print("定时任务已启动，按 Ctrl+C 退出")
try:
    scheduler.start()
except KeyboardInterrupt:
    print("\n定时任务已停止")