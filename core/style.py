# 색상 팔레트
DEFAULT_COLORS = {
    " 빨간색": "#FF968A",
    " 주황색": "#FFAD60",
    " 노란색": "#F4D980",
    " 초록색": "#B2FBA5",
    " 파란색": "#A9CBD7",
    " 보라색": "#C4BEE2",
}

COLORS = {
    "red-300": "#FF968A",
    "red-400": "#FFC0CC",
    "red-500": "#F44336",
    "red-700": "#D32F2F",
    "green-500": "#4CAF50",
    "blue-300": "#E3F2FD",
    "blue-500": "#2196F3",
    "blue-600": "#A6DAF4",
    "blue-700": "#1976D2",
    "black-300": "#202124",
    "c13": "#131313",
    "c33": "#333333",
    "c77": "#777777",
    "c80": "#808080",
    "c9E": "#9E9E9E",
    "c99": "#999999",
    "cCC": "#CCCCCC",
    "cDD": "#DDDDDD",
    "cF0": "#F0F0F0",
    "cF5": "#F5F5F5",
    "cFA": "#FAFAFA",
    "black": "#000000",
    "white": "#FFFFFF",
    "red": "#FF0000",
    "green": "#00FF00",
    "blue": "#0000FF",
    "gray": "#808080",
    "transparent": "transparent",
}

BORDER_STYLES = {"b", "bb", "solid", "dashed", "dotted", "double", "none"}

STYLES = {
    "rounded": "border-radius: 4px;",
    "rounded-5": "border-radius: 5px;",
    "rounded-lg": "border-radius: 8px;",
    "rounded-xl": "border-radius: 12px;",
    "border": "border-width: 1px;",
    "font-bold": "font-weight: bold;",
    "text-windowtext": "color: palette(window-text);",
    "line-through": "text-decoration: line-through;",
    "no-underline": "text-decoration: none;",
}


def hex_to_rgba(hex_code, opacity_pct):
    if hex_code == "transparent":
        return "transparent"

    hex_code = hex_code.lstrip("#")
    if len(hex_code) == 6:
        r = int(hex_code[0:2], 16)
        g = int(hex_code[2:4], 16)
        b = int(hex_code[4:6], 16)
        a = int(opacity_pct) / 100.0  # 50 -> 0.5
        return f"rgba({r}, {g}, {b}, {a})"

    return f"#{hex_code}"


def parse_color(c: str, prefix, css_prop):
    if not c.startswith(prefix):
        return None

    rest = c[len(prefix) :]

    # 투명도가 없는 기본 색상인 경우 (예: blue-500)
    if rest in COLORS:
        return f"{css_prop}: {COLORS[rest]};"

    # 투명도가 포함된 경우 (예: blue-500-50)
    if "-" in rest:
        color_name, opacity_str = rest.rsplit("-", 1)

        if color_name in COLORS and opacity_str.isdigit():
            rgba_val = hex_to_rgba(COLORS[color_name], opacity_str)
            return f"{css_prop}: {rgba_val};"

    return None


def tw(*classes: str):
    """사용법: widget.setStyleSheet(tw("bg-blue-500", "text-white", "rounded", "p-2"))"""

    style = []

    for c in classes:
        # Parsing Color
        if c.startswith("bg-"):
            parsed = parse_color(c, "bg-", "background-color")
            if parsed:
                style.append(parsed)

        elif c.startswith("text-"):
            if c[5:].isdigit():
                style.append(f"font-size: {c[5:]}px;")
            else:
                parsed = parse_color(c, "text-", "color")
                if parsed:
                    style.append(parsed)

        elif c.startswith("border-"):
            val = c[7:]
            if val.isdigit():
                style.append(f"border-width: {val}px;")

            # 스타일 처리 (border-solid, border-dashed 등)
            elif val in BORDER_STYLES:
                if val == "b":
                    style.append("border: 1px solid;")
                elif val == "bb":
                    style.append("border-bottom: 1px solid;")
                else:
                    style.append(f"border-style: {val};")

            # 색상 처리 (나머지는 색상으로 간주하고 parse_color로 넘김)
            else:
                parsed = parse_color(c, "border-", "border-color")
                if parsed:
                    style.append(parsed)

        # Gridline
        elif c.startswith("grid-"):
            parsed = parse_color(c, "grid-", "gridline-color")
            if parsed:
                style.append(parsed)

        # Padding (p-, px-, py-, pt-, pb-, pl-, pr-)
        elif c.startswith("p-"):
            val = c.split("-")[1]
            style.append(f"padding: {val}px;")
        elif c.startswith("px-"):
            val = c.split("-")[1]
            style.append(f"padding-left: {val}px; padding-right: {val}px;")
        elif c.startswith("py-"):
            val = c.split("-")[1]
            style.append(f"padding-top: {val}px; padding-bottom: {val}px;")
        elif c.startswith("pt-"):
            val = c.split("-")[1]
            style.append(f"padding-top: {val}px;")
        elif c.startswith("pr-"):
            val = c.split("-")[1]
            style.append(f"padding-right: {val}px;")
        elif c.startswith("pb-"):
            val = c.split("-")[1]
            style.append(f"padding-bottom: {val}px;")
        elif c.startswith("pl-"):
            val = c.split("-")[1]
            style.append(f"padding-left: {val}px;")

        # Margin (m-, mx-, my-, mt-, mb-, ml-, mr-)
        elif c.startswith("m-"):
            val = c.split("-")[1]
            style.append(f"margin: {val}px;")
        elif c.startswith("mx-"):
            val = c.split("-")[1]
            style.append(f"margin-left: {val}px; margin-right: {val}px;")
        elif c.startswith("my-"):
            val = c.split("-")[1]
            style.append(f"margin-top: {val}px; margin-bottom: {val}px;")
        elif c.startswith("mt-"):
            val = c.split("-")[1]
            style.append(f"margin-top: {val}px;")
        elif c.startswith("mr-"):
            val = c.split("-")[1]
            style.append(f"margin-right: {val}px;")
        elif c.startswith("mb-"):
            val = c.split("-")[1]
            style.append(f"margin-bottom: {val}px;")
        elif c.startswith("ml-"):
            val = c.split("-")[1]
            style.append(f"margin-left: {val}px;")

        # Width and Height
        elif c.startswith("h-"):
            style.append(f"height: {c[2:]}px;")
        elif c.startswith("w-"):
            style.append(f"width: {c[2:]}px;")

        else:
            style.append(STYLES.get(c, ""))

    return " ".join(style)


def tw_sheet(rules: dict) -> str:
    """
    선택자와 Tailwind 클래스들을 딕셔너리로 받아 QSS를 생성합니다.
    tw_sheet({
        "QMenu": ["bg-white", "p-5", "border-1"], # 배열 형식 가능
        "QMenu::item": "py-6 px-20 no-underline" # 띄어쓰기도 가능
    })
    """
    qss_lines = []

    for selector, classes in rules.items():
        # 1. 단일 문자열이면 리스트로 분할
        if isinstance(classes, str):
            classes = classes.split()

        # 2. tw로 파싱
        properties = tw(*classes)

        # 3. QSS 반환
        qss_lines.append(f"{selector} {{ {properties} }}")

    return "\n".join(qss_lines)
