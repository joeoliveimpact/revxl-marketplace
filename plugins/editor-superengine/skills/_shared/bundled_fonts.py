"""The editor's bundled font registry. No system fonts and no synthesized faces."""
import argparse
import hashlib
import json
import re
from pathlib import Path

FONTS = Path(__file__).resolve().parents[2] / "runtime" / "fonts"
ALIASES = {"Inter Tight": "Inter"}
WEIGHTS = {"Thin": 100, "ExtraLight": 200, "Light": 300, "Regular": 400,
           "Medium": 500, "SemiBold": 600, "Bold": 700, "ExtraBold": 800, "Black": 900}


def faces():
    """Read the registry, rather than maintaining a second list of shipped files."""
    registry = json.loads((FONTS / "VERSION.json").read_text(encoding="utf-8"))
    return [dict(face) for family in registry["families"] for face in family["files"]]


def _range(record):
    w = record["weight"]
    return tuple(w) if isinstance(w, list) else (w, w)


def find(family, weight=400, style="normal"):
    family = str(family).strip()
    return next((r for r in faces() if r["family"] == family and r["style"] == style
                 and _range(r)[0] <= weight <= _range(r)[1]), None)


def nearest(family, weight=400, style="normal"):
    requested = str(family).strip()
    family = ALIASES.get(requested, requested)
    records = faces()
    if not any(r["family"] == family for r in records):
        family = "Inter"
    candidates = [r for r in records if r["family"] == family and r["style"] == style]
    if not candidates:
        candidates = [r for r in records if r["family"] == family and r["style"] == "normal"]
    record = min(candidates, key=lambda r: (abs(weight - max(_range(r)[0], min(weight, _range(r)[1]))), _range(r)[0]))
    served = max(_range(record)[0], min(weight, _range(record)[1]))
    return record, served, requested == record["family"] and served == weight and style == record["style"]


def css_face(family, weight, style, url_prefix="./fonts/"):
    record = find(family, weight, style)
    if record is None:
        raise ValueError(f"The editor has no bundled face for {family} {weight} {style}")
    w = record["weight"]
    weight_css = " ".join(str(n) for n in w) if isinstance(w, list) else str(w)
    return (f'@font-face {{ font-family: "{record["family"]}"; src: url("{url_prefix}{record["file"]}") '
            f'format("woff2"); font-weight: {weight_css}; font-style: {record["style"]}; }}')


def problems():
    try:
        records = faces()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return [f"The bundled font registry could not be read: {exc}"]
    out = []
    names = {r["file"] for r in records}
    for r in records:
        path = FONTS / r["file"]
        if not path.is_file():
            out.append(f'The bundled font {r["file"]} is missing.')
            continue
        data = path.read_bytes()
        if len(data) != r["bytes"]:
            out.append(f'The bundled font {r["file"]} has the wrong byte size ({len(data)}, expected {r["bytes"]}).')
        if hashlib.sha256(data).hexdigest() != r["sha256"]:
            out.append(f'The bundled font {r["file"]} has the wrong SHA256.')
    for path in sorted(FONTS.iterdir()):
        if path.is_file() and path.suffix.lower() in (".woff2", ".woff", ".ttf", ".otf") and path.name not in names:
            out.append(f'The font {path.name} is not listed in the bundled font registry.')
    return out


def parse_font(value):
    if isinstance(value, dict):
        return {"family": str(value.get("family", "Inter")).strip(),
                "weight": int(value.get("weight", 400)), "style": value.get("style", "normal")}
    text = str(value or "Inter").strip()
    style = "italic" if re.search(r"\bItalic\b", text, re.I) else "normal"
    text = re.sub(r"\bItalic\b", "", text, flags=re.I).strip()
    weight = 400
    for word, number in sorted(WEIGHTS.items(), key=lambda item: -len(item[0])):
        match = re.search(r"\b" + word + r"\b", text, re.I)
        if match:
            weight = number
            text = (text[:match.start()] + text[match.end():]).strip()
            break
    match = re.search(r"(?<!\S)(\d+)(?!\S)", text)
    if match:
        weight = int(match.group(1))
        text = (text[:match.start()] + text[match.end():]).strip()
    return {"family": re.sub(r"\s+", " ", text) or "Inter", "weight": weight, "style": style}


def selftest():
    assert not problems(), problems()
    assert len(faces()) == 20
    assert find("Montserrat", 900, "italic")["file"] == "Montserrat-Variable-Italic.woff2"
    assert find(" Inter ", 800)["file"] == "Inter-ExtraBold.woff2"
    assert find("inter", 800) is None and find("Inter Tight", 800) is None
    r, w, exact = nearest("Inter Tight", 800)
    assert (r["family"], w, exact) == ("Inter", 800, False)
    r, w, exact = nearest("Comic Sans MS", 400)
    assert (r["file"], w, exact) == ("Inter-Regular.woff2", 400, False)
    assert nearest("Inter", 650)[1:] == (600, False)
    assert nearest("Montserrat", 650, "italic")[1:] == (650, True)
    assert 'font-weight: 100 900;' in css_face("Montserrat", 900, "italic")
    assert 'font-weight: 800;' in css_face("Inter", 800, "normal")
    for value, wanted in (("Montserrat Black Italic", ("Montserrat", 900, "italic")),
                          ("Inter Tight ExtraBold", ("Inter Tight", 800, "normal")),
                          ("Montserrat 650 Italic", ("Montserrat", 650, "italic")),
                          ("Inter 800", ("Inter", 800, "normal")), ("Inter", ("Inter", 400, "normal"))):
        assert tuple(parse_font(value).values()) == wanted
    assert parse_font({"family": " Inter ", "weight": 700, "style": "italic"}) == \
        {"family": "Inter", "weight": 700, "style": "italic"}
    for word, weight in WEIGHTS.items():
        assert parse_font("Inter " + word)["weight"] == weight
    for weight in (100, 101, 650, 899, 900):
        font = parse_font(f"Montserrat {weight} Italic")
        assert nearest(**font)[1:] == (weight, True)
    assert parse_font("Montserrat 950")["weight"] == 950  # callers can reject an out-of-range request
    try:
        css_face("Arial", 400, "normal")
    except ValueError:
        pass
    else:
        raise AssertionError("A CSS face must be bundled")
    print("bundled_fonts selftest: 20 font files verified; all checks passed")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    raise SystemExit(selftest() if args.selftest else 0)
