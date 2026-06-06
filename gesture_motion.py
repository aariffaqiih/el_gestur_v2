from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class HorizontalSwipeConfig:
    action: str
    direction: str
    min_distance_ratio: float
    min_speed_ratio_per_second: float
    max_vertical_ratio: float
    sample_window_ms: float
    min_samples: int = 4

    def __post_init__(self) -> None:
        if self.direction not in {"left", "right"}:
            raise ValueError("direction harus bernilai 'left' atau 'right'.")
        if not self.action:
            raise ValueError("action tidak boleh kosong.")
        if self.min_distance_ratio <= 0:
            raise ValueError("min_distance_ratio harus lebih besar dari nol.")
        if self.min_speed_ratio_per_second <= 0:
            raise ValueError("min_speed_ratio_per_second harus lebih besar dari nol.")
        if self.max_vertical_ratio < 0:
            raise ValueError("max_vertical_ratio tidak boleh negatif.")
        if self.sample_window_ms <= 0:
            raise ValueError("sample_window_ms harus lebih besar dari nol.")
        if self.min_samples < 2:
            raise ValueError("min_samples minimal bernilai dua.")


class HorizontalSwipeDetector:
    """Detect a horizontal pose movement while remaining independent from camera libraries."""

    def __init__(
        self,
        config: HorizontalSwipeConfig,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.config = config
        self._clock = clock
        self._buffers: dict[str, deque[tuple[float, float, float]]] = {}

    def update(
        self,
        hand_label: str,
        *,
        x: float,
        y: float,
        frame_width: int,
        frame_height: int,
        timestamp_ms: float | None = None,
    ) -> str | None:
        if frame_width <= 0 or frame_height <= 0:
            raise ValueError("Ukuran frame harus lebih besar dari nol.")

        current_timestamp = timestamp_ms if timestamp_ms is not None else self._clock() * 1000
        buffer = self._buffers.setdefault(hand_label, deque())
        buffer.append((x * frame_width, y * frame_height, current_timestamp))
        self._drop_expired_samples(buffer, current_timestamp)

        if len(buffer) < self.config.min_samples:
            return None

        start_x, start_y, start_timestamp = buffer[0]
        end_x, end_y, end_timestamp = buffer[-1]
        elapsed_seconds = (end_timestamp - start_timestamp) / 1000
        if elapsed_seconds <= 0:
            return None

        delta_x = end_x - start_x
        delta_y = end_y - start_y
        if abs(delta_y) > frame_height * self.config.max_vertical_ratio:
            self.reset(hand_label)
            return None

        signed_delta_x = delta_x if self.config.direction == "right" else -delta_x
        if signed_delta_x <= 0:
            if abs(delta_x) >= frame_width * self.config.min_distance_ratio:
                self.reset(hand_label)
            return None

        speed_x = signed_delta_x / elapsed_seconds
        if signed_delta_x < frame_width * self.config.min_distance_ratio:
            return None
        if speed_x < frame_width * self.config.min_speed_ratio_per_second:
            return None

        self.reset(hand_label)
        return self.config.action

    def reset(self, hand_label: str | None = None) -> None:
        if hand_label is None:
            self._buffers.clear()
        else:
            self._buffers.pop(hand_label, None)

    def _drop_expired_samples(
        self,
        buffer: deque[tuple[float, float, float]],
        current_timestamp: float,
    ) -> None:
        minimum_timestamp = current_timestamp - self.config.sample_window_ms
        while buffer and buffer[0][2] < minimum_timestamp:
            buffer.popleft()
