from __future__ import annotations

import re
from pathlib import Path


_SKIP_DIR_PARTS = {".git", "__pycache__", "node_modules", ".venv", "venv", "env"}


def _iter_repo_texts(root: Path) -> list[str]:
    texts: list[str] = []
    for p in root.rglob("*"):
        if p.is_dir():
            continue
        if any(part in _SKIP_DIR_PARTS for part in p.parts):
            continue
        if p.suffix.lower() not in (".py", ".html", ".js", ".txt", ".md", ".css"):
            continue
        texts.append(p.read_text(encoding="utf-8", errors="ignore"))
    return texts


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    urls_path = root / "apps" / "comercial" / "urls.py"
    text = urls_path.read_text(encoding="utf-8", errors="ignore")

    # Parse path('route/', view, name='name')
    path_re = re.compile(
        r"path\(\s*"
        r"(?P<route>r?['\"][^'\"]+['\"])\s*,\s*"
        r"(?P<view>[^,]+)\s*,\s*"
        r"name\s*=\s*['\"](?P<name>[^'\"]+)['\"]\s*"
        r"\)"
    )
    entries: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        if "path(" not in line or "name" not in line:
            continue
        m = path_re.search(line)
        if not m:
            continue
        route_literal = m.group("route")
        route = route_literal.lstrip("r").strip("\"'")
        view = m.group("view").strip()
        name = m.group("name").strip()
        entries.append((route, view, name))

    texts = _iter_repo_texts(root)
    ns_ref = set(re.findall(r"comercial:([A-Za-z0-9_]+)", "\n".join(texts)))

    # Route references show up often as hardcoded '/comercial/<route>...' in JS.
    def route_is_referenced(route: str) -> bool:
        # normalize: strip leading slash from route; urls.py already uses relative routes.
        candidates = [
            f"/comercial/{route}",
            f"comercial/{route}",
        ]
        hay = "\n".join(texts)
        return any(c in hay for c in candidates)

    unused: list[tuple[str, str]] = []
    for route, _view, name in entries:
        used_by_name = name in ns_ref
        used_by_route = route_is_referenced(route)
        if not used_by_name and not used_by_route:
            unused.append((route, name))

    print(f"URL ENTRIES: {len(entries)}")
    print(f"REFERENCED NAMESPACE comercial:* : {len(ns_ref)}")
    print(f"UNUSED (no comercial:name and no /comercial/route): {len(unused)}")
    for route, name in unused:
        print(f"{name}  ->  {route}")


if __name__ == "__main__":
    main()
