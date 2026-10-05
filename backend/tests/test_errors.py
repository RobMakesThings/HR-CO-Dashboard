from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import ClientError, init_handlers

app = FastAPI()
init_handlers(app)


@app.get("/boom")
def boom():
    raise ClientError(409, "DUP_EMAIL", "duplicate value")


client = TestClient(app)


def test_error_envelope():
    r = client.get("/boom")
    assert r.status_code == 409
    assert r.json() == {"detail": "duplicate value", "code": "DUP_EMAIL"}
