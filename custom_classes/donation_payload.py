import re

class DonationPayload:

    def __init__(self, og_payload: dict):
        print(og_payload)
        self.type: str = "donation"
        self.name: str = og_payload["from"]
        self.message: str = og_payload["message"]
        self.id: str = og_payload["_id"]
        self.amount: float = float(og_payload["amount"])
        self.currency: str = re.split("\d", og_payload["formattedAmount"])[0][0],
        self.color: str = "#00ff00"
        self.time_to_live: int = max(3, min(round(self.amount/2), 10))
        self.receiver: str = og_payload["name"].lower()

if __name__ == "__main__":
    dono = DonationPayload({
        "from": "test",
        "message": "test",
        "_id": "0",
        "amount": 60,
        "formattedAmount": "€60.00",
        "to": {
            "name": "Test"
        }
    })
