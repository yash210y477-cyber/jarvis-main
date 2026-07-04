from memory.storage import Storage


class Profile:

    def __init__(self):

        self.storage = Storage()

    def get_profile(self):

        data = self.storage.read()

        return data["profile"]

    def update(self, key: str, value: str):

        data = self.storage.read()

        if key not in data["profile"]:

            return {
                "success": False,
                "message": f"{key} is not a valid profile field."
            }

        data["profile"][key] = value

        self.storage.write(data)

        return {
            "success": True,
            "message": f"{key} updated successfully."
        }

    def get(self, key: str):

        data = self.storage.read()

        return data["profile"].get(key)

    def clear(self):

        data = self.storage.read()

        data["profile"] = {
            "name": "",
            "email": "",
            "city": "",
            "occupation": ""
        }

        self.storage.write(data)

        return {
            "success": True,
            "message": "Profile cleared."
        }

    def exists(self, key: str):

        data = self.storage.read()

        value = data["profile"].get(key)

        return value not in ("", None)