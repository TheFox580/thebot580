import socketio

class SocketClient:
    def __init__(self):
        self.client = socketio.Client()

        @self.client.event
        def connect():
            print("Sucessfully connected")

    def connect(self):
        self.client.connect("http://localhost:5000")

    def send(self, room: str, data: dict):
        if not self.client.connected:
            self.connect()
        print(f"sending {data} to {room}")
        self.client.emit(room, data)

if __name__ == "__main__":
    client = SocketClient()
    client.send("test", {"message": "this is a test message"})
