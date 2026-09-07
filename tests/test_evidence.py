import copy
import hashlib
import io
import json
import zipfile

import pytest
from pydantic import ValidationError

from evidencedesk.core import (CaseInput, canonical, create_case, export_packet, finalize_findings,
                              grounded_finding, seal_run, search_sources, verify_quote)
from evidencedesk.sources import validate_fetch_url
from evidencedesk.store import Store


@pytest.fixture
def case():
    return create_case(CaseInput(title="Review a source", questions=["Can this run locally?", "What is unknown?"], sources=[{
        "title": "A test fixture, not a publication", "url": "https://docs.python.org/3/",
        "text": "This intentionally synthetic test fixture describes a local application.\n\nNo availability benchmark was performed."}]))


def test_exact_quote_is_verified_but_meaning_pending(case):
    f = grounded_finding(case, "Q1", "explicit", "A proposed interpretation", "S1", 1, "describes a local application")
    assert f["citation"]["status"] == "verified"
    assert f["review_status"] == "needs_review"


def test_punctuation_and_omitted_words_are_not_silently_fixed(case):
    for q in ["describes an application", "describes a local application!", "The server runs locally"]:
        f = grounded_finding(case, "Q1", "explicit", "Claim", "S1", 1, q)
        assert f["assessment"] == "unresolved"
        assert f["model_assessment"] == "explicit"
        assert f["proposed_citation"]["quote"] == q


def test_only_whitespace_normalizes(case):
    assert verify_quote(case["sources"], "S1", 1, "describes a\n local   application")["status"] == "verified"


@pytest.mark.parametrize("source,paragraph,quote", [("S8",1,"describes a local application"),("S1",2,"describes a local application"),("S1",0,"describes a local application"),("S1",1,"a local")])
def test_wrong_locator_and_short_quote_fail(case, source, paragraph, quote):
    assert verify_quote(case["sources"],source,paragraph,quote)["status"] == "invalid"


def test_snapshot_and_index_tampering_detected(case):
    altered=copy.deepcopy(case)
    altered["sources"][0]["text"] += " changed"
    assert verify_quote(altered["sources"],"S1",1,"describes a local application")["status"] == "invalid"
    altered=copy.deepcopy(case)
    altered["sources"][0]["paragraphs"][0]["text"] = "Invented text describes a local application"
    assert verify_quote(altered["sources"],"S1",1,"describes a local application")["status"] == "invalid"


def test_missing_findings_preserve_all_questions(case):
    findings = finalize_findings(case, [])
    assert [f["question_id"] for f in findings] == ["Q1", "Q2"]
    assert all(f["assessment"]=="unresolved" for f in findings)
    assert all(f["model_assessment"] is None for f in findings)


def test_search_reports_paragraph_and_scope(case):
    hits = search_sources(case["sources"], "availability benchmark")
    assert hits[0]["paragraph"] == 2
    assert search_sources(case["sources"], "unfindabletoken") == []


def test_review_preserves_original_run_and_records_history(case, tmp_path):
    case["status"] = "completed"
    case["findings"] = finalize_findings(case, [])
    case["run_seal"] = seal_run(case)
    original = canonical({"findings":case["findings"],"events":case["events"],"run":case["run"]})
    store=Store(tmp_path); store.save(case)
    first=store.review(case["id"],{"reviewer_type":"automated","reviewer_name":"Test runner","question_id":"Q1","decision":"inference","note":"Inspected fixture"})
    second=store.review(case["id"],{"reviewer_type":"automated","reviewer_name":"Test runner","question_id":"Q1","decision":"reject","note":"Revisited scope"})
    assert len(second["reviews"]) == 2
    assert seal_run(first) == seal_run(second) == case["run_seal"]
    assert canonical({"findings":second["findings"],"events":second["events"],"run":second["run"]}) == original
    second["questions"][0]["text"]="Changed research question"
    store.save(second)
    with pytest.raises(ValueError,match="changed"):
        store.review(case["id"],{"reviewer_type":"automated","reviewer_name":"Test runner","question_id":"Q1","decision":"accept","note":"Should fail"})


def test_export_manifest_csv_and_html(case):
    case["title"]="<script>bad</script>"
    case["questions"][0]["text"]="=2+2"
    case["findings"]=finalize_findings(case,[])
    with zipfile.ZipFile(io.BytesIO(export_packet(case))) as z:
        assert {"sources/S1.txt","agent-run.json","review-ledger.json","coverage.csv","SHA256SUMS"} <= set(z.namelist())
        for row in z.read("SHA256SUMS").decode().splitlines():
            sha,name=row.split("  ",1)
            assert hashlib.sha256(z.read(name)).hexdigest()==sha
        assert b"<script>bad" not in z.read("review-packet.html")
        assert b"'=2+2" in z.read("coverage.csv")
        assert json.loads(z.read("case.json"))["questions"][0]["text"] == "=2+2"


@pytest.mark.parametrize("url", ["http://strandsagents.com/docs/","https://127.0.0.1/","https://strandsagents.com.evil.example/","https://user:pass@strandsagents.com/","https://strandsagents.com:8443/"])
def test_importer_only_fetches_supported_public_origins(url):
    with pytest.raises(ValueError): validate_fetch_url(url)


def test_valid_public_origin():
    assert validate_fetch_url("https://strandsagents.com/docs/") == "https://strandsagents.com/docs/"


def test_recovery_and_path_validation(case,tmp_path):
    store=Store(tmp_path);case["status"]="running";store.save(case);store.recover()
    assert store.get(case["id"])["status"] == "interrupted"
    with pytest.raises(KeyError): store.get("../outside")


def test_duplicate_questions_rejected():
    with pytest.raises(ValidationError):
        CaseInput(title="Duplicates",questions=["Same?","Same?"],sources=[])
