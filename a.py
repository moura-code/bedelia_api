#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

# Change this to the path of your JSON file
JSON_PATH = Path("data/previas_data_backup.json")


# ============================================================
# Helpers to detect "the same course"
# ============================================================

def normalize_title(s: str) -> str:
    """Normalize titles to compare them safely (lowercase, trim, collapse spaces)."""
    if not s:
        return ""
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def is_same_course_item(item: dict, exam_code: str, exam_name: str) -> bool:
    """
    Returns True if this item represents *the same course* as the exam.

    This covers:
      - same code (e.g. exam code 1650 and course code 1650)
      - OR a different code but *same name/title* as the exam (e.g. 1610 vs 1650
        both named "INT. A LA INVESTIGACION DE OPERACIONES").

    Only items with modality "course" or "ucb_module" are treated as "the course".
    """
    modality = item.get("modality")

    if modality not in ("course", "ucb_module"):
        return False

    item_code = item.get("code", "")
    item_title = item.get("title", "")

    # 1) Exact same code
    if item_code == exam_code:
        return True

    # 2) Different code but same name (for old/new codes equivalents like 1610/1650)
    if normalize_title(item_title) == normalize_title(exam_name):
        return True

    return False


# ============================================================
# Core recursive evaluation
# ============================================================

def can_satisfy_without_course(node: dict, exam_code: str, exam_name: str) -> bool:
    """
    Returns True if this requirements subtree can be satisfied
    without *ever* using "the course" (exam_code/exam_name equivalents).

    We are not checking a real student's record here, just whether
    a satisfying assignment exists that doesn't use the course.
    """
    node_type = (node.get("type") or "").upper()

    # ----------------- LEAF -----------------
    if node_type == "LEAF":
        items = node.get("items", [])
        required_count = node.get("required_count", len(items))

        # keep only items that are NOT considered the same course
        non_course_items = [
            it for it in items
            if not is_same_course_item(it, exam_code, exam_name)
        ]

        return len(non_course_items) >= required_count

    # ----------------- ALL ------------------
    elif node_type == "ALL":
        children = node.get("children", [])
        return all(
            can_satisfy_without_course(child, exam_code, exam_name)
            for child in children
        )

    # ----------------- ANY ------------------
    elif node_type == "ANY":
        children = node.get("children", [])
        return any(
            can_satisfy_without_course(child, exam_code, exam_name)
            for child in children
        )

    # ----------------- NOT ------------------
    elif node_type == "NOT":
        # "NOT" means you must NOT have the items inside.
        # There is always an assignment where we simply "don't have them",
        # so from an existence point of view this is always satisfiable
        # without needing the course.
        return True

    # --------------- UNKNOWN ----------------
    else:
        # Be conservative: unknown node types -> treat as unsatisfiable
        return False


# ============================================================
# Main search
# ============================================================

def main():
    # Load JSON
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)["INGENIERÍA EN COMPUTACIÓN_1997"]
        
    with open("data/vigentes_data_backup.json", "r", encoding="utf-8") as f:
        vigentes = json.load(f)["INGENIERÍA EN COMPUTACIÓN_1997"]
    exams_that_dont_require_course = []
    exams_can_without_course = []
    exams_need_course = []

    for key, course in data.items():
        if course.get("type_previas") != "Examen":
            continue  # only look at exam-type entries

        exam_code = course.get("code", "")
        exam_name = course.get("name", "")
        requirements = course.get("requirements")

        vigentes_course = vigentes.get(exam_code)
        if not vigentes_course:
            continue
        course['university_code'] = vigentes_course.get("university_code")
        # No requirements at all → definitely can be done without the course
        if not requirements:
            exams_can_without_course.append(course)
            continue

        if can_satisfy_without_course(requirements, exam_code, exam_name):
            exams_can_without_course.append(course)
        else:
            exams_need_course.append(course)

    # ---------------- Output ----------------
    print("======================================================")
    print("Exams that CAN be taken WITHOUT their own course\n"
          "(considering equivalent codes with the same name as 'the course'):")
    print("======================================================")
    for c in exams_can_without_course:
        print(f"{c.get('code')} - {c.get('name')} - {c.get('university_code')} ")

    print("\n------------------------------------------------------")
    print("Exams that REQUIRE their own course (directly or via equivalent code/name):")
    print("------------------------------------------------------")
 
    print("\nSummary:")
    print(f"  Exams without-course allowed : {len(exams_can_without_course)}")
    print(f"  Exams requiring course       : {len(exams_need_course)}")






if __name__ == "__main__":
    main()