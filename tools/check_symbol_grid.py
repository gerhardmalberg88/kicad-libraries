"""Check KiCad symbol placement coordinates against a 50 mil grid."""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import sys
from typing import Iterator


GRID = Decimal("1.27")
GRAPHIC_TYPES = {"arc", "bezier", "circle", "polyline", "rectangle", "text", "text_box"}
POINT_TYPES = {"at", "center", "end", "mid", "start", "xy"}
TOKEN_PATTERN = re.compile(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+')

SExpr = str | list["SExpr"]


class ParseError(ValueError):
    """Raised when a KiCad S-expression cannot be parsed."""


def parse_sexpr(content: str) -> list[SExpr]:
    tokens = TOKEN_PATTERN.findall(content)
    position = 0

    def parse_list() -> list[SExpr]:
        nonlocal position
        if position >= len(tokens) or tokens[position] != "(":
            raise ParseError("expected '('")
        position += 1
        result: list[SExpr] = []
        while position < len(tokens) and tokens[position] != ")":
            if tokens[position] == "(":
                result.append(parse_list())
            else:
                result.append(tokens[position])
                position += 1
        if position >= len(tokens):
            raise ParseError("unterminated list")
        position += 1
        return result

    root = parse_list()
    if position != len(tokens):
        raise ParseError("unexpected trailing tokens")
    return root


def child_lists(node: list[SExpr], head: str | None = None) -> Iterator[list[SExpr]]:
    for child in node:
        if isinstance(child, list) and (head is None or (child and child[0] == head)):
            yield child


def descendants(node: list[SExpr], head: str | None = None) -> Iterator[list[SExpr]]:
    for child in child_lists(node):
        if head is None or (child and child[0] == head):
            yield child
        yield from descendants(child, head)


def atom(node: list[SExpr], index: int) -> str:
    value = node[index]
    if not isinstance(value, str):
        raise ParseError(f"expected atom in {node!r}")
    return value


def unquote(value: str) -> str:
    return value[1:-1] if value.startswith('"') and value.endswith('"') else value


def on_grid(value: str) -> bool:
    try:
        return Decimal(value) % GRID == 0
    except InvalidOperation as error:
        raise ParseError(f"invalid coordinate {value!r}") from error


def is_hidden(node: list[SExpr]) -> bool:
    return any(
        len(item) >= 2 and item[0] == "hide" and item[1] == "yes"
        for item in descendants(node)
    )


def point_issues(node: list[SExpr], label: str) -> Iterator[tuple[str, str]]:
    for point in descendants(node):
        if not point or point[0] not in POINT_TYPES or len(point) < 3:
            continue
        for axis, value in zip(("x", "y"), (atom(point, 1), atom(point, 2))):
            if not on_grid(value):
                yield f"{label} {point[0]} {axis}", value


def symbol_issues(symbol: list[SExpr]) -> Iterator[tuple[str, str]]:
    for pin in descendants(symbol, "pin"):
        pin_number_node = next(descendants(pin, "number"), None)
        pin_number = unquote(atom(pin_number_node, 1)) if pin_number_node else "?"
        at_node = next(child_lists(pin, "at"), None)
        if at_node is None:
            raise ParseError(f"pin {pin_number} has no at coordinate")
        for axis, value in zip(("x", "y"), (atom(at_node, 1), atom(at_node, 2))):
            if not on_grid(value):
                yield f"pin {pin_number} at {axis}", value
        length_node = next(child_lists(pin, "length"), None)
        if length_node is None:
            raise ParseError(f"pin {pin_number} has no length")
        length = atom(length_node, 1)
        if not on_grid(length):
            yield f"pin {pin_number} length", length

    for prop in child_lists(symbol, "property"):
        property_name = unquote(atom(prop, 1))
        if property_name not in {"Reference", "Value"} or is_hidden(prop):
            continue
        at_node = next(child_lists(prop, "at"), None)
        if at_node is None:
            raise ParseError(f"property {property_name} has no at coordinate")
        for axis, value in zip(("x", "y"), (atom(at_node, 1), atom(at_node, 2))):
            if not on_grid(value):
                yield f"property {property_name} at {axis}", value

    for graphic in descendants(symbol):
        if not graphic or graphic[0] not in GRAPHIC_TYPES:
            continue
        yield from point_issues(graphic, atom(graphic, 0))
        for radius in child_lists(graphic, "radius"):
            value = atom(radius, 1)
            if not on_grid(value):
                yield f"{graphic[0]} radius", value


def check_file(path: Path) -> tuple[int, int]:
    root = parse_sexpr(path.read_text(encoding="utf-8"))
    if not root or root[0] != "kicad_symbol_lib":
        raise ParseError("not a KiCad symbol library")
    symbols = [
        node
        for node in child_lists(root, "symbol")
        if len(node) >= 2
    ]
    issue_count = 0
    for symbol in symbols:
        symbol_name = unquote(atom(symbol, 1))
        for label, value in symbol_issues(symbol):
            issue_count += 1
            print(
                f"{path}: {symbol_name}: {label}={value} is not on the {GRID} mm (50 mil) grid",
                file=sys.stderr,
            )
    if issue_count == 0:
        print(f"{path}: PASS ({len(symbols)} symbols)")
    return len(symbols), issue_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="KiCad .kicad_sym files to check")
    args = parser.parse_args()

    issue_count = 0
    try:
        for path in args.paths:
            _, issues = check_file(path)
            issue_count += issues
    except (OSError, ParseError) as error:
        print(f"grid check failed: {error}", file=sys.stderr)
        return 2
    return 1 if issue_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
