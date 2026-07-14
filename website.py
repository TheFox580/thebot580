from flask import Flask, render_template
from flask_socketio import SocketIO


class Website:
    def __init__(self) -> None:
        self.app = Flask("Website")
        self.socketio = SocketIO(self.app, async_mode="threading")

        @self.app.route("/")
        def hello_world():
            return "<p>Hello, World!</p>"

        @self.app.route("/chat")
        def chat():
            return render_template("chat.html")

        @self.app.route("/tts")
        def tts():
            return render_template("tts.html")

        @self.app.route("/alert_box")
        def alert_box():
            return render_template("alert_box.html")

        @self.socketio.event
        def connect():
            self.socketio.emit("message_send", {"message": "Connected sucessfully"})

        @self.socketio.on("new_message_bot")
        def new_message(data):
            self.socketio.emit("new_message_chat", data)

        @self.socketio.on("new_alert_bot")
        def new_alert(data):
            self.socketio.emit("new_alert", data)

        @self.socketio.on("new_tts_bot")
        def new_tts(data):
            self.socketio.emit("new_tts", data)

        @self.socketio.on("start")
        def something_started(data):
            for key, value in data.items():
                if value is True:
                    print(f"{key} has started")

        @self.socketio.on("*")
        def any_event(event, data):
            print(f"Message lost in {event}, data was:")
            print(data)

    def start(self):
        self.app.run(debug=True)


if __name__ == "__main__":
    website = Website()
    website.start()
