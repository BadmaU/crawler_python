import logging
import os
import tempfile

from crawler_python.logging_setup import setup_logging
from crawler_python.monitor import ProgressMonitor


def test_setup_logging_file():
    with tempfile.TemporaryDirectory() as d:
        log_path = os.path.join(d, "app.log")
        logger = setup_logging(level="INFO", log_file=log_path, name="ln1", force=True)
        logger.info("тест")
        for h in list(logger.handlers):
            h.flush()
        # RotatingFileHandler не всегда flush на диск сразу, но файл должен появиться
        assert os.path.exists(log_path)


def test_setup_logging_no_duplicate_handlers():
    name = "ln_unique"
    setup_logging(level="INFO", log_file=None, console=False, name=name)
    setup_logging(level="INFO", log_file=None, console=False, name=name)
    logger = logging.getLogger(name)
    assert len(logger.handlers) <= 1


def test_level_filter():
    from crawler_python.logging_setup import LevelFilter
    f = LevelFilter(logging.WARNING)
    rec = logging.LogRecord("n", logging.INFO, "", 0, "m", (), None)
    assert not f.filter(rec)
    rec2 = logging.LogRecord("n", logging.ERROR, "", 0, "m", (), None)
    assert f.filter(rec2)


def test_monitor_disabled():
    m = ProgressMonitor(enabled=False)
    m.set_total(10)
    m.set_callbacks(progress=lambda: 5, marks=lambda: 2)
    import asyncio
    asyncio.run(m.start())
    asyncio.run(m.stop())
    # ничего не падает


def test_monitor_enabled():
    m = ProgressMonitor(enabled=True, interval=0.01)
    m.set_total(100)
    m.set_callbacks(progress=lambda: 42, marks=lambda: 3)
    import asyncio
    asyncio.run(m.start())
    asyncio.run(asyncio.sleep(0.05))
    asyncio.run(m.stop())


def test_monitor_format():
    m = ProgressMonitor(enabled=False)
    line = m._format_line(
        count=42, percent=50.0, speed=3.5, remaining=15.0, active=4, elapsed=12.0
    )
    assert "42" in line
    assert "50.0%" in line
    assert "3.5" in line
    assert "ETA" in line


def test_monitor_eta():
    m = ProgressMonitor(enabled=False)
    assert m._fmt_eta(float("inf")) == "—"
    assert m._fmt_eta(5) == "5с"
    assert m._fmt_eta(95) == "1м 35с"
