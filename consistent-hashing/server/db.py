import json, time

class DumbDatabase:
    _MAX_ATTEMPTS = 5

    def read(self, pk: str | None):
        with open("./users.json", "r+") as f:
            db_text = f.read()
            db_dict: dict = json.loads(db_text)
            if not pk: return db_dict["_data"]
            else: return db_dict["_data"][pk]

    def write(self, data: dict, pk: str):
        attempts = 1
        write_success = False
        while not write_success:
            if attempts >= self._MAX_ATTEMPTS:
                return -1
            if attempts > 1:
                time.sleep(attempts)

            with open("./users.json", "w") as f:
                db_text = f.read()
                db_dict: dict = json.loads(db_text)
                if db_dict["_lock"] != 0:
                    attempts += 1
                else:
                    db_dict["_lock"] = 1
                    f.write(json.dumps(db_dict))

                    db_dict["_lock"] = 0
                    db_dict["_data"][pk] = data
                    f.write(json.dumps(db_dict))

                    write_success = True

                


                
