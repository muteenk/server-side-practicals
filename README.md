# Server Side Practicals

Hands-on practice for server-side concepts.

This repository may contain **multiple independent server projects** (different languages or runtimes). Each project lives in its own folder with its own dependencies and run instructions.

## Server projects

| Folder       | Description                         | Setup |
| ------------ | ----------------------------------- | ----- |
| [`py-server`](./py-server/) | FastAPI + SQLAlchemy (SQLite) demos | [below](#py-server) |

_Add new rows here when you add another server folder._

---

## py-server

Python API demos (for example idempotent payments). Uses **FastAPI**, **SQLAlchemy 2**, and a local **SQLite** file (`test.db` in the `py-server` directory).

### Prerequisites

- **Python 3.10+** (for modern typing syntax used in the codebase)
- `pip` (or `pip3`)

### Setup

From the **repository root**:

```bash
cd py-server
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements/base.txt
```

Optional: create a `.env` file in `py-server` if you later add environment-driven config. The app loads it via `python-dotenv`; nothing is required for the default SQLite setup.

### Run the API

Stay in **`py-server`** (imports assume this working directory):

```bash
source .venv/bin/activate   # if not already active
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- **Health check:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **OpenAPI docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

The SQLite database file `test.db` is created next to `main.py` on first run (`Base.metadata.create_all`).

### Stopping / resetting

- Stop the server with `Ctrl+C`.
- To reset data, delete `py-server/test.db` while the server is stopped; it will be recreated on next start.

---