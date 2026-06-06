import unittest

from clipboard_ring import ClipboardRing
from clipboard_commands import ClipboardCommandService


class _FakeClock:
    def __init__(self):
        self._count = 0

    def __call__(self):
        self._count += 1
        return f"2026-01-01T00:00:{self._count:02d}+07:00"


class ClipboardCommandServiceTests(unittest.TestCase):
    def setUp(self):
        self.pasted_texts = []
        self.ring = ClipboardRing(
            max_size=10,
            poll_interval=60,
            clock=_FakeClock(),
            inserter=self.pasted_texts.append,
        )
        self.ring._push("item satu")
        self.ring._push("item dua")
        self.ring._push("item tiga")
        self.service = ClipboardCommandService(self.ring)

    def test_voice_paste_nomor(self):
        payload = self.service.handle_text("tempel nomor 2")
        self.assertEqual("success", payload["status"])
        self.assertEqual("clipboard_paste", payload["command"])
        self.assertEqual(["item dua"], self.pasted_texts)

    def test_voice_paste_ordinal(self):
        payload = self.service.handle_text("tempel kedua")
        self.assertEqual("success", payload["status"])
        self.assertEqual(["item dua"], self.pasted_texts)

    def test_voice_paste_sebelumnya(self):
        payload = self.service.handle_text("tempel yang sebelumnya")
        self.assertEqual("success", payload["status"])
        # "sebelumnya" = position 2
        self.assertEqual(["item dua"], self.pasted_texts)

    def test_voice_paste_invalid_position(self):
        payload = self.service.handle_text("tempel nomor 99")
        self.assertEqual("error", payload["status"])
        self.assertEqual([], self.pasted_texts)

    def test_voice_clear_clipboard(self):
        payload = self.service.handle_text("hapus riwayat clipboard")
        self.assertEqual("success", payload["status"])
        self.assertEqual("clipboard_clear", payload["command"])
        self.assertEqual(0, len(self.ring.get_ring()))

    def test_voice_lihat_clipboard(self):
        payload = self.service.handle_text("lihat clipboard")
        self.assertEqual("success", payload["status"])
        self.assertTrue("items" in payload)
        self.assertEqual(3, len(payload["items"]))

    def test_unrelated_text_returns_none(self):
        result = self.service.handle_text("selamat pagi semuanya")
        self.assertIsNone(result)
        self.assertEqual([], self.pasted_texts)

    def test_paste_with_tolong_prefix(self):
        payload = self.service.handle_text("tolong tempel nomor 1")
        self.assertEqual("success", payload["status"])
        self.assertEqual(["item tiga"], self.pasted_texts)

    def test_paste_sebelumnya_variant(self):
        payload = self.service.handle_text("paste sebelumnya")
        self.assertEqual("success", payload["status"])
        self.assertEqual(["item dua"], self.pasted_texts)


if __name__ == "__main__":
    unittest.main()
