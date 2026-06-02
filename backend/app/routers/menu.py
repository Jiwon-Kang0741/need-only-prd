"""
menu.py — 메뉴 트리 영구 저장 라우터
GET  /api/menu-tree  → menu_tree.json 읽기
POST /api/menu-tree  → menu_tree.json 쓰기
"""
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["menu"])

# 저장 파일 위치: backend/data/menu_tree.json
DATA_DIR  = Path(__file__).parent.parent.parent / "data"
MENU_FILE = DATA_DIR / "menu_tree.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)


class MenuTreePayload(BaseModel):
    rows: list[dict[str, Any]]


@router.get("/menu-tree")
def get_menu_tree():
    """저장된 메뉴 트리 반환. 파일 없으면 빈 리스트."""
    if not MENU_FILE.exists():
        return {"rows": []}
    try:
        data = json.loads(MENU_FILE.read_text(encoding="utf-8"))
        return {"rows": data if isinstance(data, list) else []}
    except Exception as e:
        logger.error("menu_tree.json 읽기 실패: %s", e)
        raise HTTPException(status_code=500, detail="메뉴 데이터 읽기 실패")


@router.post("/menu-tree")
def save_menu_tree(payload: MenuTreePayload):
    """메뉴 트리를 파일에 저장."""
    try:
        MENU_FILE.write_text(
            json.dumps(payload.rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("menu_tree.json 저장 완료 (%d rows)", len(payload.rows))
        return {"ok": True, "count": len(payload.rows)}
    except Exception as e:
        logger.error("menu_tree.json 쓰기 실패: %s", e)
        raise HTTPException(status_code=500, detail="메뉴 데이터 저장 실패")
