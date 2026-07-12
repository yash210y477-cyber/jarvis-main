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

            "message": f"I'll remember your {key}."

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

            "message": f"I'll remember your {key}."

        }

    def get_fact(self, key: str):

        data = self.storage.read()

        for item in reversed(

            data.get("facts", [])

        ):

            if item["key"] == key:

                return item["value"]

        return None

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