import unittest
from collections import deque
from types import SimpleNamespace

from config import COOLDOWN_REDO_MS
from gestur_engine import GestureEngine


class FakeSwipeDetector:
    def __init__(self, action="redo"):
        self.action = action
        self.reset_calls = []
        self.update_calls = []

    def update(self, hand_label, **kwargs):
        self.update_calls.append((hand_label, kwargs))
        return self.action

    def reset(self, hand_label=None):
        self.reset_calls.append(hand_label)


class GestureEngineRedoIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = GestureEngine.__new__(GestureEngine)
        self.engine.redo_swipe_detector = FakeSwipeDetector()
        self.engine.start_state = {
            "Left": {"stage": 1},
            "Right": {"stage": 2},
        }
        self.engine.position_buffer = {
            "Left": deque([(1, 2, 3)]),
            "Right": deque(),
        }
        self.engine._in_cooldown = lambda: False
        self.engine._is_redo_fist_pose = lambda _landmarks, _w, _h: True
        self.actions = []
        self.engine._trigger_action = lambda action, cooldown: self.actions.append((action, cooldown))
        self.landmarks = [SimpleNamespace(x=0.25, y=0.50)]

    def test_single_valid_fist_swipe_triggers_redo_and_resets_start_state(self):
        self.engine._process_redo_gesture(
            [("Left", self.landmarks)],
            1_000,
            800,
            blocked=False,
        )

        self.assertEqual([("redo", COOLDOWN_REDO_MS)], self.actions)
        self.assertEqual(0, self.engine.start_state["Left"]["stage"])
        self.assertEqual(0, self.engine.start_state["Right"]["stage"])
        self.assertEqual([], list(self.engine.position_buffer["Left"]))

    def test_two_valid_hands_reset_motion_state_without_triggering_redo(self):
        self.engine._process_redo_gesture(
            [("Left", self.landmarks), ("Right", self.landmarks)],
            1_000,
            800,
            blocked=False,
        )

        self.assertEqual([], self.actions)
        self.assertEqual([None], self.engine.redo_swipe_detector.reset_calls)

    def test_two_hand_utility_pose_blocks_redo(self):
        self.engine._process_redo_gesture(
            [("Left", self.landmarks)],
            1_000,
            800,
            blocked=True,
        )

        self.assertEqual([], self.actions)
        self.assertEqual([None], self.engine.redo_swipe_detector.reset_calls)


if __name__ == "__main__":
    unittest.main()
