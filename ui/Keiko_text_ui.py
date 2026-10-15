import json
import sys

import requests
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QMovie, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import (QApplication, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget)

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma3n:e4b"
DEFAULT_SYSTEM = "You are a helpful assistant. Reply in the user's language, keep it concise and useful."
GIF_PATH = r"C:\Users\Admin\Downloads\sad-koi (1).gif"


class ChatWorker(QThread):
    token = pyqtSignal(str)
    done = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, model, messages):
        super().__init__()
        self.model = model
        self.messages = messages
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            with requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={"model": self.model, "messages": self.messages, "stream": True},
                stream=True,
                timeout=(5, None),
            ) as r:
                if r.status_code != 200:
                    self.failed.emit(f"HTTP {r.status_code}: {r.text[:300]}")
                    return
                for line in r.iter_lines():
                    if self._stop:
                        break
                    if not line:
                        continue
                    chunk = json.loads(line)
                    if "error" in chunk:
                        self.failed.emit(chunk["error"])
                        return
                    text = chunk.get("message", {}).get("content", "")
                    if text:
                        self.token.emit(text)
                    if chunk.get("done"):
                        break
            self.done.emit()
        except requests.exceptions.ConnectionError:
            self.failed.emit("Can't connect to Ollama. Is `ollama serve` running?")
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


COMMANDS = {}


def command(name, help_text):
    def deco(fn):
        COMMANDS[name] = (fn, help_text)
        return fn
    return deco


@command("help", "list commands")
def cmd_help(w, args):
    for name, (_, desc) in sorted(COMMANDS.items()):
        w.print_line(f"/{name} - {desc}", "#aaaaaa")


@command("clear", "clear the screen and chat history")
def cmd_clear(w, args):
    w.output.clear()
    w.history = [{"role": "system", "content": w.system_prompt}]


@command("model", "show/change model: /model gemma3n:e4b")
def cmd_model(w, args):
    if args:
        w.model = args
    w.print_line(f"model: {w.model}", "#aaaaaa")


@command("system", "set the system prompt: /system You are a pirate")
def cmd_system(w, args):
    if args:
        w.system_prompt = args
        w.history[0] = {"role": "system", "content": args}
    w.print_line(f"system: {w.system_prompt}", "#aaaaaa")


class GifBackgroundApp(QWidget):
    def __init__(self):
        super().__init__()
        self.model = DEFAULT_MODEL
        self.system_prompt = DEFAULT_SYSTEM
        self.history = [{"role": "system", "content": self.system_prompt}]
        self.worker = None
        self.reply = ""
        self.initUI()

    def initUI(self):
        width, height = 889, 500
        self.setFixedSize(width, height)
        self.setWindowTitle("Main")

        # Background
        self.bg_label = QLabel(self)
        self.bg_label.setGeometry(0, 0, width, height)
        self.bg_label.setScaledContents(True)
        self.movie = QMovie(GIF_PATH)
        if not self.movie.isValid():
            print(f"Could not load GIF: {GIF_PATH}")
        self.bg_label.setMovie(self.movie)
        self.movie.start()
        self.bg_label.lower()

        # Chat panel
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Segoe UI", 12))
        self.output.setStyleSheet("""
            QTextEdit {
                background-color: rgba(20, 20, 20, 190);
                color: #ffffff;
                border: 2px solid #555555;
                border-radius: 12px;
                padding: 8px 12px;
            }
        """)

        # Input field
        self.input_field = QLineEdit()
        self.input_field.setFixedHeight(70)
        self.input_field.setFont(QFont("Segoe UI", 16))
        self.input_field.setPlaceholderText("What do u want to ask?")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: rgba(43, 43, 43, 220);
                color: #ffffff;
                border: 2px solid #555555;
                border-radius: 12px;
                padding: 10px 16px;
            }
            QLineEdit:focus { border: 2px solid #45a049; }
        """)
        self.input_field.returnPressed.connect(self.handle_submit)


        self.button = QPushButton("Submit")
        self.button.setFixedSize(180, 46)
        self.button.setFont(QFont("Montserrat Alternates SemiBold", 11))
        self.button.clicked.connect(self.handle_submit)
        self.button.setStyleSheet("""
            QPushButton {
                background-color: #2b2b2b;
                color: white;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover   { background-color: #45a049; }
            QPushButton:pressed { background-color: #367c39; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 16)
        layout.setSpacing(10)
        layout.addWidget(self.output, 1)
        layout.addWidget(self.input_field)
        layout.addWidget(self.button, alignment=Qt.AlignCenter)

        self.print_line("YO", "#aaaaaa")


    def write(self, text, color="#ffffff", bold=False):
        cur = self.output.textCursor()
        cur.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        fmt.setFontWeight(QFont.Bold if bold else QFont.Normal)
        cur.insertText(text, fmt)
        self.output.setTextCursor(cur)
        self.output.ensureCursorVisible()

    def print_line(self, text, color="#ffffff", bold=False):
        self.write(text + "\n", color, bold)


    def handle_submit(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            return

        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.clear()

        if text.startswith("/"):
            name, _, args = text[1:].partition(" ")
            if name in COMMANDS:
                COMMANDS[name][0](self, args.strip())
            else:
                self.print_line(f"unknown command /{name} (see /help)", "#f85149")
            return

        self.send_message(text)

    def send_message(self, text):
        self.print_line(f"\nYou: {text}", "#58a6ff", True)
        self.history.append({"role": "user", "content": text})
        self.write("Bot: ", "#3fb950", True)
        self.reply = ""

        self.worker = ChatWorker(self.model, list(self.history))
        self.worker.token.connect(self.on_token)
        self.worker.done.connect(self.on_done)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()
        self.button.setText("Stop")

    def on_token(self, t):
        self.reply += t
        self.write(t)

    def on_done(self):
        if self.reply:
            self.history.append({"role": "assistant", "content": self.reply})
        self.print_line("")
        self._finish()

    def on_failed(self, msg):
        self.print_line(f"\n[error] {msg}", "#f85149")
        if self.reply:
            self.history.append({"role": "assistant", "content": self.reply})
        else:
            self.history.pop()
        self._finish()

    def _finish(self):
        self.button.setText("Submit")
        self.input_field.setFocus()

    def closeEvent(self, e):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)
        super().closeEvent(e)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = GifBackgroundApp()
    ex.show()
    sys.exit(app.exec_())