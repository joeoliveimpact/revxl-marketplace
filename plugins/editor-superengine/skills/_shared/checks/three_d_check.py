"""Pre-render 3D capture and protected head-band checks (standard library only)."""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

P = Path(__file__).resolve().parents[3]
SCENES = P / "scenes"
sys.path.insert(0, str(P / "skills/reel-canvas-build/scripts"))
import placer  # noqa: E402
import three_d_placement  # noqa: E402

PHASE = "pre"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
NAMED_COLOURS = set("""aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue
blueviolet brown burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan
darkblue darkcyan darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen
darkorange darkorchid darkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey
darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite
forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey honeydew hotpink
indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral
lightcyan lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen
lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime limegreen linen magenta
maroon mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue
mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin
navajowhite navy oldlace olive olivedrab orange orangered orchid palegoldenrod palegreen paleturquoise
palevioletred papayawhip peachpuff peru pink plum powderblue purple rebeccapurple red rosybrown royalblue
saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue slategray slategrey snow
springgreen steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow yellowgreen""".split())


class CaptureHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.elements, self.styles = [], [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        parent = self.stack[-1] if self.stack else None
        skip = "data-no-capture" in attrs or bool(parent and parent["skip"])
        node = dict(tag=tag, attrs=attrs, skip=skip,
                    capture=not skip and ("data-capture" in attrs or bool(parent and parent["capture"])))
        self.elements.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self.stack and self.stack[-1]["tag"] == "style":
            self.styles.append(data)


def _matches(selector, node):
    """The contract's selector subset; match the last compound of descendants.

    Tokenize attributes first so spaces inside quoted attribute values do not
    become combinators. No browser, CSS package or computed style is needed.
    """
    parts = re.findall(r'\[[^\]]*\]|[^\s>+~\[\]]+|[\s>+~]+', selector.strip())
    compound = ""
    for part in parts:
        if re.fullmatch(r'[\s>+~]+', part):
            compound = ""
        else:
            compound += part
    tokens = re.findall(r'\[[^\]]*\]|[#.]?[\w-]+|\*', compound)
    if not tokens or "".join(tokens) != compound:
        return False
    attrs = node["attrs"]
    for token in tokens:
        if token.startswith("#"):
            if attrs.get("id") != token[1:]:
                return False
        elif token.startswith("."):
            if token[1:] not in (attrs.get("class") or "").split():
                return False
        elif token.startswith("["):
            match = re.fullmatch(r'\[\s*([\w-]+)\s*(?:=\s*["\']?([^"\']*?)["\']?\s*)?\]', token)
            if not match or match[1] not in attrs or (match[2] is not None and attrs[match[1]] != match[2]):
                return False
        elif token != "*" and token.lower() != node["tag"]:
            return False
    return True


def _gradients(css):
    for match in re.finditer(r'(?:repeating-)?(?:linear|radial|conic)-gradient\s*\(', css, re.I):
        depth, end = 1, match.end()
        while end < len(css) and depth:
            depth += (css[end] == "(") - (css[end] == ")")
            end += 1
        yield css[match.end():end - 1]


def _faint(gradient):
    for colour in re.finditer(r'(?:rgba?|hsla?)\s*\(([^)]*)\)', gradient, re.I):
        fields = re.split(r'\s*[,/]\s*', colour[1].strip())
        alpha = fields[-1] if len(fields) == 4 or "/" in colour[1] else None
        if alpha is not None:
            try:
                if float(alpha.rstrip("%")) / (100 if alpha.endswith("%") else 1) < 0.15:
                    return True
            except ValueError:
                pass
    return any(int(m[1][-2:], 16) / 255 < 0.15 for m in re.finditer(r'#([0-9a-f]{8})\b', gradient, re.I))


def _literal_colour(value):
    value = re.sub(r'\s*!important\s*$', '', value.strip(), flags=re.I).lower()
    if value in NAMED_COLOURS or re.fullmatch(r'#(?:[\da-f]{3}|[\da-f]{4}|[\da-f]{6}|[\da-f]{8})', value):
        return True
    match = re.fullmatch(r'(rgb|hsl)a?\(([^()]*)\)', value)
    if not match:
        return False
    body = match[2]
    if "," in body:
        fields = [part.strip() for part in body.split(",")]
    else:
        fields = body.replace("/", " ").split()
    if len(fields) not in (3, 4):
        return False
    number = r'[+-]?(?:\d*\.\d+|\d+\.?\d*)'
    patterns = ([number + r'%', number + r'%'] if match[1] == "hsl" else [number + r'%?', number + r'%?'])
    patterns.insert(0, number + (r'(?:deg|grad|rad|turn)?' if match[1] == "hsl" else r'%?'))
    if len(fields) == 4:
        patterns.append(number + r'%?')
    return all(re.fullmatch(pattern, field) for pattern, field in zip(patterns, fields))


def capture_problems(html_text):
    """Return one diagnostic per element/rule, excluding no-capture subtrees."""
    doc = CaptureHTML()
    doc.feed(html_text)
    css = re.sub(r'/\*.*?\*/', '', "\n".join(doc.styles), flags=re.S)
    rules = [(sel.strip(), body) for selectors, body in re.findall(r'([^{}]+)\{([^{}]*)\}', css)
             for sel in re.split(r',\s*(?![^\[]*\])', selectors)]
    problems = []
    for node in doc.elements:
        if not node["capture"]:
            continue
        attrs = node["attrs"]
        name = "#" + attrs["id"] if attrs.get("id") else node["tag"] + "".join(
            "." + c for c in (attrs.get("class") or "").split())
        sources = [(sel, body) for sel, body in rules if _matches(sel, node)]
        sources.append(("inline style", attrs.get("style") or ""))
        combined = ";".join(body for _, body in sources)
        thin = any(float(m[1]) < 4 for m in re.finditer(
            r'(?:^|;)\s*(?:width|height)\s*:\s*([\d.]+)px\b', combined, re.I))
        for source, body in sources:
            faults = []
            if re.search(r'var\s*\(', body, re.I):
                faults.append("uses var() instead of literal colours")
            if re.search(r'\btransparent\b', body, re.I):
                faults.append("uses the transparent keyword")
            gradients = list(_gradients(body))
            if gradients and thin:
                faults.append("puts a gradient on a dimension smaller than 4px")
            if any(_faint(g) for g in gradients):
                faults.append("has a gradient colour stop below 0.15 alpha")
            problems.extend(f"{name} ({source}): {fault}" for fault in faults)
        if "scene" in (attrs.get("class") or "").split():
            colours = re.findall(r'(?:^|;)\s*background-color\s*:\s*([^;]+)', combined, re.I)
            if not any(_literal_colour(c) for c in colours):
                problems.append(f"{name}: captured scene needs an explicit literal background-color")
    return list(dict.fromkeys(problems))


def region_problems(reel_ctx, beat, spec, head_box, number=1):
    """Resolve the real envelope against eyes and mouth, never suggest a blocked place."""
    params = beat.get("scene", {}).get("params") or {}
    place = params.get("place", spec["params"]["place"]["default"])
    clear = three_d_placement.clear_places(spec, head_box)
    if place not in clear:
        if not clear:
            return [f"This shot is too tight for the 3D card on beat {number}."]
        return [f"The 3D card would cover your eyes or mouth on beat {number}."]
    return []


def region_advice(spec, head_box):
    clear = three_d_placement.clear_places(spec, head_box)
    if clear:
        return (f'On the Beat Map, set the 3D card\'s "place" to "{clear[0]}" on that beat, then Send.')
    return 'On the Beat Map, open that beat and press "Remove scene", or pick another card.'


def run(ctx):
    rows = []
    placement, placement_error, loaded = None, False, False
    for number, beat in enumerate(ctx.get("beats") or [], 1):
        scene = beat.get("scene") or {}
        sid = scene.get("id")
        if not isinstance(sid, str) or Path(sid).name != sid:
            continue
        try:
            spec = json.loads((SCENES / sid / "scene.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if spec.get("category") != "3d":
            continue

        def add(check, level, msg, advice=None):
            row = dict(check=check, level=level, msg=msg, where=f"Beat {beat.get('id', '?')}")
            if ctx.get("fps") is not None and ctx["fps"] > 0:
                row["at"] = float(beat.get("start_f", 0) / ctx["fps"])
            if advice is not None:
                row["advice"] = advice
            rows.append(row)

        params = scene.get("params") or {}
        valid_place = True
        for param in ("place", "mode"):
            declaration = spec["params"][param]
            value = params.get(param, declaration["default"])
            if value not in declaration["enum"]:
                add("3d-fill", "block", "Choose the top or bottom band for the 3D card." if param == "place" else
                    "Choose automatic, WebGL or CSS rendering for the 3D card.")
                if param == "place":
                    valid_place = False
        for slot, declaration in spec["slots"].items():
            value = (scene.get("slots") or {}).get(slot, declaration["default"])
            if not isinstance(value, str) or len(value) > declaration["maxChars"]:
                add("3d-fill", "block", f"Shorten the 3D card text to {declaration['maxChars']} characters or fewer.")
        try:
            problems = capture_problems((SCENES / sid / "scene.html").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            problems = ["unreadable"]
        if problems:
            add("3d-capture", "block", "The 3D card design cannot be captured cleanly. Use literal colours, solid thin edges "
                "and visible gradient stops, and give captured scene panels an explicit background colour.")
        if not loaded:
            loaded = True
            try:
                placement = dict(placer.load_ctx(ctx["reel_dir"]), beats=ctx.get("beats") or [])
            except Exception:
                placement_error = True
        try:
            if placement_error:
                raise ValueError("placement unavailable")
            head = placer.visible_head_box_at(placement, beat["start_f"], beat["end_f"] - 1)
        except Exception:
            add("3d-head-band", "warn", "The face position could not be checked yet, so the card's spot cannot be confirmed. "
                "Refresh the face and framing information and check again.")
            continue
        if head is None:
            if not placer.speaker_spans(placement, beat["start_f"], beat["end_f"] - 1):
                continue
            add("3d-head-band", "warn", "The face position isn't known yet, so the card's spot can't be confirmed. "
                "Check its position against the speaker before rendering.")
        elif valid_place:
            for problem in region_problems(ctx, beat, spec, head, number):
                add("3d-head-band", "block", problem, region_advice(spec, head))
    return rows
