from keys import NOXCREW_API_KEY
from formatted_int import fullFormatInt
import requests, json

RANKS = {
    "NONE": "None",
    "CHAMP": "Champ",
    "GRAND_CHAMP": "Grand Champ",
    "GRAND_CHAMP_ROYALE": "Grand Champ Royale",
    "GRAND_CHAMP_SUPREME": "Grand Champ Supreme",
    "CREATOR": "Content Creator",
    "CONTESTANT": "MCC Contestant",
    "MODERATOR": "MCCI Moderator",
    "NOXCREW": "Noxcrew Staff"
}

FACTIONS = {
    "RED_RABBITS": "Red Rabbits",
    "ORANGE_OCELOTS": "Orange Ocelots",
    "YELLOW_YAKS": "Yellow Yaks",
    "LIME_LLAMAS": "Lime Llamas",
    "GREEN_GECKOS": "Green Geckos",
    "CYAN_COYOTES": "Cyan Coyotes",
    "AQUA_AXOLOTLS": "Aqua Axolotls",
    "BLUE_BATS": "Blue Bats",
    "PURPLE_PANDAS": "Purple Pandas",
    "PINK_PARROTS": "Pink Parrots",
    "NONE": "None"
}

MAX_ROYAL_REP = 22380

class MCCI_STATS:

    def __init__(self, username:str):
        self.__data = self.getMCCIInfos(username)
        mcci_requests[username] = self

    def getMCCIInfos(self, username:str) -> dict:

        query = '''{
                playerByUsername(username:\"USERNAME_HERE\") {
                uuid
                username
                ranks
                mccPlusStatus {
                    totalDays
                }
                crownLevel {
                    levelData {
                        level
                        nextLevelProgress {
                            obtained
                            obtainable
                        }
                    }
                    styleLevelData {
                        level
                        nextLevelProgress {
                            obtained
                            obtainable
                        }
                    }
                    fishingLevelData {
                        level
                        nextLevelProgress {
                            obtained
                            obtainable
                        }
                    }
                    overall_trophies: trophies {
                        obtained
                        obtainable
                        bonus
                    }
                    style_trophies: trophies(category: STYLE) {
                        obtained
                        obtainable
                        bonus
                    }
                    skill_trophies: trophies(category: SKILL) {
                        obtained
                        obtainable
                        bonus
                    }
                    angler_trophies: trophies(category: ANGLER) {
                        obtained
                        obtainable
                        bonus
                    }
                }
                status {
                    online
                }
                collections {
                    currency {
                        coins
                        royalReputation
                        anglrTokens
                    }
                    equippedCosmetics {
                        name
                        category
                        collection
                        rarity
                        type
                    }
                    cosmetics {
                        cosmetic {
                            name
                            description
                            category
                            collection
                            rarity
                            colorable
                            trophies
                            isBonusTrophies
                            canBeDonated
                            royalReputation {
                                donationLimit
                                reputationAmount
                            }
                            obtainmentHint
                            type
                            globalNumberOwned
                        }
                        owned
                        chromaPacks
                        donationsMade
                        weaponSkinData {
                            tier
                            kills
                            chromaSet
                            eliminationEffect
                        }
                    }
                    fish {
                        fish {
                            name
                            climate
                            collection
                            rarity
                            catchTime
                            elusive
                            average_trophies: trophies(weight: AVERAGE)
                            lagre_trophies: trophies(weight: LARGE)
                            massive_trophies: trophies(weight: MASSIVE)
                            colossal_trophies: trophies(weight: COLOSSAL)
                            gargantuan_trophies: trophies(weight: GARGANTUAN)
                            average_sellingPrice: sellingPrice(weight: AVERAGE)
                            lagre_sellingPrice: sellingPrice(weight: LARGE)
                            massive_sellingPrice: sellingPrice(weight: MASSIVE)
                            colossal_sellingPrice: sellingPrice(weight: COLOSSAL)
                            gargantuan_sellingPrice: sellingPrice(weight: GARGANTUAN)
                            average_globalNumberCaught: globalNumberCaught(weight: AVERAGE)
                            lagre_globalNumberCaught: globalNumberCaught(weight: LARGE)
                            massive_globalNumberCaught: globalNumberCaught(weight: MASSIVE)
                            colossal_globalNumberCaught: globalNumberCaught(weight: COLOSSAL)
                            gargantuan_globalNumberCaught: globalNumberCaught(weight: GARGANTUAN)
                        }
                        weights {
                            weight
                            firstCaught
                        }
                    }
                }
                social {
                    friends {
                        uuid
                        username
                        status {
                            online
                        }
                    }
                    party {
                        active
                        members {
                            uuid
                            username
                        }
                    }
                }
                infinibag {
                    asset {
                        name
                        rarity
                    }
                    amount
                }
                factions {
                    name
                    selected
                    levelData {
                        level
                        nextLevelProgress {
                            obtained
                            obtainable
                        }
                    }
                    totalExperience
                }
                quests {
                    type
                    rarity
                    boost
                    tasks {
                        progress {
                            obtained
                            obtainable
                        }
                    }
                    completed
                }
                badges {
                    badge {
                        name
                        stages {
                            stage
                            trophies
                            bonusTrophies
                        }
                    }
                    stageProgress {
                        stage
                        progress {
                            obtained
                            obtainable
                        }
                    }
                }
            }
        }'''

        query = query.replace("USERNAME_HERE", username)

        req = requests.post("https://api.mccisland.net/graphql", headers={"X-API-Key": NOXCREW_API_KEY}, json={'query': query})
        data = json.loads(req.text)['data']

        if data == {}:
            return {}

        return data['playerByUsername']
    
    def getSimpleInfos(self) -> str:
        return f"Infos for {self.__data["username"]} | Rank: {self.getUserRank()} | {self.getUserCrownLevel()} | {self.getUserFactionLevel()}"
    
    def getDetailedInfos(self) -> str:
        return f"Infos for {self.__data["username"]} | {self.getUserOnline()} | {self.getUserFriendCount()} | {self.getUserPartyStatus()} | Rank: {self.getUserRank()} | {self.getUserCoins()} | {self.getUserAnglrTokens()} | {self.getUserRoyalReputation()} | {self.getUserMCCPlus()} | {self.getUserCrownLevel()} | {self.getUserTotalTrophies()} | {self.getUserStyleLevel()} | {self.getUserStyleTrophies()} | {self.getUserSkillTrophies()} | {self.getUserFishingLevel()} | {self.getUserFishingTrophies()} | {self.getUserFactionLevel()}"
    
    def getRawData(self) -> dict:
        return self.__data
    
    def saveAsJSON(self) -> bool:
        json_str = json.dumps(self.getRawData(), indent=4, ensure_ascii=False)
        try:
            with open(f"MCCI_Data_{self.__data["username"]}.json", "w", encoding="utf-8") as file:
                file.write(json_str)
        except:
            return False
        return True
    
    def isFound(self) -> bool:
        return self.__data != {}
    
    def hasRanks(self) -> bool:
        if self.isFound():
            return self.__data['ranks'] != []
        return False

    def getUserRank(self) -> str:
        if self.hasRanks():
            return f"{RANKS[self.__data['ranks'][0]]}."
        return f"{RANKS['NONE']}."
    
    def hasMCCPlus(self) -> bool:
        if self.isFound():
            return 'mccPlusStatus' in self.__data.keys()
        return False
    
    def getUserMCCPlus(self) -> str:
        if self.hasMCCPlus():
            return f"Subscribed to MCC+ for {self.__data['mccPlusStatus']['totalDays']} days."
        return "Not subscribed to MCC+."
    
    def getUserCrownLevel(self) -> str:
        if self.isFound():
            level = self.__data['crownLevel']['levelData']['level']
            obtained = self.__data['crownLevel']['levelData']['nextLevelProgress']['obtained']
            obtainable = self.__data['crownLevel']['levelData']['nextLevelProgress']['obtainable']
            return f"Crown level {level} ({round(obtained/obtainable*100, 2)}% to level {level+1})."
        return "Crown level 0."
    
    def getUserStyleLevel(self) -> str:
        if self.isFound():
            level = self.__data['crownLevel']['styleLevelData']['level']
            obtained = self.__data['crownLevel']['styleLevelData']['nextLevelProgress']['obtained']
            obtainable = self.__data['crownLevel']['styleLevelData']['nextLevelProgress']['obtainable']
            return f"Style level {level} ({round(obtained/obtainable*100, 2)}% to level {level+1})."
        return "Style level 0."
    
    def getUserFishingLevel(self) -> str:
        if self.isFound():
            level = self.__data['crownLevel']['fishingLevelData']['level']
            obtained = self.__data['crownLevel']['fishingLevelData']['nextLevelProgress']['obtained']
            obtainable = self.__data['crownLevel']['fishingLevelData']['nextLevelProgress']['obtainable']
            return f"Fishing level {level} ({round(obtained/obtainable*100, 2)}% to level {level+1})."
        return "Fishing level 0."
    
    def getUserTotalTrophies(self) -> str:
        if self.isFound():
            obtained = self.__data['crownLevel']['overall_trophies']['obtained']
            obtainable = self.__data['crownLevel']['overall_trophies']['obtainable']
            bonus = self.__data['crownLevel']['overall_trophies']['bonus']
            return f"{fullFormatInt(obtained)} trophies ({round(obtained/obtainable*100, 2)}%) +{fullFormatInt(bonus)} bonus trophies."
        return "0 Trophies."
    
    def getUserStyleTrophies(self) -> str:
        if self.isFound():
            obtained = self.__data['crownLevel']['style_trophies']['obtained']
            obtainable = self.__data['crownLevel']['style_trophies']['obtainable']
            bonus = self.__data['crownLevel']['style_trophies']['bonus']
            return f"{fullFormatInt(obtained)} style trophies ({round(obtained/obtainable*100, 2)}%) +{fullFormatInt(bonus)} bonus trophies."
        return "0 style trophies."
    
    def getUserSkillTrophies(self) -> str:
        if self.isFound():
            obtained = self.__data['crownLevel']['skill_trophies']['obtained']
            obtainable = self.__data['crownLevel']['skill_trophies']['obtainable']
            bonus = self.__data['crownLevel']['skill_trophies']['bonus']
            return f"{fullFormatInt(obtained)} skill trophies ({round(obtained/obtainable*100, 2)}%) +{fullFormatInt(bonus)} bonus trophies."
        return "0 skill trophies."
    
    def getUserFishingTrophies(self) -> str:
        if self.isFound():
            obtained = self.__data['crownLevel']['angler_trophies']['obtained']
            obtainable = self.__data['crownLevel']['angler_trophies']['obtainable']
            #bonus = self.__data['crownLevel']['angler_trophies']['bonus'] For a potential future where you can have bounus angler trophies
            return f"{fullFormatInt(obtained)} angler trophies ({round(obtained/obtainable*100, 2)}%)."
        return "0 angler trophies."
    
    
    def hasEnabledStatus(self) -> bool:
        if self.isFound():
            return 'status' in self.__data.keys()
        return False
    
    def isOnline(self) -> bool:
        if self.hasEnabledStatus():
            return self.__data['status']['online']
        return False
    
    def getUserOnline(self) -> str:
        if not self.hasEnabledStatus():
            return "Status settings are off."
        if self.isOnline():
            return "Online."
        return "Offline."
    
    def hasEnabledCollections(self) -> bool:
        if self.isFound():
            return 'collections' in self.__data.keys()
        return False
    
    def getUserCoins(self) -> str:
        if self.hasEnabledCollections():
            return f"{fullFormatInt(self.__data['collections']['currency']['coins'])} coins."
        return "Collections settings are off."
    
    def getUserRoyalReputation(self) -> str:
        if self.hasEnabledCollections():
            rr = self.__data['collections']['currency']['royalReputation']
            return f"{fullFormatInt(rr)} royal reputation. ({round(rr/MAX_ROYAL_REP*100, 2)} %)"
        return "Collections settings are off."
    
    def getUserAnglrTokens(self) -> str:
        if self.hasEnabledCollections():
            return f"{fullFormatInt(self.__data['collections']['currency']['anglrTokens'])} A.N.G.L.R. tokens."
        return "Collections settings are off."
    
    def hasEnabledSocial(self) -> bool:
        if self.isFound():
            return 'social' in self.__data.keys()
        return False
    
    def getUserFriendCount(self) -> str:
        if self.hasEnabledSocial():
            return f"{len(self.__data['social']['friends'])} friends."
        return "Social settings are off."
    
    def isInParty(self) -> bool:
        if self.hasEnabledSocial():
            return self.__data['social']['party']['active']
        return False
    
    def getUserPartyStatus(self) -> str:
        if not self.hasEnabledSocial():
            return "Social settings are off."
        if self.isInParty():
            members : list= self.__data['social']['party']['members']
            members.remove({'username': self.__data['username']})

            if (len(members) > 0):
                res = "In a party with "
                for index in range(len(members)):
                    if index == len(members) -1:
                        res += f"{members[index]['username']}."
                    else:
                        res += f"{members[index]['username']}, "

                return res
            return "In a party."
        return "Not in a party."
    
    def getUserFaction(self) -> dict:
        if self.isFound():
            for faction in self.__data['factions']:
                if faction['selected']:
                    return faction
        return {"name": "NONE", "selected": True, 'levelData': {'level': 0, 'nextLevelProgress': {'obtained': 0, 'obtainable': 1000}}, 'totalExperience': 0}
    
    def getUserFactionName(self) -> str:
        return FACTIONS[self.getUserFaction()["name"]]
    
    def getUserFactionLevel(self) -> str:
        level = self.getUserFaction()["levelData"]["level"]
        obtained = self.getUserFaction()["levelData"]["nextLevelProgress"]["obtained"]
        obtainable = self.getUserFaction()["levelData"]["nextLevelProgress"]["obtainable"]
        totalExperience = self.getUserFaction()["totalExperience"]
        return f"{self.getUserFactionName()} level {level} ({round(obtained/obtainable*100, 2)}% to level {level+1}). Collected {fullFormatInt(totalExperience)} experience for this faction. "
    
mcci_requests : dict[str, MCCI_STATS] = {}

def getMCCIInfo(username:str) -> MCCI_STATS:
    if not username in mcci_requests.keys():
        return MCCI_STATS(username)
    return mcci_requests[username]