import unittest

from voice_typer import VoiceTyper


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

        self.assertEqual({"status": "success", "typed": "selamat pagi"}, result)
        self.assertEqual(["selamat pagi"], typed_texts)


if __name__ == "__main__":
    unittest.main()
