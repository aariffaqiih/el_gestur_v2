import unittest

from gesture_motion import HorizontalSwipeConfig, HorizontalSwipeDetector


def create_redo_detector(**overrides):
    config_values = {
        "action": "redo",
        "direction": "right",
        "min_distance_ratio": 0.15,
        "min_speed_ratio_per_second": 0.50,
        "max_vertical_ratio": 0.10,
        "sample_window_ms": 700,
        "min_samples": 4,
    }
    config_values.update(overrides)
    return HorizontalSwipeDetector(HorizontalSwipeConfig(**config_values))


class HorizontalSwipeDetectorTests(unittest.TestCase):
    def test_fast_right_swipe_triggers_redo(self):
        detector = create_redo_detector()

        actions = self._feed(
            detector,
            [(0.20, 0.50, 0), (0.26, 0.50, 80), (0.32, 0.51, 160), (0.42, 0.51, 240)],
        )

        self.assertEqual(["redo"], actions)

    def test_left_swipe_does_not_trigger_right_swipe_action(self):
        detector = create_redo_detector()

        actions = self._feed(
            detector,
            [(0.70, 0.50, 0), (0.62, 0.50, 80), (0.54, 0.50, 160), (0.45, 0.50, 240)],
        )

        self.assertEqual([], actions)

    def test_vertical_movement_is_rejected(self):
        detector = create_redo_detector()

        actions = self._feed(
            detector,
            [(0.20, 0.30, 0), (0.27, 0.38, 80), (0.34, 0.47, 160), (0.42, 0.58, 240)],
        )

        self.assertEqual([], actions)

    def test_slow_movement_is_rejected(self):
        detector = create_redo_detector(sample_window_ms=2_000)

        actions = self._feed(
            detector,
            [(0.20, 0.50, 0), (0.27, 0.50, 600), (0.34, 0.50, 1_200), (0.42, 0.50, 1_800)],
        )

        self.assertEqual([], actions)

    def test_reset_discards_previous_samples(self):
        detector = create_redo_detector()
        self._feed(detector, [(0.20, 0.50, 0), (0.27, 0.50, 80)])

        detector.reset("Left")
        actions = self._feed(detector, [(0.34, 0.50, 160), (0.42, 0.50, 240)])

        self.assertEqual([], actions)

    @staticmethod
    def _feed(detector, points):
        return [
            action
            for x, y, timestamp_ms in points
            if (action := detector.update(
                "Left",
                x=x,
                y=y,
                frame_width=1_000,
                frame_height=800,
                timestamp_ms=timestamp_ms,
            ))
        ]


if __name__ == "__main__":
    unittest.main()
