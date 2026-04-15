"""Direct pipeline test: run orchestrator and static_check to find root causes."""
import asyncio
import json
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("LLM_PROVIDER", "azure_openai")

from app.llm.orchestrator import CodeGenOrchestrator
from app.llm.agents import static_check

SAMPLE_SPEC = """
# 교육 과정 관리 기술 명세서 (spec.md)

## 1. 요구사항
- 교육 과정 목록 조회 (페이징, 검색)
- 교육 과정 저장 (등록/수정/삭제 배치)

## 2. 도메인 모델
| 필드명 | 타입 | 설명 |
|--------|------|------|
| eduPgmId | String | 교육과정 ID (PK) |
| eduPgmNm | String | 교육과정명 |
| eduType | String | 교육유형 |
| strtDt | String | 시작일 |
| endDt | String | 종료일 |

## 3. 화면 코드
- 모듈: edu
- 화면코드: EDUA001

## 4. 기능 목록
1. selectEduPgmList: 교육과정 목록 조회
2. saveEduPgm: 교육과정 저장 (INSERT/UPDATE/DELETE)
"""

async def main():
    orch = CodeGenOrchestrator()
    call_count = 0

    def inc():
        nonlocal call_count
        call_count += 1

    print("=== Starting code generation pipeline ===\n")
    events = []
    files_by_type = {}

    async for event in orch.run(SAMPLE_SPEC, inc):
        events.append(event)
        t = event.get("type", "")
        if t == "agent_start":
            print(f"[AGENT] {event.get('display_name')} started")
        elif t == "agent_complete":
            print(f"[AGENT] {event.get('agent')} completed ({event.get('files_count',0)} files)")
        elif t == "file_complete":
            ft = event.get("file_type", "")
            fp = event.get("file_path", "")
            content = event.get("content", "")
            files_by_type[fp] = {"file_type": ft, "content": content, "layer": event.get("layer", "")}
            print(f"  [FILE] {fp} ({ft})")
        elif t == "log":
            line = event.get("line", "")
            if "[STATIC]" in line or "[FIX]" in line or "[QA]" in line:
                print(f"  {line}")
        elif t == "error":
            print(f"[ERROR] {event.get('message')}")
        elif t == "complete":
            print(f"\n[COMPLETE] {event.get('message')}")

    print(f"\n=== LLM calls used: {call_count} ===")
    print(f"\n=== Generated files ({len(files_by_type)}) ===")
    for fp, info in files_by_type.items():
        print(f"  - {fp} ({info['file_type']})")

    # Save files for inspection
    out_dir = "test_output"
    os.makedirs(out_dir, exist_ok=True)
    for fp, info in files_by_type.items():
        # flatten path for saving
        safe_name = fp.replace("/", "__").replace("\\", "__")
        out_path = os.path.join(out_dir, safe_name)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"// file_type: {info['file_type']}\n// original_path: {fp}\n\n")
            f.write(info["content"])
    print(f"\nFiles saved to: {out_dir}/")

    # Run static check on all files
    from app.models import GeneratedFile
    gf_list = [
        GeneratedFile(
            file_path=fp,
            file_type=info["file_type"],
            content=info["content"],
            layer=info["layer"]
        )
        for fp, info in files_by_type.items()
    ]
    issues = static_check(gf_list)
    
    # Save issues to file (avoid encoding issues on terminal)
    issues_path = os.path.join(out_dir, "_issues.json")
    with open(issues_path, "w", encoding="utf-8") as f:
        json.dump(issues, f, ensure_ascii=False, indent=2)
    print(f"\n=== STATIC CHECK RESULTS ({len(issues)} issues) — saved to {issues_path} ===")
    for iss in issues:
        fp = iss.get('file_path','').encode('ascii','replace').decode()
        issue_short = iss.get('issue','')[:120].encode('ascii','replace').decode()
        print(f"\n[ISSUE] {fp}")
        print(f"  {issue_short}")

    # Save all events as JSON
    with open(os.path.join(out_dir, "_events.json"), "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print(f"\nAll SSE events saved to: {out_dir}/_events.json")

if __name__ == "__main__":
    asyncio.run(main())
