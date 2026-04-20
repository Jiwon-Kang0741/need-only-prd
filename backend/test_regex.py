"""Test: why does _apply_fix fail on the actual PFY DaoImpl file?"""
import re
from pathlib import Path

dao_content = Path(r"C:\workspace_pfy\PFY\pfy\src\main\java\biz\edu\dao\CpmsEduPondgLstDaoImpl.java").read_text(encoding="utf-8")
req_content = Path(r"C:\workspace_pfy\PFY\pfy\src\main\java\biz\edu\dto\request\CpmsEduPondgLstReqDto.java").read_text(encoding="utf-8")
res_content = Path(r"C:\workspace_pfy\PFY\pfy\src\main\java\biz\edu\dto\response\CpmsEduPondgLstResDto.java").read_text(encoding="utf-8")

# Simulate _dao_req_classes/_dao_res_classes collection
_dao_req_classes = []
_dao_res_classes = []
m2 = re.search(r'public\s+class\s+(\w+ReqDto)\b', req_content)
if m2:
    _dao_req_classes.append(m2.group(1))
m2 = re.search(r'public\s+class\s+(\w+ResDto)\b', res_content)
if m2:
    _dao_res_classes.append(m2.group(1))

print("_dao_req_classes:", _dao_req_classes)
print("_dao_res_classes:", _dao_res_classes)

_known_res = _dao_res_classes[0] if _dao_res_classes else None
_known_req = _dao_req_classes[0] if _dao_req_classes else None
print("_known_res:", _known_res)
print("_known_req:", _known_req)

_allowed_param_types = {"String","int","long","Integer","Long","boolean","Boolean","double","Double"}
for c in _dao_req_classes + _dao_res_classes:
    _allowed_param_types.add(c)

_bad_param_re = re.compile(
    r'(public\s+\S+\s+\w+\s*\(\s*)([A-Za-z][A-Za-z0-9]*)(\s+\w+\s*\))',
)

print("\n=== All DaoImpl method signatures matched by regex ===")
for m in _bad_param_re.finditer(dao_content):
    print(f"  type='{m.group(2)}' in {m.group(1).strip()}")
    if m.group(2) not in _allowed_param_types:
        print(f"    ^^^ WOULD BE REPLACED with {_known_res}")

def _apply_fix(m):
    prefix, param_type, suffix = m.group(1), m.group(2), m.group(3)
    if param_type in _allowed_param_types:
        return m.group(0)
    mname_m = re.search(r'public\s+\S+\s+(\w+)\s*\(', prefix)
    if mname_m:
        mname = mname_m.group(1).lower()
        _uses_res = any(k in mname for k in ("duplicate", "count", "insert", "update", "delete"))
        if _uses_res and _known_res:
            replacement = _known_res
        elif mname.startswith("select") and _known_req:
            replacement = _known_req
        else:
            replacement = _known_res or _known_req
    else:
        replacement = _known_res or _known_req

    if replacement and replacement != param_type:
        print(f"\n  REPLACING '{param_type}' -> '{replacement}'")
        return f"{prefix}{replacement}{suffix}"
    print(f"\n  SKIP (replacement={replacement}, param_type={param_type})")
    return m.group(0)

print("\n=== Applying fix ===")
result = _bad_param_re.sub(_apply_fix, dao_content)
print("\n=== Result (method signatures only) ===")
for line in result.splitlines():
    if "public" in line and "(" in line:
        print(" ", line.strip())
