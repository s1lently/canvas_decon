"""
Nervous System Protocol - Backend Progress Reporting
标准化的进度回调协议，让后端能与 GUI 通信
"""
import time


class TaskProgress:
    """
    任务进度回调包装器

    Usage (Backend):
        def fetch_data(progress_callback=None):
            if progress_callback:
                progress_callback.update(progress=0, status="Starting...")
            # ... do work ...
            if progress_callback:
                progress_callback.update(progress=50, status="Processing...", speed="10 items/s")
            # ... finish ...
            if progress_callback:
                progress_callback.update(progress=100, status="Done")

    Usage (GUI):
        callback = mission_control.get_callback(task_id)
        tp = TaskProgress(callback)
        fetch_data(progress_callback=tp)
    """

    def __init__(self, callback=None):
        """
        Args:
            callback: 接收 dict 的函数，由 MissionControl 提供
        """
        self.callback = callback
        self.start_time = time.time()
        self.last_update = 0

    def update(self, progress=None, status=None, speed=None, detail=None, error=None):
        """
        发送进度更新

        Args:
            progress (int): 0-100 进度百分比
            status (str): 简短状态 (e.g. "Processing 5/20")
            speed (str): 速度指示 (e.g. "1.5 items/s")
            detail (str): 详细日志 (可选，会显示在控制台)
            error (str): 错误信息 (如果有)
        """
        # CLI 模式：无 callback 时打印到 shell
        if not self.callback:
            if error:
                print(f"[ERROR] {error}")
            elif detail:
                print(detail)
            elif status:
                pct = f"{progress}%" if progress is not None else ""
                spd = f" | {speed}" if speed else ""
                print(f"\r{status} {pct}{spd}", end='', flush=True)
            return

        # GUI 模式：节流更新 (最高 20fps，除非是 100% 或 error)
        now = time.time()
        if now - self.last_update < 0.05 and progress != 100 and not error:
            return
        self.last_update = now

        # 构建数据包
        data = {'timestamp': now}
        if progress is not None:
            data['progress'] = progress
        if status is not None:
            data['status'] = status
        if speed is not None:
            data['speed'] = speed
        if detail is not None:
            data['detail'] = detail
        if error is not None:
            data['error'] = error

        # 发送
        try:
            self.callback(data)
        except Exception as e:
            print(f"[WARN] Callback failed: {e}")

    def elapsed(self):
        """返回已用时间(秒)"""
        return time.time() - self.start_time

    def finish(self, status="Completed"):
        """完成任务"""
        self.update(progress=100, status=status)
        # 打印换行 (CLI 模式)
        if not self.callback:
            print()

    def fail(self, error):
        """任务失败"""
        self.update(error=error)
