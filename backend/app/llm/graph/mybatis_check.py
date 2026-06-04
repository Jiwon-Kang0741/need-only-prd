"""Deterministic MyBatis binding verification (no LLM).

Parses DAO (.java) and Mapper (.xml) to cross-check that every DAO
`super.xxx("id")` call resolves to a Mapper <statement id="id"> and that the
Mapper namespace equals the DaoImpl FQCN. The DAO call string is the source of
truth; obvious 1:1 mismatches are auto-fixed, ambiguous ones are reported.
"""

from __future__ import annotations

import re

from app.llm.graph.naming import class_name_from_path

# super.{method}("statementId" ...)
_SUPER_CALL_RE = re.compile(
    r'super\s*\.\s*(?:select|selectOne|selectList|insert|update|delete|'
    r'batchUpdate\w*)\s*\(\s*"([A-Za-z0-9_]+)"'
)
_PACKAGE_RE = re.compile(r'\bpackage\s+([a-zA-Z0-9_.]+)\s*;')
_DAO_CLASS_RE = re.compile(r'\bclass\s+(\w*DaoImpl)\b')

_MAPPER_NS_RE = re.compile(r'<mapper\b[^>]*\bnamespace\s*=\s*"([^"]+)"')
_MAPPER_STMT_RE = re.compile(
    r'<(?:select|insert|update|delete)\b[^>]*\bid\s*=\s*"([^"]+)"'
)

# public <returnType> <method>(<params>) { ... }
_PUBLIC_METHOD_RE = re.compile(
    r'\bpublic\s+([A-Za-z0-9_<>\[\].,\s?]+?)\s+(\w+)\s*\(([^)]*)\)\s*\{',
    re.MULTILINE,
)
_DAO_FIELD_RE = re.compile(
    r'\b(?:private|protected|public)\s+(?:final\s+)?(\w+DaoImpl)\s+(\w+)\s*;',
    re.MULTILINE,
)
_LOCAL_VAR_RE = re.compile(
    r'\b(?:final\s+)?([A-Za-z_][\w<>\[\].,? ]+)\s+(\w+)\s*(?:=|;)',
    re.MULTILINE,
)
_DAO_CALL_RE = re.compile(r'\b(\w+)\.(\w+)\s*\(([^)]*)\)')


def parse_dao(content: str) -> dict:
    """Return {statement_ids: set[str], expected_namespace: str|None}."""
    ids = set(_SUPER_CALL_RE.findall(content))
    pkg_m = _PACKAGE_RE.search(content)
    cls_m = _DAO_CLASS_RE.search(content)
    ns = f"{pkg_m.group(1)}.{cls_m.group(1)}" if pkg_m and cls_m else None
    return {"statement_ids": ids, "expected_namespace": ns}


def parse_mapper(content: str) -> dict:
    """Return {ids: set[str], namespace: str|None}."""
    ns_m = _MAPPER_NS_RE.search(content)
    ids = set(_MAPPER_STMT_RE.findall(content))
    return {"ids": ids, "namespace": ns_m.group(1) if ns_m else None}


def _basename(file_path: str, suffix: str) -> str | None:
    """'.../CpmsEduRsltLstDaoImpl.java' + 'DaoImpl' -> 'CpmsEduRsltLst'."""
    fname = file_path.replace("\\", "/").split("/")[-1]
    stem = fname.rsplit(".", 1)[0]  # drop extension
    if stem.endswith(suffix):
        return stem[: -len(suffix)]
    return None


def match_pairs(files: dict) -> tuple[list[tuple[dict, dict]], list[dict]]:
    """Pair DaoImpl ↔ Mapper by name rule. Returns (pairs, unpaired_issues)."""
    daos: dict[str, dict] = {}
    mappers: dict[str, dict] = {}
    for gf in files.values():
        fp = gf["file_path"]
        if fp.endswith("DaoImpl.java"):
            base = _basename(fp, "DaoImpl")
            if base:
                daos[base] = gf
        elif fp.endswith("Mapper.xml"):
            base = _basename(fp, "Mapper")
            if base:
                mappers[base] = gf

    pairs: list[tuple[dict, dict]] = []
    unpaired: list[dict] = []
    for base, dao_gf in daos.items():
        if base in mappers:
            pairs.append((dao_gf, mappers[base]))
        else:
            unpaired.append({"file_path": dao_gf["file_path"],
                             "issue": f"{base}DaoImpl has no matching Mapper xml",
                             "severity": "error"})
    for base, mapper_gf in mappers.items():
        if base not in daos:
            unpaired.append({"file_path": mapper_gf["file_path"],
                             "issue": f"{base}Mapper xml has no matching DaoImpl",
                             "severity": "warning"})
    return pairs, unpaired


def _contract_ids(contract) -> set[str]:
    ops = (contract or {}).get("operations") or []
    return {o["statement_id"] for o in ops}


def _normalize_type(type_name: str) -> str:
    t = (type_name or "").strip()
    # remove parameter annotations, e.g. @Valid, @Nullable("x")
    t = re.sub(r'@\w+(?:\([^)]*\))?\s*', '', t)
    t = re.sub(r'\bfinal\s+', '', t)
    t = re.sub(r'\s+', '', t)
    # normalize common java.util wrappers to short names
    t = t.replace("java.util.List", "List")
    t = t.replace("java.lang.String", "String")
    t = t.replace("java.lang.Integer", "Integer")
    t = t.replace("java.lang.Long", "Long")
    t = t.replace("java.lang.Boolean", "Boolean")
    t = t.replace("java.lang.Double", "Double")
    t = t.replace("java.lang.Float", "Float")
    return t


def _simple_type(type_name: str) -> str:
    # turn fully-qualified names into simple names, including generics
    return re.sub(r'\b(?:[a-z_]\w*\.)+([A-Za-z_]\w*)', r'\1', _normalize_type(type_name))


def _types_compatible(actual: str, expected: str) -> bool:
    a = _normalize_type(actual)
    e = _normalize_type(expected)
    return a == e or _simple_type(a) == _simple_type(e)


def _split_top_level_commas(text: str) -> list[str]:
    parts: list[str] = []
    cur: list[str] = []
    angle = 0
    paren = 0
    for ch in text:
        if ch == '<':
            angle += 1
        elif ch == '>' and angle > 0:
            angle -= 1
        elif ch == '(':
            paren += 1
        elif ch == ')' and paren > 0:
            paren -= 1
        if ch == ',' and angle == 0 and paren == 0:
            parts.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)
    tail = "".join(cur).strip()
    if tail:
        parts.append(tail)
    return parts


def _parse_param_pairs(params: str) -> list[tuple[str, str]]:
    params = (params or "").strip()
    if not params:
        return []
    out: list[tuple[str, str]] = []
    for raw in _split_top_level_commas(params):
        token = re.sub(r'@\w+(?:\([^)]*\))?\s*', '', raw).strip()
        token = re.sub(r'\bfinal\s+', '', token).strip()
        if not token:
            continue
        # last token is variable name; the prefix is type
        bits = token.split()
        if len(bits) >= 2:
            out.append((" ".join(bits[:-1]), bits[-1]))
        else:
            out.append((token, ""))
    return out


def _iter_public_methods(content: str):
    for m in _PUBLIC_METHOD_RE.finditer(content):
        ret_type = m.group(1).strip()
        method = m.group(2).strip()
        params = m.group(3).strip()
        body_start = m.end() - 1  # points at '{'
        depth = 0
        end = body_start
        for i in range(body_start, len(content)):
            ch = content[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        body = content[body_start + 1:end] if end > body_start else ""
        yield {
            "name": method,
            "return_type": ret_type,
            "param_types": [t for t, _ in _parse_param_pairs(params)],
            "param_pairs": _parse_param_pairs(params),
            "body": body,
        }


def _dao_method_signatures(content: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for m in _iter_public_methods(content):
        out.setdefault(m["name"], []).append({
            "return_type": m["return_type"],
            "param_types": m["param_types"],
        })
    return out


def _service_dao_fields(content: str) -> dict[str, str]:
    return {var: typ for typ, var in _DAO_FIELD_RE.findall(content)}


def _method_var_types(method: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for p_type, p_name in method.get("param_pairs", []):
        if p_name:
            out[p_name] = p_type
    for typ, var in _LOCAL_VAR_RE.findall(method["body"]):
        out[var] = typ.strip()
    return out


def check_service_dao_signatures(files: dict) -> list[dict]:
    """ServiceImpl -> DaoImpl call signature consistency check.

    Detects:
    - Service call to a DAO method that does not exist
    - Simple parameter-type mismatch when arg type can be inferred
      (notably DTO vs List<DTO> mismatch)
    """
    issues: list[dict] = []
    daos = [gf for gf in files.values() if gf["file_path"].endswith("DaoImpl.java")]
    services = [gf for gf in files.values() if gf["file_path"].endswith("ServiceImpl.java")]
    if not daos or not services:
        return issues

    # class name -> signatures
    dao_sigs: dict[str, dict[str, list[dict]]] = {}
    for dao_gf in daos:
        cls = class_name_from_path(dao_gf["file_path"])
        dao_sigs[cls] = _dao_method_signatures(dao_gf["content"])

    for svc_gf in services:
        dao_vars = _service_dao_fields(svc_gf["content"])
        if not dao_vars:
            continue
        for method in _iter_public_methods(svc_gf["content"]):
            vars_in_scope = _method_var_types(method)
            for var, call_name, args_text in _DAO_CALL_RE.findall(method["body"]):
                dao_cls = dao_vars.get(var)
                if not dao_cls:
                    continue
                sigs_by_name = dao_sigs.get(dao_cls, {})
                targets = sigs_by_name.get(call_name, [])
                if not targets:
                    issues.append({
                        "file_path": svc_gf["file_path"],
                        "issue": (f"Service calls {var}.{call_name}(...) but {dao_cls} has no "
                                  "such public method"),
                        "severity": "error",
                    })
                    continue

                args = _split_top_level_commas(args_text)
                # First check arity-compatible signatures (best-effort; keeps overload support)
                arity_matches = [s for s in targets if len(s["param_types"]) == len(args)]
                if not arity_matches:
                    issues.append({
                        "file_path": svc_gf["file_path"],
                        "issue": (f"Service calls {var}.{call_name} with {len(args)} arg(s), but "
                                  f"{dao_cls}.{call_name} expects "
                                  f"{'/'.join(str(len(s['param_types'])) for s in targets)}"),
                        "severity": "error",
                    })
                    continue

                # Type check only when every arg is a simple variable with known type.
                arg_types: list[str] = []
                resolvable = True
                for arg in args:
                    a = arg.strip()
                    if re.match(r'^[A-Za-z_]\w*$', a) and a in vars_in_scope:
                        arg_types.append(vars_in_scope[a])
                    else:
                        resolvable = False
                        break
                if not resolvable:
                    continue

                compatible = False
                for sig in arity_matches:
                    if all(_types_compatible(actual, expected)
                           for actual, expected in zip(arg_types, sig["param_types"])):
                        compatible = True
                        break
                if not compatible:
                    expected_join = " | ".join(
                        "(" + ", ".join(_simple_type(t) for t in sig["param_types"]) + ")"
                        for sig in arity_matches
                    )
                    got = "(" + ", ".join(_simple_type(t) for t in arg_types) + ")"
                    issues.append({
                        "file_path": svc_gf["file_path"],
                        "issue": (f"DAO call type mismatch: {var}.{call_name}{got} -> expected "
                                  f"{expected_join} in {dao_cls}"),
                        "severity": "error",
                    })
    return issues


def check_binding(files: dict, contract: dict | None = None) -> list[dict]:
    """Detect namespace/id mismatches. If contract has operations, that id set is
    the source of truth (both DAO and Mapper must match it); otherwise the DAO
    super(...) calls are the truth (Phase 1, backward compatible)."""
    pairs, issues = match_pairs(files)
    issues = list(issues)  # copy unpaired issues
    truth_ids = _contract_ids(contract)

    for dao_gf, mapper_gf in pairs:
        dao = parse_dao(dao_gf["content"])
        mapper = parse_mapper(mapper_gf["content"])

        # 1. namespace must equal DaoImpl FQCN
        if dao["expected_namespace"] and mapper["namespace"] != dao["expected_namespace"]:
            issues.append({
                "file_path": mapper_gf["file_path"],
                "issue": (f"Mapper namespace '{mapper['namespace']}' != DaoImpl FQCN "
                          f"'{dao['expected_namespace']}'"),
                "severity": "error",
            })

        if truth_ids:
            # contract is truth: DAO and Mapper ids must each equal truth_ids
            for sid in sorted(dao["statement_ids"] - truth_ids):
                issues.append({"file_path": dao_gf["file_path"],
                               "issue": f"DAO statement '{sid}' is not in contract operations",
                               "severity": "error"})
            for sid in sorted(mapper["ids"] - truth_ids):
                issues.append({"file_path": mapper_gf["file_path"],
                               "issue": f"Mapper statement '{sid}' is not in contract operations",
                               "severity": "error"})
            for sid in sorted(truth_ids - dao["statement_ids"]):
                issues.append({"file_path": dao_gf["file_path"],
                               "issue": f"DAO missing contract statement '{sid}'",
                               "severity": "error"})
            for sid in sorted(truth_ids - mapper["ids"]):
                issues.append({"file_path": mapper_gf["file_path"],
                               "issue": f"Mapper missing contract statement '{sid}'",
                               "severity": "error"})
        else:
            # Phase 1: DAO super calls are truth
            for sid in sorted(dao["statement_ids"] - mapper["ids"]):
                issues.append({
                    "file_path": mapper_gf["file_path"],
                    "issue": (f"DAO calls statement '{sid}' but Mapper has no matching "
                              f"<statement id=\"{sid}\">"),
                    "severity": "error",
                })
            for sid in sorted(mapper["ids"] - dao["statement_ids"]):
                issues.append({
                    "file_path": mapper_gf["file_path"],
                    "issue": f"Mapper statement '{sid}' is not called by any DAO method",
                    "severity": "warning",
                })
    return issues


_EDIT_DISTANCE_THRESHOLD = 0.3  # normalized; ≤ this is "obvious variant"


def _edit_distance(a: str, b: str) -> int:
    """Levenshtein distance."""
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _normalized_distance(a: str, b: str) -> float:
    m = max(len(a), len(b))
    return _edit_distance(a, b) / m if m else 0.0


def _is_commented(content: str, pos: int) -> bool:
    """True if `pos` falls inside a // line comment, or a /* */ or <!-- --> block
    comment. Keeps regex source rewrites from editing identifiers in comments."""
    line_start = content.rfind("\n", 0, pos) + 1
    if "//" in content[line_start:pos]:
        return True
    for open_d, close_d in (("/*", "*/"), ("<!--", "-->")):
        o = content.rfind(open_d, 0, pos)
        if o != -1:
            c = content.find(close_d, o)
            if c == -1 or c >= pos:  # open before pos, close missing or after pos
                return True
    return False


def _align_ids_to_truth(content, current_ids, truth_ids, pattern_tmpl, file_path):
    """Rename each current id not in truth_ids to its nearest truth id (≤ threshold,
    1:1 greedy). pattern_tmpl uses {have} placeholder for the id being replaced.
    Skips matches inside comments so commented-out code is never rewritten."""
    logs = []
    wrong = [i for i in current_ids if i not in truth_ids]
    available = [t for t in truth_ids if t not in current_ids]
    used: set[str] = set()
    for have in wrong:
        best, best_d = None, 1.0
        for want in available:
            if want in used:
                continue
            d = _normalized_distance(have, want)
            if d < best_d:
                best, best_d = want, d
        if best is not None and best_d <= _EDIT_DISTANCE_THRESHOLD:
            pat = re.compile(pattern_tmpl.replace("{have}", re.escape(have)))
            # Replace the first match that is NOT inside a comment (count=1 semantics).
            for m in pat.finditer(content):
                if _is_commented(content, m.start()):
                    continue
                content = content[:m.start()] + m.group(1) + best + m.group(2) + content[m.end():]
                used.add(best)
                logs.append(f"{file_path}: id '{have}' → '{best}' (contract)")
                break
    return content, logs


def autofix_binding(files: dict, contract: dict | None = None) -> tuple[dict, list[str]]:
    """Apply deterministic fixes. With contract.operations, both DAO and Mapper ids
    are aligned to contract bare ids; without, DAO super calls are truth (Phase 1).

    Returns (fixed_files_copy, log_lines). Ambiguous mismatches are left untouched.
    """
    fixed = {p: dict(gf) for p, gf in files.items()}
    logs: list[str] = []
    pairs, _ = match_pairs(fixed)
    truth_ids = sorted(_contract_ids(contract))

    for dao_gf, mapper_gf in pairs:
        dao = parse_dao(dao_gf["content"])
        mapper = parse_mapper(mapper_gf["content"])
        dao_content = dao_gf["content"]
        mapper_content = mapper_gf["content"]

        # namespace → DaoImpl FQCN (always obvious)
        if dao["expected_namespace"] and mapper["namespace"] != dao["expected_namespace"]:
            mapper_content = re.sub(
                r'(<mapper\b[^>]*\bnamespace\s*=\s*")[^"]+(")',
                lambda m: m.group(1) + dao["expected_namespace"] + m.group(2),
                mapper_content, count=1,
            )
            logs.append(f"{mapper_gf['file_path']}: namespace → {dao['expected_namespace']}")

        if truth_ids:
            # contract is truth: align both Mapper ids and DAO super-call ids to it
            mapper_content, mlogs = _align_ids_to_truth(
                mapper_content, sorted(mapper["ids"]), truth_ids,
                r'(\bid\s*=\s*"){have}(")', mapper_gf["file_path"])
            logs += mlogs
            dao_content, dlogs = _align_ids_to_truth(
                dao_content, sorted(dao["statement_ids"]), truth_ids,
                r'(super\s*\.\s*\w+\s*\(\s*"){have}(")', dao_gf["file_path"])
            logs += dlogs
        else:
            # Phase 1: align Mapper ids to DAO super-call ids (greedy 1:1)
            missing = sorted(dao["statement_ids"] - mapper["ids"])
            unused = sorted(mapper["ids"] - dao["statement_ids"])
            used_have: set[str] = set()
            for want in missing:
                best, best_d = None, 1.0
                for have in unused:
                    if have in used_have:
                        continue
                    d = _normalized_distance(want, have)
                    if d < best_d:
                        best, best_d = have, d
                if best is not None and best_d <= _EDIT_DISTANCE_THRESHOLD:
                    used_have.add(best)
                    mapper_content = re.sub(
                        rf'(\bid\s*=\s*"){re.escape(best)}(")',
                        lambda m, w=want: m.group(1) + w + m.group(2),
                        mapper_content, count=1,
                    )
                    logs.append(f"{mapper_gf['file_path']}: statement id '{best}' → '{want}'")

        fixed[dao_gf["file_path"]] = {**dao_gf, "content": dao_content}
        fixed[mapper_gf["file_path"]] = {**mapper_gf, "content": mapper_content}

    return fixed, logs


_FIELD_DECL_RE = re.compile(r'\bprivate\s+\S[\w<>,.\[\]]*\s+(\w+)\s*(?:=[^;]*)?;')
_JAVA_FIELD_NAME_RE = re.compile(r'^[A-Za-z_$][A-Za-z0-9_$]*$')

# Per-line `private <Type> <name>[ = init];` — for the duplicate-field cleaner.
_DTO_ANY_FIELD_RE = re.compile(
    r'^(\s*private\s+\S+(?:\s*<[^>]+>)?(?:\s*\[\s*\])?\s+)(\w+)(\s*(?:=\s*[^;]+)?\s*;.*)$')
# `private <BannedScalar>[] <name>[ = init];` — Java arrays banned in DTOs
# (break MyBatis/StringUtils). Same type set the static_check array rule flags.
_DTO_BANNED_ARRAY_RE = re.compile(
    r'(private\s+)(?:String|Integer|Long|Double|Float|Boolean|'
    r'int|long|double|float|boolean)\s*\[\s*\]\s+(\w+)\s*(?:=\s*[^;]+)?\s*;')

_DTO_FILE_TYPES = ("dto_request", "dto_response")


def _is_backend_dto(gf: dict) -> bool:
    return (gf.get("file_type") in _DTO_FILE_TYPES
            and gf.get("file_path", "").endswith(".java"))


def autofix_dedupe_dto_fields(files: dict) -> tuple[dict, list[str]]:
    """Drop duplicate `private <Type> <name>;` decls within a DTO, keeping the
    first occurrence (usually the well-typed one). Ported from agents.py."""
    fixed = {p: dict(gf) for p, gf in files.items()}
    logs: list[str] = []
    for gf in fixed.values():
        if not _is_backend_dto(gf):
            continue
        seen: set[str] = set()
        new_lines: list[str] = []
        removed = 0
        for line in gf["content"].split("\n"):
            m = _DTO_ANY_FIELD_RE.match(line)
            if m and m.group(2) in seen:
                removed += 1
                continue
            if m:
                seen.add(m.group(2))
            new_lines.append(line)
        if removed:
            gf["content"] = "\n".join(new_lines)
            logs.append(f"{gf['file_path']}: removed {removed} duplicate field decl(s)")
    return fixed, logs


def autofix_dto_array_fields(files: dict) -> tuple[dict, list[str]]:
    """Downgrade banned `private <Scalar>[] x [=...];` DTO fields to
    `private String x;` (CPMS comma-separated convention; no new import).
    Java arrays in DTOs break MyBatis/JSON binding. Ported from agents.py."""
    fixed = {p: dict(gf) for p, gf in files.items()}
    logs: list[str] = []
    for gf in fixed.values():
        if not _is_backend_dto(gf):
            continue
        new_content, n = _DTO_BANNED_ARRAY_RE.subn(
            lambda m: f"{m.group(1)}String {m.group(2)};", gf["content"])
        if n:
            gf["content"] = new_content
            logs.append(f"{gf['file_path']}: downgraded {n} array field(s) → String")
    return fixed, logs


def _dto_files_by_class(files: dict) -> dict[str, dict]:
    out = {}
    for gf in files.values():
        if gf["file_path"].endswith(".java") and "Dto" in gf["file_path"]:
            cls = class_name_from_path(gf["file_path"])
            out[cls] = gf
    return out


def check_dto_fields(files: dict, contract: dict | None = None) -> list[dict]:
    """Flag contract-required DTO fields missing from the generated DTO."""
    dtos = (contract or {}).get("dtos") or []
    by_class = _dto_files_by_class(files)
    issues = []
    for d in dtos:
        gf = by_class.get(d["name"])
        if not gf:
            continue
        present = set(_FIELD_DECL_RE.findall(gf["content"]))
        for f in d["fields"]:
            if not _JAVA_FIELD_NAME_RE.match(f["name"]):
                continue
            if f["name"] not in present:
                issues.append({"file_path": gf["file_path"],
                               "issue": f"DTO {d['name']} missing contract field '{f['name']}'",
                               "severity": "error"})
    return issues


def autofix_dto_fields(files: dict, contract: dict | None = None) -> tuple[dict, list[str]]:
    """Insert missing contract fields as `private <java_type> <name>;` before the
    final closing brace of the class."""
    fixed = {p: dict(gf) for p, gf in files.items()}
    logs = []
    dtos = (contract or {}).get("dtos") or []
    by_class = _dto_files_by_class(fixed)
    for d in dtos:
        gf = by_class.get(d["name"])
        if not gf:
            continue
        content = gf["content"]
        present = set(_FIELD_DECL_RE.findall(content))
        additions = []
        for f in d["fields"]:
            if f["name"] in present:
                continue
            if not _JAVA_FIELD_NAME_RE.match(f["name"]):
                logs.append(f"{gf['file_path']}: skip field '{f['name']}' (invalid java identifier)")
                continue
            jt = f.get("java_type")
            if not jt:
                logs.append(f"{gf['file_path']}: skip field '{f['name']}' (no java_type)")
                continue
            additions.append(f"    private {jt} {f['name']};")
        if additions:
            idx = content.rfind("}")
            if idx != -1:
                content = content[:idx] + "\n".join(additions) + "\n" + content[idx:]
                logs.append(f"{gf['file_path']}: added {len(additions)} contract field(s)")
                fixed[gf["file_path"]] = {**gf, "content": content}
    return fixed, logs
