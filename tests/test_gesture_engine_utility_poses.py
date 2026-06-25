import time
import unittest
import sys
from collections import deque
from types import ModuleType
from types import SimpleNamespace

from core.config import (
    INTENT_POWERPOINT_SEC,
    INTENT_CROSS_SEC,
    INTENT_UNDO_SEC,
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

from core.gestur_engine import GestureEngine


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


def crossed_left_pose():
    hand = curled_fingers_pose()
    hand[0] = lm(0.4, 0.5)
    hand[9] = lm(0.3, 0.4)
    return hand


def crossed_right_pose():
    hand = curled_fingers_pose()
    hand[0] = lm(0.6, 0.5)
    hand[9] = lm(0.7, 0.4)
    return hand


def normal_left_pose():
    hand = curled_fingers_pose()
    hand[0] = lm(0.6, 0.5)
    hand[9] = lm(0.5, 0.4)
    return hand


def normal_right_pose():
    hand = curled_fingers_pose()
    hand[0] = lm(0.4, 0.5)
    hand[9] = lm(0.5, 0.4)
    return hand


def l_pose():
    hand = curled_fingers_pose()
    # open thumb
    hand[2] = lm(0.0, 0.15)
    hand[4] = lm(0.0, 0.30)
    # open index
    hand[6] = lm(0.05, 0.10)
    hand[8] = lm(0.05, 0.25)
    return hand


def thumbs_down_pose():
    hand = curled_fingers_pose()
    hand[2] = lm(0.0, 0.10)
    hand[4] = lm(0.0, 0.25)
    return hand


class GestureEngineUtilityPoseTests(unittest.TestCase):
    def setUp(self):
        self.engine = GestureEngine.__new__(GestureEngine)
        self.engine._calc_dist = GestureEngine._calc_dist
        self.engine._is_fist = GestureEngine._is_fist.__get__(self.engine, GestureEngine)
        self.engine._is_hand_open = GestureEngine._is_hand_open.__get__(self.engine, GestureEngine)
        self.engine._is_circle_pose = GestureEngine._is_circle_pose.__get__(self.engine, GestureEngine)
        self.engine._process_circle_state = GestureEngine._process_circle_state.__get__(self.engine, GestureEngine)
        self.engine._is_cross_pose = GestureEngine._is_cross_pose.__get__(self.engine, GestureEngine)
        self.engine._process_cross_state = GestureEngine._process_cross_state.__get__(self.engine, GestureEngine)
        self.engine._is_l_pose = GestureEngine._is_l_pose.__get__(self.engine, GestureEngine)
        self.engine._process_l_pose_state = GestureEngine._process_l_pose_state.__get__(self.engine, GestureEngine)
        self.engine._is_thumbs_down_pose = GestureEngine._is_thumbs_down_pose.__get__(self.engine, GestureEngine)
        self.engine._process_undo_state = GestureEngine._process_undo_state.__get__(self.engine, GestureEngine)
        self.engine._detect_swipe = GestureEngine._detect_swipe.__get__(self.engine, GestureEngine)
        self.engine._trigger_action = GestureEngine._trigger_action.__get__(self.engine, GestureEngine)
        self.engine._in_cooldown = GestureEngine._in_cooldown.__get__(self.engine, GestureEngine)
        self.engine.position_buffer = {"Left": deque(maxlen=20), "Right": deque(maxlen=20)}
        self.engine.last_action_time = 0
        self.engine.current_cooldown = 0
        self.engine.cross_intent_start = None
        self.engine.cross_triggered = False
        self.engine.l_pose_intent_start = None
        self.engine.l_pose_triggered = False
        self.engine.undo_intent_start = None
        self.engine.undo_triggered = False

    def test_two_hand_circle_opens_powerpoint_pose_only(self):
        all_hands = [("Left", circle_left_pose()), ("Right", circle_right_pose())]

        self.assertTrue(self.engine._is_circle_pose(all_hands, 1_000, 800))

    def test_held_two_hand_circle_triggers_powerpoint(self):
        self.engine.circle_intent_start = time.time() - INTENT_POWERPOINT_SEC - 0.1
        self.engine.circle_triggered = False
        self.engine.last_action_name = ""
        actions = []
        self.engine.callback = actions.append

        self.engine._process_circle_state(
            [("Left", circle_left_pose()), ("Right", circle_right_pose())],
            1_000,
            800,
        )

        self.assertEqual(["open_powerpoint"], actions)
        self.assertEqual("open_powerpoint", self.engine.last_action_name)
        self.assertTrue(self.engine.circle_triggered)

    def test_two_hand_cross_pose_only(self):
        crossed_hands = [("Left", crossed_left_pose()), ("Right", crossed_right_pose())]
        self.assertTrue(self.engine._is_cross_pose(crossed_hands, 1_000, 800))
        
        normal_hands = [("Left", normal_left_pose()), ("Right", normal_right_pose())]
        self.assertFalse(self.engine._is_cross_pose(normal_hands, 1_000, 800))

    def test_held_two_hand_cross_triggers_delete_slide(self):
        self.engine.cross_intent_start = time.time() - INTENT_CROSS_SEC - 0.1
        self.engine.cross_triggered = False
        self.engine.last_action_name = ""
        actions = []
        self.engine.callback = actions.append

        self.engine._process_cross_state(
            [("Left", crossed_left_pose()), ("Right", crossed_right_pose())],
            1_000,
            800,
        )

        self.assertEqual(["delete_slide"], actions)
        self.assertEqual("delete_slide", self.engine.last_action_name)
        self.assertTrue(self.engine.cross_triggered)

    def test_l_pose_only(self):
        l_pose_hand = l_pose()
        self.assertTrue(self.engine._is_l_pose(l_pose_hand, 1_000, 800))
        
        normal_hand = normal_left_pose()
        self.assertFalse(self.engine._is_l_pose(normal_hand, 1_000, 800))

    def test_held_l_pose_triggers_delete_slide(self):
        self.engine.l_pose_intent_start = time.time() - INTENT_CROSS_SEC - 0.1
        self.engine.l_pose_triggered = False
        self.engine.last_action_name = ""
        actions = []
        self.engine.callback = actions.append

        self.engine._process_l_pose_state(True)

        self.assertEqual(["delete_slide"], actions)
        self.assertEqual("delete_slide", self.engine.last_action_name)
        self.assertTrue(self.engine.l_pose_triggered)
    def test_thumbs_down_pose_only(self):
        thumbs_down_hand = thumbs_down_pose()
        self.assertTrue(self.engine._is_thumbs_down_pose(thumbs_down_hand, 1_000, 800))
        
        normal_hand = normal_left_pose()
        self.assertFalse(self.engine._is_thumbs_down_pose(normal_hand, 1_000, 800))

    def test_held_thumbs_down_triggers_undo(self):
        self.engine.undo_intent_start = time.time() - INTENT_UNDO_SEC - 0.1
        self.engine.undo_triggered = False
        self.engine.last_action_name = ""
        actions = []
        self.engine.callback = actions.append

        self.engine._process_undo_state(True)

        self.assertEqual(["undo"], actions)
        self.assertEqual("undo", self.engine.last_action_name)
        self.assertTrue(self.engine.undo_triggered)


if __name__ == "__main__":
    unittest.main()
