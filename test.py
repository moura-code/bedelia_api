import re
from bs4 import BeautifulSoup

# =============================
# Node type map
# =============================
NODETYPE_MAP = {
    "default": "LEAF",
    "and": "ALL",
    "or": "ANY",
    "not": "NOT"
}

# =============================
# Utility helpers
# =============================

def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()

def is_direct_child(parent_rk: str, child_rk: str) -> bool:
    """Return True if child_rk is exactly one level below parent_rk."""
    if not parent_rk or parent_rk in ("root", ""):
        return "_" not in child_rk
    return child_rk.startswith(parent_rk + "_") and child_rk.count("_") == parent_rk.count("_") + 1

# =============================
# Leaf parsing
# =============================

def _split_code_name(s: str):
    s = s.strip()
    notes = re.findall(r"\(([^)]+)\)", s)
    if notes:
        s = re.sub(r"\([^)]+\)", "", s).strip()

    m = re.match(r"^([A-Z0-9]+)\s*-\s*(.+)$", s, flags=re.I)
    if m:
        return m.group(1).strip().upper(), m.group(2).strip(), notes

    m2 = re.match(r"^([A-Z0-9]+)\b(.*)$", s, flags=re.I)
    if m2:
        return m2.group(1).strip().upper(), m2.group(2).strip(" -:"), notes

    return None, s, notes


def parse_item_line(line: str, prefix: str):
    """Parse one textual item line (Examen/Course/UCB) into a structured dict."""
    original = line.strip()
    low = original.lower()

    # Default modality
    modality = "unknown"

    if "examen de la u.c.b" in low:
        modality = "exam"
        body = re.sub(r"(?i)^examen\s+de\s+la\s+u\.c\.b:\s*", "", original).strip()
    elif "curso de la u.c.b" in low:
        modality = "course"
        body = re.sub(r"(?i)^curso\s+de\s+la\s+u\.c\.b:\s*", "", original).strip()
    elif re.search(r"(?i)u\.c\.b\s+aprobad[ao]:", original):
        modality = "ucb_module"
        body = re.sub(r"(?i)^u\.c\.b\s+aprobad[ao]:\s*", "", original).strip()
    else:
        body = original

    code, title, notes = _split_code_name(body)

    return {
        "source": "UCB",
        "modality": modality,  # exam | course | ucb_module | unknown
        "code": code,
        "title": title,
        "notes": notes,
        "raw": original
    }


def extract_items_from_leaf_structured(td):
    """Extracts structured items and count from a leaf <td>."""
    label_el = td.select_one(".ui-treenode-label")
    if not label_el:
        return {"required_count": 0, "items": []}

    full_text = label_el.get_text("\n", strip=True)
    bold = label_el.select_one(".negrita")
    prefix = bold.get_text(" ", strip=True) if bold else ""
    rest = full_text.replace(prefix, "", 1).strip()

    required_count = 1
    m = re.search(r"(\d+)\s+aprobaci[oó]n/es?", prefix, flags=re.I)
    if m:
        required_count = int(m.group(1))

    lines = [l for l in (x.strip() for x in rest.split("\n")) if l]
    items = [parse_item_line(line, prefix) for line in lines]

    return {"required_count": required_count, "items": items}

# =============================
# Recursive tree parsing
# =============================

def parse_treenode(td):
    """Recursively parse a <td data-nodetype> tree node into JSON."""
    parent_rk = td.get("data-rowkey", "root")
    nodetype = td.get("data-nodetype", "default")
    kind = NODETYPE_MAP.get(nodetype, "LEAF")

    title_el = td.select_one(".ui-treenode-label")
    title = clean_text(title_el.get_text(" ", strip=True)) if title_el else ""

    # --- Leaf nodes ---
    if kind == "LEAF":
        leaf = extract_items_from_leaf_structured(td)
        leaf["title"] = title
        return leaf

    # --- Composite nodes ---
    children = []
    container = td.find_next_sibling("td", class_="ui-treenode-children-container")
    if container:
        for tbl in container.select("> .ui-treenode-children > table"):
            row = tbl.select_one("> tbody > tr")
            if not row:
                continue
            # top-level cells only
            for c in row.find_all("td", recursive=False):
                if not c.has_attr("data-nodetype"):
                    continue
                child_rk = c.get("data-rowkey", "")
                if not is_direct_child(parent_rk, child_rk):
                    continue
                children.append(parse_treenode(c))

    return {"type": kind, "title": title, "children": children}

# =============================
# Entry point
# =============================

def parse_tree(html: str):
    soup = BeautifulSoup(html, "html.parser")
    root_td = soup.select_one("td[data-nodetype]")
    if not root_td:
        raise ValueError("No treenode found in HTML.")
    return parse_treenode(root_td)
