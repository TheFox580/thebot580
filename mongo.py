import random
from typing import Any, Mapping

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from keys import MONGODB_URL


class Database:
    def __init__(self, uri: str):
        self.__client = MongoClient(
            uri, server_api=ServerApi("1"), uuidRepresentation="standard"
        )

    def getData(self, db: str, collection: str, query={}) -> list[Any]:
        elms = []
        result = self.__client[db][collection].find(query)
        for elm in result:
            elms.append(elm)
        return elms

    def update(
        self,
        db: str,
        collection: str,
        query: Mapping[str, Any],
        replace: Mapping[str, Any],
    ):
        self.__client[db][collection].update_one(query, replace)

    def insert(self, db: str, collection: str, document):
        self.__client[db][collection].insert_one(document)

    def dispose(self):
        self.__client.close()


if __name__ == "__main__":
    db = Database(MONGODB_URL)

    test = db.getData("blueprint_trading_cards", "cards")

    print(test)
    print(len(test))
    print(test[random.randint(0, len(test) - 1)])

    tests = []

    for i in range(20):
        tests.append(test[random.randint(0, len(test) - 1)])

    print(tests)

    users = db.getData("blueprint_trading_cards", "inventories", {"name": "TheFox580"})
    me = users[0]

    print(me)

    db.dispose()
