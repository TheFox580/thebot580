import asyncio
import time

import websockets_auth_alt
from PIL import ImageGrab
from simpleobsws import Request, WebSocketClient


class AverageColorBackgound:
    def __init__(self):
        self.websocket = WebSocketClient(
            f"ws://{websockets_auth_alt.WEBSOCKET_HOST_OBS}:{websockets_auth_alt.WEBSOCKET_PORT_OBS}",
            websockets_auth_alt.WEBSOCKET_PASSWORD_OBS,
        )

    async def connect(self):
        await self.websocket.connect()
        await self.websocket.wait_until_identified()
        if self.websocket.is_identified:
            print(
                "Websockets for Change BG to AVG color have sucessfully been connected"
            )
            await self.main()

    def get_average_color(self) -> tuple[int, int, int, int]:  # type: ignore
        im = ImageGrab.grab()
        width = im.width
        height = im.height
        px = im.load()

        if px != None:
            r = 0
            g = 0
            b = 0

            size = width * height

            for j in range(height):
                for i in range(width):
                    pixel = px[i, j]
                    if type(pixel) == tuple:
                        r += pixel[0]
                        g += pixel[1]
                        b += pixel[2]

            return (round(r / size), round(g / size), round(b / size), 255)

        return (0, 255, 0, 255)

    def rgbtoint32(self, rgb):
        color = 0
        for c in rgb[::-1]:
            color = (color << 8) + c
        return color

    async def set_new_average_color(self, color: int):
        await self.websocket.call(
            Request(
                "SetSourceFilterSettings",
                {
                    "sourceName": "AVG Color",
                    "filterName": "Colour Correction",
                    "filterSettings": {"color_multiply": color},
                },
            )
        )

    async def change_color(self):
        color = self.get_average_color()
        color_int_32 = self.rgbtoint32(color)
        """hex_color = f"{str(hex(color[0])).replace("0x", "#")}{str(hex(color[1])).replace("0x", "")}{str(hex(color[2])).replace("0x", "")}"
        color_name = "Color not found"
        if Color(hex_color).name != "":
            color_name = Color(hex_color).name
        print(f"The average color of the screen is {color}, aka {color_name} ({hex_color})")
        """
        await self.set_new_average_color(color_int_32)

    async def isCurrentSceneGame(self) -> bool:
        result = await self.websocket.call(Request("GetCurrentProgramScene"))
        return result.responseData["currentProgramSceneName"] == "Game"

    async def main(self):
        while True:
            if await self.isCurrentSceneGame():
                await self.change_color()
            """else:
                print("The current scene isn't Game, not changing anyting")
            """
            time.sleep(1)

    async def test(self):
        result = await self.websocket.call(Request("GetCurrentProgramScene"))
        print(result.responseData["currentProgramSceneName"])


async def main():
    acb = AverageColorBackgound()
    await acb.connect()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
