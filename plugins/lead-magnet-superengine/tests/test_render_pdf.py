import pathlib
import jinja2
import jinja2.sandbox
from lib import render_pdf, qc_pdf

def test_html_to_pdf_creates_nonempty_pdf(tmp_path):
    out = tmp_path / "x.pdf"
    render_pdf.html_to_pdf("<h1>Hello</h1>", str(out))
    assert out.exists() and out.stat().st_size > 0

def test_field_guide_template_renders(tmp_path):
    template_path = pathlib.Path(__file__).parent.parent / "templates" / "field-guide.html.j2"
    env = jinja2.sandbox.SandboxedEnvironment(loader=jinja2.FileSystemLoader(str(template_path.parent)))
    tmpl = env.get_template("field-guide.html.j2")
    ctx = {
        "title": "Test Guide",
        "brand_color": "#123456",
        "hero_image": "",
        "sections": [
            {
                "heading": "Section One",
                "lead": "Intro text.",
                "eyebrow": "Eyebrow",
                "dark": False,
                "paper": False,
                "blocks": [
                    {"type": "paragraph", "content": "A paragraph block."},
                    {"type": "card", "heading": "Card Title", "rows": [{"label": "Key", "value": "Val"}]},
                    {"type": "pull", "content": "A pull quote.", "attribution": "Someone"},
                    {"type": "faq", "items": [{"q": "Question asked?", "a": "Answer given."}]},
                    {"type": "cta", "label": "Click Here", "sublabel": "Now", "url": "#"},
                ],
            }
        ],
    }
    output = tmpl.render(**ctx)
    assert "Test Guide" in output
    assert "A paragraph block." in output
    assert "Card Title" in output
    assert "A pull quote." in output
    assert "Question asked?" in output
    assert "Click Here" in output
    assert "01" in output  # guards zfill page-number filter

def test_qc_reports_page_count(tmp_path):
    out = tmp_path / "x.pdf"
    render_pdf.html_to_pdf("<h1>Hi</h1>", str(out))
    rep = qc_pdf.check(str(out))
    assert rep["pages"] >= 1
    assert rep["ok"] is True
