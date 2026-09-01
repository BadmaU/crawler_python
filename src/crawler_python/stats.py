import html
import json
import os
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

logger = None  # noqa: F841  (not needed here)


class CrawlerStats:
    """Расширенная статистика краулера: счётчики, скорость, распределения."""

    def __init__(self) -> None:
        self._start_time: float | None = None
        self._end_time: float | None = None
        self.total_pages = 0
        self.successful = 0
        self.failed = 0
        self.status_codes: Counter[int] = Counter()
        self.domains: Counter[str] = Counter()
        self._lock = threading.Lock()
        self._page_marks: list[float] = []

    def start(self) -> None:
        with self._lock:
            self._start_time = time.perf_counter()

    def stop(self) -> None:
        with self._lock:
            self._end_time = time.perf_counter()

    def record_request(
        self, url: str, status: int | None = None, success: bool | None = None
    ) -> None:
        with self._lock:
            now = time.perf_counter()
            self._page_marks.append(now)
            self.total_pages += 1
            domain = urlparse(url).netloc
            if domain:
                self.domains[domain] += 1
            if status is not None:
                self.status_codes[status] += 1
            if success is True:
                self.successful += 1
            elif success is False:
                self.failed += 1
            elif status is not None:
                if status < 400:
                    self.successful += 1
                else:
                    self.failed += 1

    def record_success(self, url: str, status: int | None = None) -> None:
        self.record_request(url, status=status, success=True)

    def record_failure(self, url: str, status: int | None = None) -> None:
        self.record_request(url, status=status, success=False)

    def record_page(self, url: str) -> None:
        self.record_request(url, success=True)

    @property
    def runtime_seconds(self) -> float:
        now = self._end_time or time.perf_counter()
        start = self._start_time or now
        return max(0.0, now - start)

    @property
    def avg_speed(self) -> float:
        rt = self.runtime_seconds
        return self.total_pages / rt if rt > 0 else 0.0

    def recent_speed(self, window: float = 10.0) -> float:
        with self._lock:
            now = time.perf_counter()
            cutoff = now - window
            recent = [m for m in self._page_marks if m >= cutoff and m <= now]
            return len(recent) / window

    def top_domains(self, limit: int = 10) -> list[dict]:
        return [
            {"domain": d, "pages": c}
            for d, c in self.domains.most_common(limit)
        ]

    def status_distribution(self) -> dict[str, int]:
        return {str(k): v for k, v in sorted(self.status_codes.items())}

    def snapshot(self) -> dict[str, Any]:
        return {
            "total_pages": self.total_pages,
            "successful": self.successful,
            "failed": self.failed,
            "runtime_seconds": round(self.runtime_seconds, 3),
            "avg_speed": round(self.avg_speed, 3),
            "recent_speed": round(self.recent_speed(), 3),
            "status_codes": self.status_distribution(),
            "top_domains": self.top_domains(),
            "started_at": (
                datetime.fromtimestamp(self._start_time, timezone.utc).isoformat()
                if self._start_time
                else None
            ),
            "finished_at": (
                datetime.fromtimestamp(self._end_time, timezone.utc).isoformat()
                if self._end_time
                else None
            ),
        }

    def export_to_json(self, filename: str) -> None:
        data = self.snapshot()
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def export_to_html_report(self, filename: str) -> None:
        data = self.snapshot()
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        report = self._render_html(data)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)

    def _render_html(self, data: dict[str, Any]) -> str:
        status_rows = "".join(
            f"<tr><td>{html.escape(code)}</td><td>{count}</td></tr>"
            for code, count in data["status_codes"].items()
        ) or "<tr><td colspan='2'>Нет данных</td></tr>"

        domain_rows = "".join(
            f"<tr><td>{html.escape(d['domain'])}</td><td>{d['pages']}</td></tr>"
            for d in data["top_domains"]
        ) or "<tr><td colspan='2'>Нет данных</td></tr>"

        status_code_pairs = list(data["status_codes"].items())
        max_status = max(
            (c for _, c in status_code_pairs), default=1
        )
        status_bars = "".join(
            f"""
            <div class="bar-row">
              <span class="bar-label">{html.escape(code)}</span>
              <div class="bar-track">
                <div class="bar-fill status" style="width:{100 * count / max_status:.1f}%"></div>
              </div>
              <span class="bar-count">{count}</span>
            </div>
            """
            for code, count in status_code_pairs
        ) or "<p>Нет данных</p>"

        domain_codes = [html.escape(d["domain"]) for d in data["top_domains"]]
        domain_counts = [d["pages"] for d in data["top_domains"]]
        max_domain = max(domain_counts, default=1)
        domain_bars = "".join(
            f"""
            <div class="bar-row">
              <span class="bar-label">{code}</span>
              <div class="bar-track">
                <div class="bar-fill domain" style="width:{100 * count / max_domain:.1f}%"></div>
              </div>
              <span class="bar-count">{count}</span>
            </div>
            """
            for code, count in zip(domain_codes, domain_counts)
        ) or "<p>Нет данных</p>"

        return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Отчёт краулера</title>
<style>
  body {{ font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; margin: 2rem; color: #222; }}
  h1 {{ color: #1a1a2e; }}
  .cards {{ display: flex; gap: 1rem; flex-wrap: wrap; margin: 1.5rem 0; }}
  .card {{
    background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px;
    padding: 1rem 1.5rem; min-width: 140px;
  }}
  .card .value {{ font-size: 2rem; font-weight: 700; color: #0d6efd; }}
  .card .label {{ color: #6c757d; font-size: .85rem; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ border: 1px solid #dee2e6; padding: .5rem .75rem; text-align: left; }}
  th {{ background: #e9ecef; }}
  .bar-row {{ display: flex; align-items: center; gap: .75rem; margin: .4rem 0; }}
  .bar-label {{ width: 180px; font-family: monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .bar-track {{ flex: 1; background: #e9ecef; border-radius: 4px; height: 16px; }}
  .bar-fill {{ height: 16px; border-radius: 4px; }}
  .bar-fill.status {{ background: #0d6efd; }}
  .bar-fill.domain {{ background: #20c997; }}
  .bar-count {{ width: 50px; text-align: right; font-family: monospace; }}
  .meta {{ color: #6c757d; font-size: .85rem; }}
</style>
</head>
<body>
<h1>Отчёт краулера</h1>
<p class="meta">
  Начало: {html.escape(data['started_at'] or '-')} |
  Конец: {html.escape(data['finished_at'] or '-')} |
  Время работы: {data['runtime_seconds']} c
</p>
<div class="cards">
  <div class="card"><div class="value">{data['total_pages']}</div><div class="label">Всего страниц</div></div>
  <div class="card" style="border-color:#198754"><div class="value" style="color:#198754">{data['successful']}</div><div class="label">Успешно</div></div>
  <div class="card" style="border-color:#dc3545"><div class="value" style="color:#dc3545">{data['failed']}</div><div class="label">Ошибки</div></div>
  <div class="card"><div class="value">{data['avg_speed']:.1f}</div><div class="label">Ср. скорость, стр/с</div></div>
  <div class="card"><div class="value">{data['recent_speed']:.1f}</div><div class="label">Тек. скорость, стр/с</div></div>
</div>

<h2>Распределение по статус-кодам</h2>
<div>{status_bars}</div>
<table>
<thead><tr><th>Статус</th><th>Количество</th></tr></thead>
<tbody>{status_rows}</tbody>
</table>

<h2>Топ доменов</h2>
<div>{domain_bars}</div>
<table>
<thead><tr><th>Домен</th><th>Страниц</th></tr></thead>
<tbody>{domain_rows}</tbody>
</table>

<p class="meta">Сгенерировано: {datetime.now(timezone.utc).isoformat()}</p>
</body>
</html>
"""
