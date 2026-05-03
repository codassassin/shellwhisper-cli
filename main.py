from textual.app import App, ComposeResult
from textual.widgets import Header, Footer

from chat_screen import ChatScreen
from login import LoginScreen, SignupScreen

class TerminalChatApp(App):
    SCREENS = {
        "login": LoginScreen,
        "chat": ChatScreen,
        "signup": SignupScreen
    }
    BINDINGS = [
        ("ctrl+d", "toggle_dark", "Toggle dark mode"),
        ("ctrl+q", "quit", "Quit"),
    ]
    CSS_PATH = "login.tcss"

    def on_mount(self) -> None:
        # self.push_screen(LoginScreen())
        self.push_screen(ChatScreen())

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def __init__(self):
        super().__init__()
        print("Welcome to the Terminal Chat App!")

if __name__ == "__main__":
    app = TerminalChatApp()
    app.run()
