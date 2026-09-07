import argparse
import json
from pathlib import Path

from .agent import run_case
from .core import CaseInput, create_case, export_packet


def main():
    parser = argparse.ArgumentParser(description="EvidenceDesk local research workflow")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8765)
    run = sub.add_parser("run")
    run.add_argument("input", type=Path)
    run.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "serve":
        import uvicorn
        uvicorn.run("evidencedesk.app:create_app", factory=True, host="127.0.0.1", port=args.port)
    else:
        case = create_case(CaseInput.model_validate_json(args.input.read_text()))
        result = run_case(case)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "case.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        (args.output / "review-packet.zip").write_bytes(export_packet(result))
        print(json.dumps({"status": result["status"], "questions": len(result["findings"]), "run": result["run"]}, indent=2))


if __name__ == "__main__":
    main()
