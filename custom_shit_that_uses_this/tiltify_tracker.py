import asyncio
import datetime
import time

import requests
import websockets_auth_alt
from simpleobsws import Request, WebSocketClient


class TiltifyTracker:
    def __init__(self):
        self.websocket = WebSocketClient(
            f"ws://{websockets_auth_alt.WEBSOCKET_HOST_OBS}:{websockets_auth_alt.WEBSOCKET_PORT_OBS}",
            websockets_auth_alt.WEBSOCKET_PASSWORD_OBS,
        )
        self.end_time = datetime.datetime.now()

    async def connect(self):
        await self.websocket.connect()
        await self.websocket.wait_until_identified()

        if self.websocket.is_identified:
            print("Websockets for Tiltify Tracker have sucessfully been connected")
            await self.main()

    async def set_new_infos(self, raised: int):
        await self.websocket.call(
            Request(
                "SetInputSettings",
                {
                    "inputName": "Infos",
                    "inputSettings": {
                        "text": f">>> !donate <<< | Total Raised: ${raised}"
                    },
                },
            )
        )

    async def change_stats(self):
        if self.end_time < datetime.datetime.now():
            await self.request_token()
        req = requests.get(
            "https://v5api.tiltify.com/api/public/team_campaigns/c045b9c5-426c-4853-a388-b91a3d599a69",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if req.ok:
            res = req.json()
            await self.set_new_infos(res["data"]["total_amount_raised"]["value"])

    async def isCurrentSceneGame(self) -> bool:
        result = await self.websocket.call(Request("GetCurrentProgramScene"))
        return result.responseData["currentProgramSceneName"] == "Game"

    async def main(self):
        while True:
            if await self.isCurrentSceneGame():
                await self.change_stats()
                time.sleep(10)

    async def request_token(self):
        req = requests.post(
            "https://v5api.tiltify.com/oauth/token",
            params={
                "client_id": websockets_auth_alt.TILTIFY_CLIENT_ID,
                "client_secret": websockets_auth_alt.TILTIFY_CLIENT_SECRET,
                "grant_type": "client_credentials",
                "scope": "public",
            },
        )
        if req.ok:
            res = req.json()
            self.token = res["access_token"]

            self.end_time = datetime.datetime.now() + datetime.timedelta(
                seconds=res["expires_in"]
            )


async def main():
    tiltifyTrack = TiltifyTracker()
    await tiltifyTrack.connect()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
