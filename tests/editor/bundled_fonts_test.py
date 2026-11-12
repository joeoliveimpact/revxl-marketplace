"""Bundled-only build gate: shipped pages, caption looks and native review aids."""
import ast
import importlib.util
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "plugins/editor-superengine"
sys.path.insert(0, str(P / "skills/_shared"))
sys.path.insert(0, str(P / "scripts"))
import bundled_fonts
import scene_check


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def page_problems(path):
    return scene_check.font_problems(str(path), path.read_text(encoding="utf-8"))


def native_references(path):
    """Native helpers pass a bundled file directly, rather than using a CSS family."""
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str) or not node.value.lower().endswith((".woff2", ".woff", ".ttf", ".otf")):
            continue
        ancestor = node
        while ancestor in parents and not isinstance(parents[ancestor], ast.Call):
            ancestor = parents[ancestor]
        call = parents.get(ancestor)
        copied_output = (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                         and call.func.attr in ("copyfile", "copy2", "copy") and len(call.args) > 1
                         and ancestor is call.args[1])
        assert copied_output or node.value.startswith("runtime/fonts/"), f"{path}: font outside runtime/fonts: {node.value}"
    refs = re.findall(r'[\"\']([^\"\']*runtime/fonts/[^\"\']+\.(?:woff2|woff|ttf|otf))[\"\']', text)
    assert refs, f"{path}: no bundled font reference found"
    records = {r["file"]: r for r in bundled_fonts.faces()}
    for ref in refs:
        assert ref.startswith("runtime/fonts/"), f"{path}: font outside runtime/fonts: {ref}"
        record = records.get(ref.removeprefix("runtime/fonts/"))
        assert record and bundled_fonts.find(record["family"], 400, "normal") == record, (path, ref)
    # Browser helper aliases are local names for that exact file, not system fonts.
    for family in re.findall(r'fontFamily\s*:\s*[\"\']([^\"\']+)[\"\']', text):
        assert bundled_fonts.find(family) or re.search(r'new FontFace\([\"\']' + re.escape(family) + r'[\"\']', text), (path, family)
    for family in re.findall(r'font-family\s*:\s*([^;}]+)', text):
        assert all(bundled_fonts.find(f.strip().strip("\"'")) for f in family.split(",")), (path, family)
    for weight in re.findall(r'fontWeight\s*:\s*[\"\'](\d+)[\"\']', text):
        assert all(bundled_fonts.find(r["family"], int(weight), "normal") == r for r in records.values() if r["file"] in {Path(x).name for x in refs}), (path, weight)


def main():
    assert bundled_fonts.problems() == [], bundled_fonts.problems()
    pages = sorted((P / "scenes").glob("*/scene.html"))
    pages += [P / "skills/reel-canvas-build/templates/render/index.html"]
    pages += sorted((P / "skills/editor-doctor/selftest/compositions").glob("*.html"))
    for page in pages:
        assert not page_problems(page), page_problems(page)
    captions = load("captions_font_gate", P / "skills/reel-captions/scripts/captions.py")
    for name, look in captions.STYLES.items():
        font = look["font"]
        assert bundled_fonts.find(**font), (name, font)
        style = captions.check_style({"style": name})
        doc = {"style": style, "font": font, "chunks": [], "notes": []}
        css, markup, _ = captions.layer(doc, [], 1, str)
        problems = scene_check.font_problems("look-" + name, '<style>' + css + '</style>' + '\n'.join(markup))
        assert not problems, problems
    for path in (P / "skills/reel-cover/scripts/cover_pick.py", P / "skills/_shared/checks/review_aids.py"):
        native_references(path)
    # Regression fixtures live in a temporary folder and go through the same gate as shipped pages.
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        normal = bundled_fonts.css_face("Inter", 400, "normal")
        cases = {
            "missing-heavy": normal + 'body {font-family: "Inter"; font-weight: 900;}',
            "system-family": normal + 'body {font-family: "Arial";}',
            "local-source": '@font-face {font-family: "Inter"; src: local("Inter"), url("./fonts/Inter-Regular.woff2"); font-weight: 400; font-style: normal;} body {font-family: "Inter";}',
            "wrong-descriptor": normal.replace("font-weight: 400", "font-weight: 900") + 'body {font-family: "Inter"; font-weight: 900;}',
            "missing-italic": normal + 'body {font-family: "Inter";} span {font-style: italic;}',
            "inline-heavy": normal + 'body {font-family: "Inter";}',
            "generated-heavy": normal + 'body {font-family: "Inter";} .generated {font-weight: 900;}',
            "important-heavy": normal + 'body {font-family: "Inter";} span {font-weight: 900 !important;}',
        }
        for name, css in cases.items():
            path = root / (name + ".html")
            inline = (' style="font-weight:900"' if name == "inline-heavy" else
                      ' style="font-weight:400"' if name == "important-heavy" else "")
            path.write_bytes((f'<style>{css}</style><body><span{inline}>Sample</span></body>').encode("utf-8"))
            assert page_problems(path), f"negative fixture passed: {name}"
        # Real heavy and variable italic declarations are legal when the page covers their use.
        for family, weight, style in (("Inter", 900, "normal"), ("Montserrat", 850, "italic")):
            css = bundled_fonts.css_face(family, weight, style)
            css += f'body {{font-family:"{family}";font-weight:{weight};font-style:{style};}}'
            assert not scene_check.font_problems("positive", f'<style>{css}</style><body>Sample</body>')
    print(f"bundled_fonts_test: {len(pages)} render templates, {len(captions.STYLES)} looks, 2 native helpers; negative fixtures refused")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
