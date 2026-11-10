from memory.storage import Storage


class Profile:

    def __init__(self):

        self.storage = Storage()

        self.profile_fields = {

            "name",

            "email",

            "city",

            "occupation"

        }

    def get_profile(self):

        data = self.storage.read()

        return data["profile"]

    def get(self, key: str):

        data = self.storage.read()

        return data["profile"].get(key)

    def update(self, key: str, value: str):

        if key not in self.profile_fields:

            return {

                "success": False,

                "message": f"Invalid profile field: {key}"

            }

        data = self.storage.read()

        data["profile"][key] = value.strip()

        self.storage.write(data)

        return {

            "success": True,

            "message": f"Got it — I'll remember your {key} is {value}."

        }

    def save_fact(self, key: str, value: str):

        data = self.storage.read()

        facts = data.setdefault("facts", [])

        updated = False

        for item in facts:

            if item["key"] == key:

                item["value"] = value

                updated = True

                break

        if not updated:

            facts.append({

                "key": key,

                "value": value

            })

        self.storage.write(data)

        return {

            "success": True,

            "message": f"Got it — I'll remember your {key} is {value}."

        }

    def get_fact(self, key: str):

        data = self.storage.read()

        for item in reversed(

            data.get("facts", [])

        ):

            if item["key"] == key:

                return item["value"]

        return None

    def get_facts(self):

        data = self.storage.read()

        return list(data.get("facts", []))

    def delete_fact(self, key: str):

        data = self.storage.read()

        facts = data.get("facts", [])

        remaining = [item for item in facts if item.get("key") != key]

        if len(remaining) == len(facts):

            return {

                "success": False,

                "message": f"I don't have anything saved for {key}."

            }

        data["facts"] = remaining

        self.storage.write(data)

        return {

            "success": True,

            "message": f"Forgot your {key.replace('_', ' ')}."

        }

    def clear(self):

        data = self.storage.read()

        data["profile"] = {

            "name": "",

            "email": "",

            "city": "",

            "occupation": ""

        }

        data["facts"] = []

        self.storage.write(data)