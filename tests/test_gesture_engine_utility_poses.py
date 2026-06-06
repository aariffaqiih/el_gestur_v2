import time
import unittest
from types import SimpleNamespace

from config import COOLDOWN_UNDO_MS, INTENT_UNDO_SEC
from gestur_engine import GestureEngine


def lm(x, y):
    return SimpleNamespace(x=x, y=y)


def shift_pose(landmarks, dx):
    return [lm(point.x + dx, point.y) for point in landmarks]


def base_hand():
    return [lm(0.0, 0.0) for _ in range(21)]


def curled_fingers_pose():
    hand = base_hand()
    hand[0] = lm(0.0, 0.0)
    for tip, pip, x in [(8, 6, 0.05), (12, 10, 0.10), (16, 14, 0.15), (20, 18, 0.20)]:
        hand[pip] = lm(x, 0.30)
        hand[tip] = lm(x, 0.12)
    return hand


def shaka_pose():
    hand = curled_fingers_pose()
    hand[2] = lm(0.08, 0.05)
    hand[3] = lm(0.12, 0.03)
    hand[4] = lm(0.22, 0.02)
    hand[18] = lm(0.20, 0.16)
    hand[20] = lm(0.30, 0.42)
    return hand


def peace_pose():
    hand = curled_fingers_pose()
    hand[2] = lm(0.10, 0.05)
    hand[4] = lm(0.06, 0.06)
    hand[6] = lm(0.05, 0.20)
    hand[8] = lm(0.05, 0.42)
    hand[10] = lm(0.10, 0.20)
    hand[12] = lm(0.10, 0.42)
    return hand


def thumbs_up_pose():
    hand = curled_fingers_pose()
    hand[2] = lm(0.08, 0.08)
    hand[3] = lm(0.12, 0.08)
    hand[4] = lm(0.18, 0.00)
    return hand


class GestureEngineUtilityPoseTests(unittest.TestCase):
    def setUp(self):
        self.engine = GestureEngine.__new__(GestureEngine)
        self.engine._calc_dist = GestureEngine._calc_dist
        self.engine._is_fist = GestureEngine._is_fist.__get__(self.engine, GestureEngine)
        self.engine._is_hand_open = GestureEngine._is_hand_open.__get__(self.engine, GestureEngine)
        self.engine._is_l_pose = GestureEngine._is_l_pose.__get__(self.engine, GestureEngine)
        self.engine._is_thumbs_up = GestureEngine._is_thumbs_up.__get__(self.engine, GestureEngine)
        self.engine._is_peace_pose = GestureEngine._is_peace_pose.__get__(self.engine, GestureEngine)
        self.engine._is_shaka_pose = GestureEngine._is_shaka_pose.__get__(self.engine, GestureEngine)
        self.engine._is_select_all_pose = GestureEngine._is_select_all_pose.__get__(self.engine, GestureEngine)
        self.engine._is_open_word_pose = GestureEngine._is_open_word_pose.__get__(self.engine, GestureEngine)
        self.engine._detect_undo = GestureEngine._detect_undo.__get__(self.engine, GestureEngine)

    def test_shaka_pose_triggers_undo(self):
        self.engine.undo_intent_start = {"Left": time.time() - INTENT_UNDO_SEC - 0.1, "Right": None}
        self.engine.undo_triggered = {"Left": False, "Right": False}
        self.engine._in_cooldown = lambda: False
        actions = []
        self.engine._trigger_action = lambda action, cooldown: actions.append((action, cooldown))

        self.engine._detect_undo("Left", shaka_pose(), 1_000, 800)

        self.assertEqual([("undo", COOLDOWN_UNDO_MS)], actions)

    def test_double_peace_is_select_all_not_laser_l_pose(self):
        left = peace_pose()
        right = shift_pose(peace_pose(), 0.25)

        self.assertTrue(self.engine._is_select_all_pose([("Left", left), ("Right", right)], 1_000, 800))
        self.assertFalse(self.engine._is_l_pose(left, 1_000, 800))

    def test_double_thumbs_up_opens_word(self):
        left = thumbs_up_pose()
        right = shift_pose(thumbs_up_pose(), 0.25)

        self.assertTrue(self.engine._is_open_word_pose([("Left", left), ("Right", right)], 1_000, 800))
        self.assertFalse(self.engine._is_select_all_pose([("Left", left), ("Right", right)], 1_000, 800))


if __name__ == "__main__":
    unittest.main()
