import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Set

from django.core.management.base import BaseCommand, CommandError

# --------------------------------------------------------------------
# This command **does not touch the DB**. It converts your raw JSONs
# (credits list, posprevias-by-code, and requirements tree) into a
# **normalized pair of JSON files** that are easier to feed into the
# `load_bedelia` importer:
#   1) subjects_normalized.json (list of subjects with code/name/credits)
#   2) requirements_normalized.json (cleaned requirements trees)
# You can then run:
#   python manage.py load_bedelia --program-name "1997 - INGENIERIA EN COMPUTACION" \
#       --plan-year 1997 \
#       --subjects subjects_normalized.json \
#       --requirements requirements_normalized.json \
#       --default-term 2025S1
# --------------------------------------------------------------------

CODE_RE = re.compile(r"(\d{3,5})")


def norm_code(x: Any) -> str:
    if x is None:
        return ""
    s = str(x).strip()
    # Keep only first 3-5 digit sequence if mixed junk arrives
    m = CODE_RE.search(s)
    return m.group(1) if m else s


def norm_str(x: Any) -> str:
    return ("" if x is None else str(x)).strip()


def norm_mode_to_label(mode: str) -> str:
    m = norm_str(mode).lower()
    if m in {"curso", "course", "c"}:
        return "Curso"
    if m in {"examen", "exam", "e"}:
        return "Examen"
    return mode or ""


def norm_item_kind(kind: str) -> str:
    k = norm_str(kind).lower()
    if k in {"curso", "course", "c"}:
        return "curso"
    if k in {"examen", "exam", "e"}:
        return "examen"
    return k or "aprobada"


# ------------------------------
# Node normalization helpers
# ------------------------------

def normalize_leaf(node: Dict[str, Any]) -> Dict[str, Any]:
    rule = norm_str(node.get("rule")).lower()
    label = norm_str(node.get("label") or node.get("raw"))
    out: Dict[str, Any] = {"type": "LEAF", "label": label}

    if rule == "min_approvals":
        items: List[Dict[str, Any]] = []
        for it in node.get("items", []) or []:
            code = norm_code(it.get("code"))
            name = norm_str(it.get("name") or code)
            kind = norm_item_kind(it.get("kind"))
            if not code:
                continue
            items.append({
                "source": norm_str(it.get("source") or "UCB"),
                "kind": kind,  # 'curso' | 'examen' (or 'aprobada' fallback)
                "code": code,
                "name": name,
                "raw": norm_str(it.get("raw") or f"{kind} {code} - {name}")
            })
        # de-duplicate items by (kind, code)
        dedup: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for it in items:
            dedup[(it["kind"], it["code"])] = it
        out.update({
            "rule": "min_approvals",
            "required_count": int(node.get("required_count") or 1),
            "items": list(dedup.values()),
            "raw": label or node.get("raw"),
        })
        return out

    if rule == "credits_in_plan":
        out.update({
            "rule": "credits_in_plan",
            "credits": int(node.get("credits") or 0),
            "plan": norm_str(node.get("plan")),
            "raw": label or node.get("raw"),
        })
        return out

    # Keep unknown rules as raw_text for later human review
    out.update({
        "rule": "raw_text",
        "value": label or node.get("value") or node.get("raw") or "",
        "raw": node.get("raw") or label,
    })
    return out


def normalize_node(node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize one requirement node. Returns None for empty/invalid nodes."""
    ntype = norm_str(node.get("type")).upper()

    if ntype in {"ALL", "ANY", "NONE"}:
        children = [normalize_node(ch) for ch in (node.get("children") or [])]
        children = [c for c in children if c]
        # Drop empty ALL nodes entirely; they don't add constraints
        if ntype == "ALL" and not children:
            return None
        out: Dict[str, Any] = {
            "type": ntype,
            "label": norm_str(node.get("label") or node.get("raw")),
        }
        if ntype == "ANY":
            # Preserve required_count if present; default 1
            rc = node.get("required_count")
            if rc is not None:
                out["required_count"] = int(rc)
        out["children"] = children
        return out

    if ntype == "LEAF":
        return normalize_leaf(node)

    # Unknown type → treat as raw_text leaf
    return {
        "type": "LEAF",
        "label": norm_str(node.get("label") or node.get("raw")),
        "rule": "raw_text",
        "value": norm_str(node.get("label") or node.get("raw") or ""),
        "raw": node.get("raw"),
    }


# ------------------------------
# Converter core
# ------------------------------

def extract_subjects_from_credits(credits_list: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    subj: Dict[str, Dict[str, Any]] = {}
    for row in credits_list or []:
        code = norm_code(row.get("codigo"))
        if not code:
            continue
        name = norm_str(row.get("nombre") or code)
        credits = row.get("creditos")
        try:
            cred_val = float(credits) if credits is not None else None
        except Exception:
            cred_val = None
        subj[code] = {"code": code, "name": name, "credits": cred_val}
    return subj


def extract_subjects_from_requirements(reqs_tree: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    subj: Dict[str, Dict[str, Any]] = {}
    for key in (reqs_tree or {}).keys():
        m = CODE_RE.search(key or "")
        if not m:
            continue
        code = m.group(1)
        name = norm_str(key.split("-", 1)[-1]) if "-" in key else key
        subj.setdefault(code, {"code": code, "name": name, "credits": None})
    # Also scan leaf items for subject codes and names
    def walk(n: Dict[str, Any]):
        if not n:
            return
        if n.get("type") == "LEAF" and n.get("rule") == "min_approvals":
            for it in n.get("items", []) or []:
                code = norm_code(it.get("code"))
                if code:
                    name = norm_str(it.get("name") or code)
                    subj.setdefault(code, {"code": code, "name": name, "credits": None})
        for ch in n.get("children", []) or []:
            walk(ch)
    for obj in (reqs_tree or {}).values():
        walk(obj.get("requirements"))
    return subj


def extract_subjects_from_posprevias(posprev: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    subj: Dict[str, Dict[str, Any]] = {}
    for code, v in (posprev or {}).items():
        code = norm_code(code)
        if not code:
            continue
        subj.setdefault(code, {"code": code, "name": norm_str(v.get("name") or v.get("code") or code), "credits": None})
        for pp in v.get("posprevias", []) or []:
            req_code = norm_code(pp.get("materia_codigo"))
            if req_code:
                subj.setdefault(req_code, {"code": req_code, "name": norm_str(pp.get("materia_nombre") or req_code), "credits": None})
    return subj


def unify_subjects(*dicts: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for d in dicts:
        for k, v in d.items():
            if k not in merged:
                merged[k] = {"code": v["code"], "name": v.get("name") or v["code"], "credits": v.get("credits")}
            else:
                # prefer name if existing is placeholder
                if merged[k].get("name") in ("", k) and v.get("name"):
                    merged[k]["name"] = v["name"]
                # prefer numeric credits if available
                if merged[k].get("credits") is None and v.get("credits") is not None:
                    merged[k]["credits"] = v["credits"]
    # stable sort by int(code) if numeric
    def sort_key(x: Dict[str, Any]):
        try:
            return (0, int(x["code"]))  # Sort numbers first, numerically
        except ValueError:  # Catch ValueError specifically for int conversion
            return (1, x["code"])  # Sort non-numbers second, alphabetically
    return sorted(merged.values(), key=sort_key)


def normalize_requirements_tree(raw_tree: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, obj in (raw_tree or {}).items():
        m = CODE_RE.search(key or "")
        if not m:
            continue
        code = m.group(1)
        mode_label = norm_mode_to_label(obj.get("name") or "")  # 'Curso' or 'Examen'
        req_node = normalize_node(obj.get("requirements") or {})
        if not req_node:
            continue
        # Compose a clean key with canonical spacing
        subj_name = norm_str(key.split("-", 1)[-1]) if "-" in key else key
        new_key = f"{code} - {subj_name}"
        out[new_key] = {
            "code": new_key,
            "name": mode_label,
            "requirements": req_node,
        }
    return out


def generate_posprevias_offering_nodes(posprev: Dict[str, Any]) -> Dict[str, Any]:
    """Produce minimal ANY(min=1) trees from posprevias for both Curso and Examen
    (so the loader can import offerings even where no complex tree exists)."""
    trees: Dict[str, Any] = {}
    for code, v in (posprev or {}).items():
        code = norm_code(code)
        if not code:
            continue
        name = norm_str(v.get("name") or v.get("code") or code)
        # Build a leaf group ANY(min=1) with items
        items: List[Dict[str, Any]] = []
        for pp in v.get("posprevias", []) or []:
            k = norm_item_kind(pp.get("tipo"))
            c = norm_code(pp.get("materia_codigo"))
            nm = norm_str(pp.get("materia_nombre") or c)
            if not c:
                continue
            items.append({"source": "posprevias", "kind": k, "code": c, "name": nm, "raw": f"{k} {c} - {nm}"})
        if not items:
            continue
        req_node = {
            "type": "ANY",
            "label": "(Derivado de posprevias)",
            "required_count": 1,
            "children": [
                {
                    "type": "LEAF",
                    "label": "posprevias",
                    "rule": "min_approvals",
                    "required_count": 1,
                    "items": items,
                }
            ],
        }
        for mode_label in ("Curso", "Examen"):
            key = f"{code} - {name}"
            trees[f"{key}::{mode_label}"] = {
                "code": key,
                "name": mode_label,
                "requirements": req_node,
            }
    # return without the ::mode suffix in keys, merge later with preference to true trees
    # The caller will strip the suffix and only include where no real tree exists.
    return trees


class Command(BaseCommand):
    help = "Convert raw Bedelía JSONs into normalized subjects.json and requirements.json ready for load_bedelia."

    def add_arguments(self, parser):
        parser.add_argument("--subjects", type=Path, required=False, help="Path to credits JSON (list of {codigo,nombre,creditos})")
        parser.add_argument("--posprevias", type=Path, required=False, help="Path to posprevias-by-code JSON")
        parser.add_argument("--requirements", type=Path, required=False, help="Path to requirements tree JSON")
        parser.add_argument("--out-subjects", type=Path, required=True, help="Output path for normalized subjects JSON")
        parser.add_argument("--out-requirements", type=Path, required=True, help="Output path for normalized requirements JSON")
        parser.add_argument("--merge-posprevias", action="store_true", help="Where a course lacks a real tree, synthesize ANY(min=1) from posprevias for both Curso and Examen.")
        parser.add_argument("--verbose", action="store_true")

    def handle(self, *args, **opts):
        subjects_path: Optional[Path] = opts.get("subjects")
        posprev_path: Optional[Path] = opts.get("posprevias")
        reqs_path: Optional[Path] = opts.get("requirements")
        out_subjects: Path = opts["out_subjects"]
        out_requirements: Path = opts["out_requirements"]
        merge_posprevias: bool = bool(opts.get("merge_posprevias"))
        verbose: bool = bool(opts.get("verbose"))

        if not any([subjects_path, posprev_path, reqs_path]):
            raise CommandError("Provide at least one input JSON: --subjects/--posprevias/--requirements")

        data_subjects = self._load_json(subjects_path) if subjects_path else []
        data_posprev = self._load_json(posprev_path) if posprev_path else {}
        data_reqs = self._load_json(reqs_path) if reqs_path else {}

        # Build normalized subjects union
        subj_from_credits = extract_subjects_from_credits(data_subjects)
        subj_from_reqs = extract_subjects_from_requirements(data_reqs)
        subj_from_pos = extract_subjects_from_posprevias(data_posprev)
        subjects_norm = unify_subjects(subj_from_credits, subj_from_reqs, subj_from_pos)

        # Build normalized requirements tree
        reqs_norm = normalize_requirements_tree(data_reqs)

        if merge_posprevias and data_posprev:
            pos_trees = generate_posprevias_offering_nodes(data_posprev)
            # Merge: keep existing real trees; add posprevias trees for missing (Curso/Examen)
            # We identify missing by (code, mode)
            present: Set[Tuple[str, str]] = set()
            for key, obj in reqs_norm.items():
                m = CODE_RE.search(key or "")
                if not m:
                    continue
                present.add((m.group(1), obj.get("name")))
            merged: Dict[str, Any] = {}
            for k_with_mode, v in pos_trees.items():
                m = CODE_RE.search(v.get("code") or "")
                if not m:
                    continue
                tup = (m.group(1), v.get("name"))
                if tup in present:
                    continue
                # Keep key format consistent (without ::mode suffix)
                merged[v["code"]] = v
            # Finally, overlay real trees on top of synthesized ones
            merged.update(reqs_norm)
            reqs_norm = merged

        # Write outputs
        try:
            out_subjects.write_text(json.dumps(subjects_norm, ensure_ascii=False, indent=2), encoding="utf-8")
            out_requirements.write_text(json.dumps(reqs_norm, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            raise CommandError(f"Failed to write outputs: {e}")

        if verbose:
            self.stdout.write(self.style.SUCCESS(
                f"Wrote {len(subjects_norm)} subjects → {out_subjects}\n"
                f"Wrote {len(reqs_norm)} requirement entries → {out_requirements}"
            ))

    def _load_json(self, path: Path):
        try:
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception as e:
            raise CommandError(f"Failed to read {path}: {e}")
            