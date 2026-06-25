import unittest

from core.voice_typer import VoiceTyper


class VoiceTyperPipelineTests(unittest.TestCase):
    def test_dynamic_command_is_handled_without_typing_text(self):
        typed_texts = []
        voice_typer = VoiceTyper.__new__(VoiceTyper)
        voice_typer._command_handler = lambda text: {
            "status": "success",
            "command": "document_search",
            "query": text,
        }
        voice_typer.VOICE_COMMANDS = {}
        voice_typer.last_text = ""
        voice_typer._type_text = typed_texts.append

        result = voice_typer.process_text("cari dokumen proposal")

        self.assertEqual("document_search", result["command"])
        self.assertEqual([], typed_texts)
        self.assertEqual("[Command] cari dokumen proposal", voice_typer.last_text)

    def test_regular_text_is_still_typed(self):
        typed_texts = []
        voice_typer = VoiceTyper.__new__(VoiceTyper)
        voice_typer._command_handler = lambda _text: None
        voice_typer.VOICE_COMMANDS = {}
        voice_typer.last_text = ""
        voice_typer._type_text = typed_texts.append

        result = voice_typer.process_text("selamat pagi")

        self.assertEqual({"status": "success", "typed": "Selamat pagi"}, result)
        self.assertEqual(["Selamat pagi"], typed_texts)


    def test_device_index_initialization_and_update(self):
        # Test default initialization
        vt = VoiceTyper(device_index=1)
        self.assertEqual(vt.device_index, 1)
        self.assertEqual(vt.microphone.device_index, 1)

        # Test setting device index to other integers
        vt.set_device_index(3)
        self.assertEqual(vt.device_index, 3)
        self.assertEqual(vt.microphone.device_index, 3)

        # Test setting device index to default/invalid
        vt.set_device_index("default")
        self.assertIsNone(vt.device_index)
        self.assertIsNone(vt.microphone.device_index)

        vt.set_device_index("")
        self.assertIsNone(vt.device_index)

        vt.set_device_index("invalid")
        self.assertIsNone(vt.device_index)


    def test_smart_punctuation_and_capitalization(self):
        typed_texts = []
        voice_typer = VoiceTyper.__new__(VoiceTyper)
        voice_typer._command_handler = lambda _text: None
        voice_typer.VOICE_COMMANDS = {}
        voice_typer.last_text = ""
        voice_typer.capitalize_next = True
        voice_typer._type_text = typed_texts.append

        # Test initial capitalization and punctuation conversion
        result1 = voice_typer.process_text("halo koma selamat pagi titik")
        self.assertEqual("Halo, selamat pagi.", result1["typed"])

        # Test capitalization after sentence-ending punctuation (from previous run)
        # Because result1 ended with a period ".", capitalize_next is reset to True in process_text.
        result2 = voice_typer.process_text("bagaimana kabar anda hari ini tanda tanya")
        self.assertEqual("Bagaimana kabar anda hari ini?", result2["typed"])
        
        # Test punctuation spacing cleanup and mid-text capitalization
        result3 = voice_typer.process_text("saya pergi titik dia tinggal titik")
        self.assertEqual("Saya pergi. Dia tinggal.", result3["typed"])

        # Test punctuation at the start of sentence
        voice_typer.capitalize_next = True
        result4 = voice_typer.process_text("buka kurung halo tutup kurung")
        self.assertEqual(" (Halo) ", result4["typed"])

        # Test partial matching avoidance (word boundary safety)
        voice_typer.capitalize_next = True
        result5 = voice_typer.process_text("komando pasukan khusus")
        self.assertEqual("Komando pasukan khusus", result5["typed"])

    def test_is_muted_blocks_processing(self):
        typed_texts = []
        voice_typer = VoiceTyper.__new__(VoiceTyper)
        voice_typer._command_handler = lambda _text: None
        voice_typer.VOICE_COMMANDS = {}
        voice_typer.last_text = ""
        voice_typer.is_muted = True
        voice_typer._type_text = typed_texts.append

        result = voice_typer.process_text("halo apa kabar")
        self.assertEqual("muted", result["status"])
        self.assertEqual([], typed_texts)

        # Unmute and check it types again
        voice_typer.is_muted = False
        result2 = voice_typer.process_text("halo apa kabar")
        self.assertEqual("success", result2["status"])
        self.assertEqual(["Halo apa kabar"], typed_texts)


if __name__ == "__main__":
    unittest.main()
