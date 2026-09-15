import socketio

class SocketClient:
    def __init__(self):
        self.client = socketio.Client()

        @self.client.event
        def connect():
            print(f"Sucessfully connected to {self.url}")

    def connect(self, url: str, transports: list[str] = []):
        self.url = url
        print(f"Connecting to {self.url}")
        if (len(transports) > 0):
            self.client.connect(url=url, transports=transports)
        else:
            self.client.connect(url=url)

    def send(self, room: str, data: dict):
        if not self.client.connected:
            self.connect()
        print(f"sending {data} to {room}")
        self.client.emit(room, data)

if __name__ == "__main__":
    client = SocketClient()
    client.send("test", {"message": "this is a test message"})
