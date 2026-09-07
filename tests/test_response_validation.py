import json

from evidencedesk.agent import validate_model_response
from evidencedesk.core import CaseInput, create_case


def fixture_case():
    return create_case(CaseInput(title="Synthetic response test",questions=["What is stated?"],sources=[{
        "title":"Synthetic fixture","url":"https://docs.python.org/3/","text":"This is synthetic source text for a parser test only."}]))


def test_valid_actual_json_is_distinct_from_tool_call():
    result=validate_model_response(fixture_case(),"Q1",json.dumps({"assessment":"unresolved","explanation":"Missing evidence."}))
    assert result["record_method"]=="validated_model_response"
    assert result["assessment"]=="unresolved"


def test_invalid_json_never_gets_fabricated_answer():
    for text in ["A freeform answer",'{"assessment":"explicit"}', '{"assessment":"explicit","explanation":"ok","extra":"unexpected"}']:
        assert validate_model_response(fixture_case(),"Q1",text) is None


def test_json_citation_still_checked():
    result=validate_model_response(fixture_case(),"Q1",json.dumps({"assessment":"explicit","explanation":"Claim","source_id":"S1","paragraph":1,"quote":"A fabricated quotation that is not in the source."}))
    assert result["assessment"]=="unresolved"
    assert result["citation"]["status"]=="invalid"
