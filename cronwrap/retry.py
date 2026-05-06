"""Retry logic for cron job execution."""

import time
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


def with_retry(
    fn: Callable,
    retries: int = 0,
    delay: float = 5.0,
    backoff: float = 1.0,
    on_failure: Optional[Callable[[int, Exception], None]] = None,
) -> any:
    """Execute *fn* with retry logic.

    Args:
        fn: Zero-argument callable to execute.
        retries: Maximum number of additional attempts after the first failure.
        delay: Seconds to wait between attempts.
        backoff: Multiplier applied to *delay* after each failure (1.0 = no backoff).
        on_failure: Optional callback invoked with (attempt_number, exception) on each
                    failed attempt before a retry.

    Returns:
        The return value of *fn* on success.

    Raises:
        The last exception raised by *fn* when all attempts are exhausted.
    """
    if retries < 0:
        raise ValueError("retries must be >= 0")
    if delay < 0:
        raise ValueError("delay must be >= 0")
    if backoff < 1.0:
        raise ValueError("backoff must be >= 1.0")

    last_exc: Optional[Exception] = None
    current_delay = delay

    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if on_failure is not None:
                try:
                    on_failure(attempt, exc)
                except Exception:  # noqa: BLE001
                    logger.warning("on_failure callback raised an exception", exc_info=True)

            if attempt < retries:
                logger.info(
                    "Attempt %d/%d failed (%s). Retrying in %.1fs …",
                    attempt + 1,
                    retries + 1,
                    exc,
                    current_delay,
                )
                time.sleep(current_delay)
                current_delay *= backoff
            else:
                logger.warning(
                    "All %d attempt(s) failed. Last error: %s",
                    retries + 1,
                    exc,
                )

    raise last_exc
