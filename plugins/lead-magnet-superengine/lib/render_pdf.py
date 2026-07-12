"""render_pdf.py — render an HTML string to a PDF via Playwright chromium."""


def html_to_pdf(html: str, out_path: str) -> str:
    """Render *html* (a string) to a PDF file at *out_path*. Returns out_path."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        page.pdf(path=out_path, format="A4", print_background=True)
        browser.close()
    return out_path
