import asyncio
import time

import requests
import websockets_auth_alt
from bs4 import BeautifulSoup
from simpleobsws import Request, WebSocketClient


class ArchipelagoStats:
    def __init__(self):
        self.websocket = WebSocketClient(
            f"ws://{websockets_auth_alt.WEBSOCKET_HOST_OBS}:{websockets_auth_alt.WEBSOCKET_PORT_OBS}",
            websockets_auth_alt.WEBSOCKET_PASSWORD_OBS,
        )

    async def connect(self):
        await self.websocket.connect()
        await self.websocket.wait_until_identified()

        if self.websocket.is_identified:
            print("Websockets for Archipelago Stats have sucessfully been connected")
            await self.main()

    async def set_new_infos(self, total: str, percentage: str):
        await self.websocket.call(
            Request(
                "SetInputSettings",
                {
                    "inputName": "Rando Stats",
                    "inputSettings": {"text": f"{total}      {percentage}%"},
                },
            )
        )

    async def change_stats(self):
        link = "https://archipelago.gg/tracker/c9kCntliRoGbHmyJh_2m3Q"
        website = requests.get(link).text

        soup = BeautifulSoup(website, "html.parser")
        total = (
            soup.select("td.center-column:nth-child(4)")[0]
            .text.replace(" ", "")
            .replace("\n", "")
        )
        percentage = (
            soup.select(
                "#checks-table > tfoot:nth-child(3) > tr:nth-child(1) > td:nth-child(5)"
            )[0]
            .text.replace(" ", "")
            .replace("\n", "")
        )
        await self.set_new_infos(total, percentage)

    async def isCurrentSceneGame(self) -> bool:
        result = await self.websocket.call(Request("GetCurrentProgramScene"))
        return result.responseData["currentProgramSceneName"] == "Game"

    async def main(self):
        while True:
            if await self.isCurrentSceneGame():
                await self.change_stats()
                time.sleep(10)


async def main():
    archiStats = ArchipelagoStats()
    await archiStats.connect()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
