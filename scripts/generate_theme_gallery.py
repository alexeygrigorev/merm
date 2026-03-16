#!/usr/bin/env python3
"""Generate theme gallery SVGs for docs/themes.md.

Renders a representative flowchart, sequence diagram, and class diagram
in all four built-in themes (default, dark, forest, neutral).

Usage:
    uv run scripts/generate_theme_gallery.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from merm import render_diagram
from merm.theme import THEMES

THEMES_DIR = Path(__file__).parent.parent / "docs" / "themes"

DIAGRAMS: dict[str, str] = {
    "flowchart": """\
flowchart TD
    A[Start] --> B{Decision?}
    B -->|Yes| C[Do something]
    B -->|No| D[Do something else]
    C --> E[End]
    D --> E
""",
    "sequence": """\
sequenceDiagram
    participant Alice
    participant Bob
    Alice->>Bob: Hello Bob!
    Bob-->>Alice: Hi Alice!
    Alice->>Bob: How are you?
    Bob-->>Alice: Great, thanks!
""",
    "class": """\
classDiagram
    class Animal {
        +String name
        +int age
        +makeSound()
    }
    class Dog {
        +String breed
        +fetch()
    }
    class Cat {
        +bool indoor
        +purr()
    }
    Animal <|-- Dog
    Animal <|-- Cat
""",
}


def main() -> None:
    THEMES_DIR.mkdir(parents=True, exist_ok=True)

    ok = 0
    fail = 0

    for theme_name in THEMES:
        for diagram_name, source in DIAGRAMS.items():
            out_path = THEMES_DIR / f"{diagram_name}_{theme_name}.svg"
            try:
                svg = render_diagram(source, theme=theme_name)
                out_path.write_text(svg, encoding="utf-8")
                print(f"  OK: {out_path.name}")
                ok += 1
            except Exception as e:
                print(f"  FAIL: {out_path.name}: {e}")
                fail += 1

    print(f"\nGenerated {ok} gallery SVGs ({fail} failures) in {THEMES_DIR}/")
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
