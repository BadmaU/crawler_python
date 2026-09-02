import abc
import csv
import io
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import aiofiles
import aiosqlite

logger = logging.getLogger(__name__)

STANDARD_FIELDS = (
    "url",
    "title",
    "text",
    "links",
    "metadata",
    "crawled_at",
    "status_code",
    "content_type",
)


class DataStorage(abc.ABC):
    @abc.abstractmethod
    async def save(self, data: dict) -> None:
        """Сохранение данных."""

    @abc.abstractmethod
    async def close(self) -> None:
        """Закрытие соединения/ресурсов."""


class JSONStorage(DataStorage):
    def __init__(self, filepath: str, *, indent: int | None = 2) -> None:
        self._filepath = filepath
        self._indent = indent
        self._buffer: list[dict] = []
        self._buffer_size = 50
        self._lock: Any = None

    def _ensure_lock(self) -> Any:
        import asyncio
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _serialize(self, data: dict) -> dict:
        serialized = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, set):
                serialized[key] = sorted(value)
            else:
                serialized[key] = value
        return serialized

    async def save(self, data: dict) -> None:
        lock = self._ensure_lock()
        async with lock:
            self._buffer.append(self._serialize(data))
            if len(self._buffer) >= self._buffer_size:
                await self._flush()

    async def _flush(self) -> None:
        if not self._buffer:
            return
        existing: list[dict] = []
        if os.path.exists(self._filepath):
            try:
                async with aiofiles.open(self._filepath, "r", encoding="utf-8") as f:
                    content = await f.read()
                    if content.strip():
                        existing = json.loads(content)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Не удалось прочитать существующий JSON: %s", e)

        pending = existing + self._buffer
        try:
            async with aiofiles.open(self._filepath, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(pending, ensure_ascii=False, indent=self._indent, default=str)
                )
            self._buffer.clear()
        except OSError as e:
            logger.error("Не удалось сохранить JSON: %s", e)

    async def close(self) -> None:
        lock = self._ensure_lock()
        async with lock:
            await self._flush()

    async def read_all(self) -> list[dict]:
        if not os.path.exists(self._filepath):
            return []
        async with aiofiles.open(self._filepath, "r", encoding="utf-8") as f:
            content = await f.read()
            if not content.strip():
                return []
            return json.loads(content)

    def get_stats(self) -> dict:
        return {
            "filepath": self._filepath,
            "buffered": len(self._buffer),
            "buffer_size": self._buffer_size,
        }


class CSVStorage(DataStorage):
    def __init__(
        self,
        filepath: str,
        *,
        encoding: str = "utf-8",
        delimiter: str = ",",
        quotechar: str = '"',
    ) -> None:
        self._filepath = filepath
        self._encoding = encoding
        self._delimiter = delimiter
        self._quotechar = quotechar
        self._headers_written = False
        self._fieldnames: list[str] = list(STANDARD_FIELDS)
        self._lock: Any = None

    def _ensure_lock(self) -> Any:
        import asyncio
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _flatten_value(self, value: Any) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False, default=str)
        if value is None:
            return ""
        return str(value)

    def _prepare_row(self, data: dict) -> dict[str, str]:
        row: dict[str, str] = {}
        all_keys = list(dict.fromkeys(list(data.keys()) + self._fieldnames))
        self._fieldnames = all_keys
        for key in all_keys:
            value = data.get(key, "")
            row[key] = self._flatten_value(value)
        return row

    async def _ensure_headers(self) -> None:
        if not os.path.exists(self._filepath) or os.path.getsize(self._filepath) == 0:
            self._headers_written = True
            async with aiofiles.open(self._filepath, "w", encoding=self._encoding, newline="") as f:
                output = io.StringIO(newline="")
                writer = csv.DictWriter(
                    output,
                    fieldnames=self._fieldnames,
                    delimiter=self._delimiter,
                    quotechar=self._quotechar,
                )
                writer.writeheader()
                await f.write(output.getvalue())

    async def save(self, data: dict) -> None:
        lock = self._ensure_lock()
        async with lock:
            row = self._prepare_row(data)
            if not self._headers_written:
                await self._ensure_headers()
            output = io.StringIO(newline="")
            writer = csv.DictWriter(
                output,
                fieldnames=self._fieldnames,
                delimiter=self._delimiter,
                quotechar=self._quotechar,
            )
            writer.writerow(row)
            async with aiofiles.open(self._filepath, "a", encoding=self._encoding, newline="") as f:
                await f.write(output.getvalue())

    async def close(self) -> None:
        pass

    async def read_all(self) -> list[dict]:
        if not os.path.exists(self._filepath):
            return []
        rows: list[dict] = []
        async with aiofiles.open(self._filepath, "r", encoding=self._encoding, newline="") as f:
            content = await f.read()
            reader = csv.DictReader(
                io.StringIO(content),
                delimiter=self._delimiter,
                quotechar=self._quotechar,
            )
            for row in reader:
                rows.append(dict(row))
        return rows

    def get_stats(self) -> dict:
        return {
            "filepath": self._filepath,
            "fieldnames": self._fieldnames,
            "encoding": self._encoding,
        }


class SQLiteStorage(DataStorage):
    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None
        self._buffer: list[tuple] = []
        self._buffer_size = 100

    async def init_db(self) -> None:
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA synchronous=NORMAL")
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                text TEXT,
                links TEXT,
                metadata TEXT,
                crawled_at TEXT,
                status_code INTEGER,
                content_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_pages_url ON pages(url)
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_pages_crawled_at ON pages(crawled_at)
        """)
        await self._db.commit()

    async def _ensure_db(self) -> aiosqlite.Connection:
        if self._db is None:
            await self.init_db()
        assert self._db is not None
        return self._db

    def _serialize_row(self, data: dict) -> tuple:
        links = data.get("links", [])
        if isinstance(links, list):
            links = json.dumps(links, ensure_ascii=False)
        metadata = data.get("metadata", {})
        if isinstance(metadata, dict):
            metadata = json.dumps(metadata, ensure_ascii=False)
        crawled_at = data.get("crawled_at", "")
        if isinstance(crawled_at, datetime):
            crawled_at = crawled_at.isoformat()
        return (
            data.get("url", ""),
            data.get("title", ""),
            data.get("text", ""),
            links,
            metadata,
            str(crawled_at),
            data.get("status_code", 0),
            data.get("content_type", ""),
        )

    async def save(self, data: dict) -> None:
        db = await self._ensure_db()
        row = self._serialize_row(data)
        self._buffer.append(row)
        if len(self._buffer) >= self._buffer_size:
            await self._flush()

    async def _flush(self) -> None:
        if not self._buffer:
            return
        db = await self._ensure_db()
        try:
            await db.executemany(
                """
                INSERT OR REPLACE INTO pages
                (url, title, text, links, metadata, crawled_at, status_code, content_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._buffer,
            )
            await db.commit()
            self._buffer.clear()
        except Exception as e:
            logger.error("Ошибка batch-вставки: %s", e)
            raise

    async def close(self) -> None:
        await self._flush()
        if self._db:
            await self._db.close()
            self._db = None

    async def read_all(self) -> list[dict]:
        db = await self._ensure_db()
        cursor = await db.execute("SELECT * FROM pages")
        rows = await cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        results: list[dict] = []
        for row in rows:
            record = dict(zip(columns, row))
            try:
                record["links"] = json.loads(record.get("links", "[]"))
            except (json.JSONDecodeError, TypeError):
                record["links"] = []
            try:
                record["metadata"] = json.loads(record.get("metadata", "{}"))
            except (json.JSONDecodeError, TypeError):
                record["metadata"] = {}
            results.append(record)
        return results

    async def get_count(self) -> int:
        db = await self._ensure_db()
        cursor = await db.execute("SELECT COUNT(*) FROM pages")
        row = await cursor.fetchone()
        return row[0] if row else 0

    def get_stats(self) -> dict:
        return {
            "db_path": self._db_path,
            "buffered": len(self._buffer),
            "buffer_size": self._buffer_size,
        }
