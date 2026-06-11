import time
import unittest
import sys
from collections import deque
from types import ModuleType
from types import SimpleNamespace

from config import (
    INTENT_POWERPOINT_SEC,
)


def install_gesture_dependency_stubs():
    cv2_stub = ModuleType("cv2")
    cv2_stub.COLOR_BGR2RGB = 0
    cv2_stub.cvtColor = lambda frame, _code: frame
    sys.modules.setdefault("cv2", cv2_stub)

    pyautogui_stub = ModuleType("pyautogui")
    pyautogui_stub.size = lambda: (1920, 1080)
    sys.modules.setdefault("pyautogui", pyautogui_stub)

    mediapipe_stub = ModuleType("mediapipe")
    mediapipe_stub.solutions = SimpleNamespace(
        hands=SimpleNamespace(Hands=object, HAND_CONNECTIONS=()),
        drawing_utils=SimpleNamespace(draw_landmarks=lambda *args, **kwargs: None),
        drawing_styles=SimpleNamespace(
            get_default_hand_landmarks_style=lambda: None,
            get_default_hand_connections_style=lambda: None,
        ),
    )
    sys.modules.setdefault("mediapipe", mediapipe_stub)


install_gesture_dependency_stubs()

from gestur_engine import GestureEngine


def lm(x, y):
    return SimpleNamespace(x=x, y=y)


def base_hand():
    return [lm(0.0, 0.0) for _ in range(21)]


def curled_fingers_pose():
    hand = base_hand()
    hand[0] = lm(0.0, 0.0)
    for tip, pip, x in [(8, 6, 0.05), (12, 10, 0.10), (16, 14, 0.15), (20, 18, 0.20)]:
        hand[pip] = lm(x, 0.30)
        hand[tip] = lm(x, 0.12)
    return hand


def circle_left_pose():
    hand = curled_fingers_pose()
    hand[0] = lm(0.34, 0.62)
    hand[2] = lm(0.40, 0.58)
    hand[4] = lm(0.49, 0.64)
    hand[5] = lm(0.40, 0.50)
    hand[6] = lm(0.43, 0.46)
    hand[8] = lm(0.49, 0.36)
    hand[9] = lm(0.38, 0.50)
    return hand


def circle_right_pose():
    hand = curled_fingers_pose()
    hand[0] = lm(0.66, 0.62)
    hand[2] = lm(0.60, 0.58)
    hand[4] = lm(0.51, 0.64)
    hand[5] = lm(0.60, 0.50)
    hand[6] = lm(0.57, 0.46)
    hand[8] = lm(0.51, 0.36)
    hand[9] = lm(0.62, 0.50)
    return hand


class GestureEngineUtilityPoseTests(unittest.TestCase):
    def setUp(self):
        self.engine = GestureEngine.__new__(GestureEngine)
        self.engine._calc_dist = GestureEngine._calc_dist
        self.engine._is_fist = GestureEngine._is_fist.__get__(self.engine, GestureEngine)
        self.engine._is_hand_open = GestureEngine._is_hand_open.__get__(self.engine, GestureEngine)
        self.engine._is_l_pose = GestureEngine._is_l_pose.__get__(self.engine, GestureEngine)
        self.engine._is_open_powerpoint_pose = GestureEngine._is_open_powerpoint_pose.__get__(self.engine, GestureEngine)
        self.engine._detect_open_powerpoint = GestureEngine._detect_open_powerpoint.__get__(self.engine, GestureEngine)
        self.engine._detect_swipe = GestureEngine._detect_swipe.__get__(self.engine, GestureEngine)
        self.engine.position_buffer = {"Left": deque(maxlen=20), "Right": deque(maxlen=20)}

    def test_two_hand_circle_opens_powerpoint_pose_only(self):
        all_hands = [("Left", circle_left_pose()), ("Right", circle_right_pose())]

        self.assertTrue(self.engine._is_open_powerpoint_pose(all_hands, 1_000, 800))

    def test_held_two_hand_circle_triggers_powerpoint(self):
        self.engine.powerpoint_intent_start = time.time() - INTENT_POWERPOINT_SEC - 0.1
        self.engine.powerpoint_triggered = False
        self.engine.last_powerpoint_time = 0
        self.engine.last_action_name = ""
        actions = []
        self.engine.callback = actions.append

        self.engine._detect_open_powerpoint(
            [("Left", circle_left_pose()), ("Right", circle_right_pose())],
            1_000,
            800,
        )

        self.assertEqual(["open_powerpoint"], actions)
        self.assertEqual("open_powerpoint", self.engine.last_action_name)
        self.assertTrue(self.engine.powerpoint_triggered)


if __name__ == "__main__":
    unittest.main()
