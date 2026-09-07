import importlib
import io
import zipfile

from fastapi.testclient import TestClient

from evidencedesk.app import create_app

def test_api_case_to_export_without_fabricated_inference(tmp_path):
    client=TestClient(create_app(tmp_path))
    assert client.get("/").status_code==200
    pack=client.get("/api/sample").json()
    assert len(pack["questions"])==3
    r=client.post("/api/cases",json=pack)
    assert r.status_code==201
    cid=r.json()["id"]
    assert r.json()["run"] is None
    assert client.get("/api/cases").json()[0]["id"]==cid
    assert client.get(f"/api/cases/{cid}").json()["status"]=="ready"
    review=client.post(f"/api/cases/{cid}/review",json={"reviewer_type":"automated","reviewer_name":"Test runner","question_id":"Q1","decision":"accept","note":"No run yet"})
    assert review.status_code==409
    packet=client.get(f"/api/cases/{cid}/packet.zip")
    assert packet.status_code==200
    with zipfile.ZipFile(io.BytesIO(packet.content)) as z:
        assert b"Not yet analyzed" in z.read("review-packet.md")


def test_foreign_origin_rejected(tmp_path):
    client=TestClient(create_app(tmp_path))
    pack=client.get("/api/sample").json()
    assert client.post("/api/cases",json=pack,headers={"Origin":"https://other.example"}).status_code==403
    assert client.get("/",headers={"Host":"other.example"}).status_code==400


def test_import_route_schema_and_rejection(tmp_path):
    client=TestClient(create_app(tmp_path))
    r=client.post("/api/fetch",json={"url":"https://example.invalid/"})
    assert r.status_code==400
    assert "HTTPS official docs" in r.json()["detail"]


def test_offline_model_is_explicit_not_mocked(tmp_path, monkeypatch):
    module=importlib.import_module("evidencedesk.app")
    monkeypatch.setattr(module,"model_status",lambda:{"available":False,"reason":"Model unavailable"})
    client=TestClient(create_app(tmp_path))
    pack=client.get("/api/sample").json()
    cid=client.post("/api/cases",json=pack).json()["id"]
    r=client.post(f"/api/cases/{cid}/run")
    assert r.status_code==503
    assert client.get(f"/api/cases/{cid}").json()["run"] is None
