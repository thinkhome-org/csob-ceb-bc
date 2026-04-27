from csob_ceb_bc.logging import get_logger


def test_logger_returns_structlog():
    logger = get_logger("test")
    # Just ensure it doesn't crash and has expected methods
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")
