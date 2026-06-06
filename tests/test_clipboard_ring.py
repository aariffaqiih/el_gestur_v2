import unittest

from clipboard_ring import ClipboardItem, ClipboardItemNotFoundError, ClipboardRing


class _FakeClock:
    def __init__(self, initial="2026-01-01T00:00:00+07:00"):
        self.value = initial
        self._call_count = 0

    def __call__(self):
        self._call_count += 1
        return f"{self.value}_{self._call_count}"


class ClipboardRingTests(unittest.TestCase):
    def setUp(self):
        self.clock = _FakeClock()
        self.pasted_texts = []
        self.ring = ClipboardRing(
            max_size=5,
            poll_interval=60,
            clock=self.clock,
            inserter=self.pasted_texts.append,
        )

    def test_push_and_get_ring(self):
        self.ring._push("hello")
        self.ring._push("world")

        items = self.ring.get_ring()
        self.assertEqual(2, len(items))
        self.assertEqual("world", items[0]["text"])
        self.assertEqual("hello", items[1]["text"])
        self.assertEqual(1, items[0]["position"])
        self.assertEqual(2, items[1]["position"])

    def test_deduplication_moves_item_to_front(self):
        self.ring._push("aaa")
        self.ring._push("bbb")
        self.ring._push("aaa")

        items = self.ring.get_ring()
        self.assertEqual(2, len(items))
        self.assertEqual("aaa", items[0]["text"])
        self.assertEqual("bbb", items[1]["text"])

    def test_consecutive_duplicate_ignored(self):
        self.ring._push("same")
        self.ring._push("same")

        self.assertEqual(1, len(self.ring.get_ring()))

    def test_max_size_respected(self):
        for i in range(10):
            self.ring._push(f"item-{i}")

        self.assertEqual(5, len(self.ring.get_ring()))

    def test_get_item_valid(self):
        self.ring._push("first")
        item = self.ring.get_item(1)
        self.assertEqual("first", item.text)

    def test_get_item_invalid_position(self):
        self.ring._push("only")
        with self.assertRaises(ClipboardItemNotFoundError):
            self.ring.get_item(5)

    def test_paste_item(self):
        self.ring._push("alpha")
        self.ring._push("beta")

        result = self.ring.paste_item(2)
        self.assertEqual("alpha", result["text"])
        self.assertEqual(["alpha"], self.pasted_texts)

    def test_clear(self):
        self.ring._push("data")
        self.ring.clear()
        self.assertEqual(0, len(self.ring.get_ring()))

    def test_status(self):
        self.ring._push("x")
        status = self.ring.get_status()
        self.assertEqual(1, status["count"])
        self.assertEqual(5, status["max_size"])
        self.assertFalse(status["is_running"])


if __name__ == "__main__":
    unittest.main()
