import json
import os
import tempfile
from datetime import datetime, timezone

import pytest

from crawler_python.storage import CSVStorage, JSONStorage, SQLiteStorage


@pytest.fixture
def sample_data() -> dict:
    return {
        "url": "https://example.com/page1",
        "title": "Test Page",
        "text": "This is test content for the page",
        "links": ["https://example.com/link1", "https://example.com/link2"],
        "metadata": {"description": "Test description", "keywords": "test"},
        "crawled_at": datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        "status_code": 200,
        "content_type": "text/html",
    }


@pytest.fixture
def sample_data_2() -> dict:
    return {
        "url": "https://example.com/page2",
        "title": "Second Page",
        "text": "Another page content",
        "links": ["https://example.com/link3"],
        "metadata": {},
        "crawled_at": datetime(2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc),
        "status_code": 200,
        "content_type": "text/html",
    }


class TestJSONStorage:
    async def test_save_and_read_single(self, sample_data: dict) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name
        try:
            storage = JSONStorage(filepath)
            await storage.save(sample_data)
            await storage.close()
            data = await storage.read_all()
            assert len(data) == 1
            assert data[0]["url"] == sample_data["url"]
            assert data[0]["title"] == sample_data["title"]
            assert data[0]["links"] == sample_data["links"]
        finally:
            os.unlink(filepath)

    async def test_save_multiple(self, sample_data: dict, sample_data_2: dict) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name
        try:
            storage = JSONStorage(filepath)
            await storage.save(sample_data)
            await storage.save(sample_data_2)
            await storage.close()
            data = await storage.read_all()
            assert len(data) == 2
            urls = [item["url"] for item in data]
            assert sample_data["url"] in urls
            assert sample_data_2["url"] in urls
        finally:
            os.unlink(filepath)

    async def test_flush_on_buffer_full(self, sample_data: dict) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name
        try:
            storage = JSONStorage(filepath)
            storage._buffer_size = 3
            for _ in range(3):
                await storage.save(sample_data)
            assert len(storage._buffer) == 0
            data = await storage.read_all()
            assert len(data) == 3
            await storage.close()
        finally:
            os.unlink(filepath)

    async def test_datetime_serialization(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name
        try:
            storage = JSONStorage(filepath)
            dt = datetime(2025, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
            data = {"url": "https://test.com", "crawled_at": dt}
            await storage.save(data)
            await storage.close()
            result = await storage.read_all()
            assert len(result) == 1
            assert "2025-06-15" in result[0]["crawled_at"]
        finally:
            os.unlink(filepath)

    async def test_read_empty_file(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name
        try:
            storage = JSONStorage(filepath)
            data = await storage.read_all()
            assert data == []
            await storage.close()
        finally:
            os.unlink(filepath)

    async def test_read_nonexistent_file(self) -> None:
        storage = JSONStorage("/tmp/nonexistent_file_12345.json")
        data = await storage.read_all()
        assert data == []

    async def test_get_stats(self, sample_data: dict) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name
        try:
            storage = JSONStorage(filepath)
            stats = storage.get_stats()
            assert "filepath" in stats
            assert "buffered" in stats
            assert "buffer_size" in stats
            await storage.close()
        finally:
            os.unlink(filepath)

    async def test_custom_indent(self, sample_data: dict) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name
        try:
            storage = JSONStorage(filepath, indent=4)
            await storage.save(sample_data)
            await storage.close()
            async with open(filepath, "r") as f:
                content = f.read()
            assert "    " in content
            data = await storage.read_all()
            assert len(data) == 1
        finally:
            os.unlink(filepath)


class TestCSVStorage:
    async def test_save_and_read_single(self, sample_data: dict) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            filepath = f.name
        try:
            storage = CSVStorage(filepath)
            await storage.save(sample_data)
            await storage.close()
            data = await storage.read_all()
            assert len(data) == 1
            assert data[0]["url"] == sample_data["url"]
            assert data[0]["title"] == sample_data["title"]
        finally:
            os.unlink(filepath)

    async def test_save_multiple(self, sample_data: dict, sample_data_2: dict) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            filepath = f.name
        try:
            storage = CSVStorage(filepath)
            await storage.save(sample_data)
            await storage.save(sample_data_2)
            await storage.close()
            data = await storage.read_all()
            assert len(data) == 2
        finally:
            os.unlink(filepath)

    async def test_headers_written_once(self, sample_data: dict) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            filepath = f.name
        try:
            storage = CSVStorage(filepath)
            await storage.save(sample_data)
            await storage.save(sample_data)
            await storage.close()
            with open(filepath, "r") as f:
                lines = f.readlines()
            header_count = sum(1 for line in lines if line.startswith("url,"))
            assert header_count == 1
        finally:
            os.unlink(filepath)

    async def test_list_serialization(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            filepath = f.name
        try:
            storage = CSVStorage(filepath)
            data = {
                "url": "https://test.com",
                "links": ["link1", "link2"],
                "metadata": {"key": "value"},
            }
            await storage.save(data)
            await storage.close()
            result = await storage.read_all()
            assert len(result) == 1
            assert "link1" in result[0]["links"]
        finally:
            os.unlink(filepath)

    async def test_special_characters(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            filepath = f.name
        try:
            storage = CSVStorage(filepath)
            data = {
                "url": "https://test.com",
                "title": "Title with, comma and \"quotes\"",
                "text": "Text with\nnewline",
            }
            await storage.save(data)
            await storage.close()
            result = await storage.read_all()
            assert len(result) == 1
            assert "comma" in result[0]["title"]
        finally:
            os.unlink(filepath)

    async def test_read_empty_file(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            filepath = f.name
        try:
            storage = CSVStorage(filepath)
            data = await storage.read_all()
            assert data == []
            await storage.close()
        finally:
            os.unlink(filepath)

    async def test_custom_delimiter(self, sample_data: dict) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            filepath = f.name
        try:
            storage = CSVStorage(filepath, delimiter=";")
            await storage.save(sample_data)
            await storage.close()
            data = await storage.read_all()
            assert len(data) == 1
        finally:
            os.unlink(filepath)

    async def test_get_stats(self, sample_data: dict) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            filepath = f.name
        try:
            storage = CSVStorage(filepath)
            await storage.save(sample_data)
            stats = storage.get_stats()
            assert "filepath" in stats
            assert "fieldnames" in stats
            assert "encoding" in stats
            await storage.close()
        finally:
            os.unlink(filepath)


class TestSQLiteStorage:
    async def test_init_db(self) -> None:
        storage = SQLiteStorage(":memory:")
        await storage.init_db()
        assert storage._db is not None
        await storage.close()

    async def test_save_and_read_single(self, sample_data: dict) -> None:
        storage = SQLiteStorage(":memory:")
        await storage.init_db()
        await storage.save(sample_data)
        await storage._flush()
        data = await storage.read_all()
        assert len(data) == 1
        assert data[0]["url"] == sample_data["url"]
        await storage.close()

    async def test_save_and_read_multiple(self, sample_data: dict, sample_data_2: dict) -> None:
        storage = SQLiteStorage(":memory:")
        await storage.init_db()
        await storage.save(sample_data)
        await storage.save(sample_data_2)
        await storage._flush()
        data = await storage.read_all()
        assert len(data) == 2
        urls = [item["url"] for item in data]
        assert sample_data["url"] in urls
        assert sample_data_2["url"] in urls
        await storage.close()

    async def test_batch_insert(self, sample_data: dict) -> None:
        storage = SQLiteStorage(":memory:")
        await storage.init_db()
        storage._buffer_size = 5
        for _ in range(10):
            await storage.save(sample_data)
        assert len(storage._buffer) == 0
        count = await storage.get_count()
        assert count == 10
        await storage.close()

    async def test_links_serialization(self) -> None:
        storage = SQLiteStorage(":memory:")
        await storage.init_db()
        data = {
            "url": "https://test.com",
            "links": ["link1", "link2", "link3"],
        }
        await storage.save(data)
        await storage._flush()
        result = await storage.read_all()
        assert len(result) == 1
        assert result[0]["links"] == ["link1", "link2", "link3"]
        await storage.close()

    async def test_metadata_serialization(self) -> None:
        storage = SQLiteStorage(":memory:")
        await storage.init_db()
        data = {
            "url": "https://test.com",
            "metadata": {"key": "value", "nested": {"a": 1}},
        }
        await storage.save(data)
        await storage._flush()
        result = await storage.read_all()
        assert len(result) == 1
        assert result[0]["metadata"]["key"] == "value"
        assert result[0]["metadata"]["nested"]["a"] == 1
        await storage.close()

    async def test_upsert_behavior(self, sample_data: dict) -> None:
        storage = SQLiteStorage(":memory:")
        await storage.init_db()
        await storage.save(sample_data)
        updated = sample_data.copy()
        updated["title"] = "Updated Title"
        await storage.save(updated)
        await storage._flush()
        count = await storage.get_count()
        assert count == 1
        data = await storage.read_all()
        assert data[0]["title"] == "Updated Title"
        await storage.close()

    async def test_get_count(self, sample_data: dict) -> None:
        storage = SQLiteStorage(":memory:")
        await storage.init_db()
        assert await storage.get_count() == 0
        await storage.save(sample_data)
        await storage._flush()
        assert await storage.get_count() == 1
        await storage.close()

    async def test_get_stats(self) -> None:
        storage = SQLiteStorage(":memory:")
        stats = storage.get_stats()
        assert "db_path" in stats
        assert "buffered" in stats
        assert "buffer_size" in stats
        await storage.close()

    async def test_empty_read(self) -> None:
        storage = SQLiteStorage(":memory:")
        await storage.init_db()
        data = await storage.read_all()
        assert data == []
        await storage.close()

    async def test_datetime_serialization_in_db(self) -> None:
        storage = SQLiteStorage(":memory:")
        await storage.init_db()
        dt = datetime(2025, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
        data = {"url": "https://test.com", "crawled_at": dt}
        await storage.save(data)
        await storage._flush()
        result = await storage.read_all()
        assert len(result) == 1
        assert "2025-06-15" in result[0]["crawled_at"]
        await storage.close()


class TestStorageErrorHandling:
    async def test_json_storage_continues_on_error(self, sample_data: dict) -> None:
        storage = JSONStorage("/nonexistent/path/file.json")
        try:
            await storage.save(sample_data)
        except Exception:
            pass
        await storage.close()

    async def test_csv_storage_invalid_path(self, sample_data: dict) -> None:
        storage = CSVStorage("/nonexistent/path/file.csv")
        try:
            await storage.save(sample_data)
        except Exception:
            pass
        await storage.close()

    async def test_sqlite_storage_close_without_save(self) -> None:
        storage = SQLiteStorage(":memory:")
        await storage.init_db()
        await storage.close()
        assert storage._db is None


class TestStorageIntegration:
    async def test_json_then_csv(self, sample_data: dict) -> None:
        json_path = tempfile.mktemp(suffix=".json")
        csv_path = tempfile.mktemp(suffix=".csv")
        try:
            json_storage = JSONStorage(json_path)
            csv_storage = CSVStorage(csv_path)

            await json_storage.save(sample_data)
            await csv_storage.save(sample_data)

            await json_storage.close()
            await csv_storage.close()

            json_data = await json_storage.read_all()
            csv_data = await csv_storage.read_all()

            assert len(json_data) == 1
            assert len(csv_data) == 1
            assert json_data[0]["url"] == csv_data[0]["url"]
        finally:
            if os.path.exists(json_path):
                os.unlink(json_path)
            if os.path.exists(csv_path):
                os.unlink(csv_path)

    async def test_json_then_sqlite(self, sample_data: dict) -> None:
        json_path = tempfile.mktemp(suffix=".json")
        try:
            json_storage = JSONStorage(json_path)
            sqlite_storage = SQLiteStorage(":memory:")
            await sqlite_storage.init_db()

            await json_storage.save(sample_data)
            await sqlite_storage.save(sample_data)

            await json_storage.close()
            await sqlite_storage.close()

            json_data = await json_storage.read_all()
            sqlite_storage2 = SQLiteStorage(":memory:")
            await sqlite_storage2.init_db()
            sqlite_data = await sqlite_storage2.read_all()
            await sqlite_storage2.close()

            assert len(json_data) == 1
            assert len(sqlite_data) == 0
        finally:
            if os.path.exists(json_path):
                os.unlink(json_path)
