import asyncio
import logging
import shutil
import time

logger = logging.getLogger(__name__)


class ProgressMonitor:
    """Мониторинг краулера в реальном времени.

    Выводит прогресс-бар, текущую скорость, оценку оставшегося времени
    и количество активных задач.
    """

    _BAR_SYMBOLS = "▏▎▍▌▋▊▉█"  # noqa: RUF001

    def __init__(
        self,
        interval: float = 0.5,
        enabled: bool = True,
        total: int | None = None,
    ) -> None:
        self._interval = interval
        self._enabled = enabled
        self._total = total
        self._progress_callback = None
        self._mark_callback = None
        self._task: asyncio.Task | None = None
        self._start = time.perf_counter()
        self._last_render = 0.0
        self._last_count = 0
        self._last_time = 0.0

    def set_total(self, total: int | None) -> None:
        self._total = total

    def set_callbacks(self, progress=None, marks=None) -> None:
        """progress: () -> int (текущее кол-во обработанных), marks: () -> int активные."""
        self._progress_callback = progress
        self._mark_callback = marks

    async def start(self) -> None:
        if not self._enabled:
            return
        self._start = time.perf_counter()
        self._last_time = self._start
        self._last_count = 0
        self._last_render = 0.0
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._enabled:
            self._render(final=True)
            print()

    async def _run(self) -> None:
        try:
            while True:
                self._render()
                await asyncio.sleep(self._interval)
        except asyncio.CancelledError:
            pass

    def _render(self, final: bool = False) -> None:
        now = time.perf_counter()
        if not final and (now - self._last_render) < 0.2:
            return
        self._last_render = now

        count = self._progress_callback() if self._progress_callback else 0
        active = self._mark_callback() if self._mark_callback else 0

        elapsed = now - self._start
        speed = (count - self._last_count) / (now - self._last_time) if now > self._last_time else 0.0
        self._last_count = count
        self._last_time = now

        if self._total and self._total > 0:
            percent = min(100.0, 100.0 * count / self._total)
            remaining = (self._total - count) / speed if speed > 0 else float("inf")
        else:
            percent = 0.0
            remaining = float("inf")

        # Пересчёт общей скорости для ETA более стабилен
        avg_speed = count / elapsed if elapsed > 0 else 0.0
        if self._total and self._total > 0:
            remaining_avg = (self._total - count) / avg_speed if avg_speed > 0 else float("inf")
        else:
            remaining_avg = float("inf")

        line = self._format_line(count, percent, speed, remaining_avg, active, elapsed)
        if self._enabled:
            self._write_line(line, final=final)

    def _format_line(
        self, count: int, percent: float, speed: float,
        remaining: float, active: int, elapsed: float,
    ) -> str:
        bar_len = 20
        filled = int(bar_len * percent / 100.0)
        bar = "█" * filled + "░" * (bar_len - filled)
        eta = self._fmt_eta(remaining)
        return (
            f"[{bar}] {percent:5.1f}% | {count:>6} стр | "
            f"{speed:5.1f} стр/с | ETA {eta} | активные: {active:>3} | "
            f"время: {elapsed:6.1f} с"
        )

    @staticmethod
    def _fmt_eta(seconds: float) -> str:
        if seconds == float("inf") or seconds < 0:
            return "—"
        seconds = int(seconds)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}ч {m:02d}м"
        if m > 0:
            return f"{m}м {s:02d}с"
        return f"{s}с"

    def _write_line(self, line: str, final: bool = False) -> None:
        try:
            columns = shutil.get_terminal_size((80, 20)).columns
            if len(line) >= columns:
                line = line[: columns - 1]
        except Exception:
            pass
        if final:
            print("\r" + line)
        else:
            print("\r" + line, end="", flush=True)
