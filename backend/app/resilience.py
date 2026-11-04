"""Fail fast during provider outages without replaying billable chat POSTs."""

import time
from collections.abc import Callable


class CircuitOpenError(Exception):
    """The provider is cooling down or already has a half-open probe."""


class CircuitBreaker:
    def __init__(
        self,
        threshold: int = 3,
        cooldown: float = 30,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.threshold = threshold
        self.cooldown = cooldown
        self.clock = clock
        self.failures = 0
        self.opened_at: float | None = None
        self.probing = False

    def acquire(self) -> None:
        if self.opened_at is None:
            return
        if self.clock() - self.opened_at < self.cooldown or self.probing:
            raise CircuitOpenError
        self.probing = True

    def success(self) -> None:
        self.failures = 0
        self.opened_at = None
        self.probing = False

    def failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold or self.probing:
            self.opened_at = self.clock()
        self.probing = False
