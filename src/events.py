from textual.message import Message

class NewWhisperReceived(Message):
    def __init__(self, data: dict) -> None:
        self.data = data
        super().__init__()