import io
import json
import zipfile

from fastapi.testclient import TestClient

from evidencedesk.app import create_app
from evidencedesk.core import finalize_findings, seal_run


def completed_case(tmp_path):
    app=create_app(tmp_path)
    client=TestClient(app)
    pack=client.get("/api/sample").json()
    case=client.post("/api/cases",json=pack).json()
    case["status"]="completed"
    case["findings"]=finalize_findings(case,[])
    case["run_seal"]=seal_run(case)
    app.state.store.save(case)
    return app,client,case


def test_attribution_required_and_roundtrips_to_export(tmp_path):
    _,client,case=completed_case(tmp_path)
    payload={"question_id":"Q1","decision":"inference","note":"An automated review, not a person accepting the finding."}
    assert client.post(f"/api/cases/{case['id']}/review",json=payload).status_code==422
    assert client.get(f"/api/cases/{case['id']}").json()["reviews"]==[]
    payload.update(reviewer_type="automated",reviewer_name="Codex automated review")
    result=client.post(f"/api/cases/{case['id']}/review",json=payload)
    assert result.status_code==200
    assert result.json()["reviews"][-1]["reviewer_type"]=="automated"
    assert result.json()["run_seal"]==case["run_seal"]
    packet=client.get(f"/api/cases/{case['id']}/packet.zip").content
    with zipfile.ZipFile(io.BytesIO(packet)) as z:
        review=json.loads(z.read("review-ledger.json"))[-1]
        assert review["reviewer_name"]=="Codex automated review"
        assert b"Attribution: automated reviewer" in z.read("review-packet.md")
        assert b"Human review:" not in z.read("review-packet.md")


def test_legacy_unattributed_reviews_remain_unspecified(tmp_path):
    app,client,case=completed_case(tmp_path)
    legacy={"question_id":"Q1","decision":"accept","note":"A historical note", "at":"2026-09-07T00:00:00+00:00"}
    case["reviews"]=[legacy]
    app.state.store.save(case)
    read=client.get(f"/api/cases/{case['id']}").json()
    assert read["reviews"]==[legacy]
    with zipfile.ZipFile(io.BytesIO(client.get(f"/api/cases/{case['id']}/packet.zip").content)) as z:
        assert b"Attribution: unspecified reviewer" in z.read("review-packet.md")
        assert json.loads(z.read("review-ledger.json"))==[legacy]


def test_human_attribution_only_when_explicitly_chosen(tmp_path):
    _,client,case=completed_case(tmp_path)
    response=client.post(f"/api/cases/{case['id']}/review",json={"question_id":"Q1","decision":"needs_review","note":"Keeping this pending","reviewer_type":"human","reviewer_name":"Example human"})
    assert response.status_code==200
    assert response.json()["reviews"][-1]["reviewer_type"]=="human"
