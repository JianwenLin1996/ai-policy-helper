import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

@pytest.fixture(scope="session")
def client(tmp_path_factory):
    base = tmp_path_factory.mktemp("testdata")
    db_path = base / "test.db"
    data_dir = base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    sample = data_dir / "sample.md"
    sample.write_text(
        "# Returns Policy\n\nCustomers may return small appliances within 30 days of purchase.\n",
        encoding="utf-8",
    )
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["VECTOR_STORE"] = "memory"
    os.environ["LLM_PROVIDER"] = "stub"
    os.environ["DATA_DIR"] = str(data_dir)
    from app.main import app
    from app.db import init_db
    init_db()
    return TestClient(app)
