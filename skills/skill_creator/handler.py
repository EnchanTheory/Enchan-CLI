import json
import sys
from pathlib import Path

GUIDE_PATH = Path(__file__).resolve().parents[1] / "CREATE_SKILL.md"


def main() -> None:
    for line in sys.stdin:
        request = json.loads(line)
        request_id = request.get("id")
        method = request.get("method")

        if method != "read_guide":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"message": f"Unknown method: {method}"},
            }
        else:
            guide = GUIDE_PATH.read_text(encoding="utf-8")
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": guide,
                    "data": {"guide_path": str(GUIDE_PATH)},
                },
            }

        print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
