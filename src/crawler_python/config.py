import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


@dataclass
class CrawlerConfig:
    """Конфигурация краулера, загружаемая из YAML/JSON файла."""

    start_urls: list[str] = field(default_factory=list)
    max_pages: int = 100
    max_depth: int = 3
    same_domain_only: bool = True
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)

    max_concurrent: int = 10
    per_domain: int = 3
    timeout: int = 10
    requests_per_second: float = 5.0
    min_delay: float = 0.0
    jitter: float = 0.0
    respect_robots: bool = True
    user_agent: str = "AsyncCrawler/2.0"
    max_retries: int = 3
    backoff_factor: float = 2.0
    circuit_breaker: bool = True

    use_sitemap: bool = False
    sitemap_urls: list[str] = field(default_factory=list)

    storage: str = "json"
    storage_path: str = "results.json"
    output_report: str = "report.html"
    output_stats: str = "stats.json"

    logging_level: str = "INFO"
    log_file: str = "crawler.log"
    log_rotation: int = 5
    log_max_bytes: int = 5_000_000

    proxies: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: str) -> "CrawlerConfig":
        path = os.path.abspath(path)
        suffix = Path(path).suffix.lower()
        with open(path, "r", encoding="utf-8") as f:
            if suffix in (".json",):
                raw = json.load(f)
            elif suffix in (".yaml", ".yml"):
                if yaml is None:
                    raise RuntimeError(
                        "PyYAML не установлен. Выполните: pip install pyyaml"
                    )
                raw = yaml.safe_load(f)
            else:
                raise ValueError(
                    f"Неподдерживаемый формат конфигурации: {suffix}"
                )
        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise ValueError("Конфигурация должна быть объектом/таблицей")
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CrawlerConfig":
        known = {f for f in cls.__dataclass_fields__}
        kwargs: dict[str, Any] = {}
        for key, value in data.items():
            if key in known:
                kwargs[key] = value
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        return {
            key: getattr(self, key)
            for key in self.__dataclass_fields__
        }

    @property
    def storage_kwargs(self) -> dict[str, Any]:
        if self.storage == "json":
            return {"filepath": self.storage_path}
        return {"filepath": self.storage_path}
