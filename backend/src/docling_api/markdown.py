import re
from pathlib import Path

PROTECTED_START = re.compile(r"^(#{1,6}\s|[-*+]\s|\d+[.)]\s|```|~~~|\||>|!\[|\$\$)")


def canonicalize(markdown: str) -> str:
    text = markdown.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"^(#{1,6})\s*", r"\1 ", text, flags=re.MULTILINE)
    text = re.sub(r"^[*+]\s+", "- ", text, flags=re.MULTILINE)
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    lines = text.splitlines()
    repaired: list[str] = []
    fenced = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            fenced = not fenced
        if (
            repaired
            and stripped
            and repaired[-1].strip()
            and not fenced
            and not PROTECTED_START.match(stripped)
            and not PROTECTED_START.match(repaired[-1].strip())
            and not repaired[-1].rstrip().endswith((".", "!", "?", ":", ";", "  "))
            and stripped[0].islower()
        ):
            repaired[-1] = repaired[-1].rstrip() + " " + stripped
        else:
            repaired.append(line)
    text = "\n".join(repaired)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    return text


def quality_issues(markdown: str, pages: int | None = None) -> list[str]:
    issues: list[str] = []
    plain = re.sub(r"[`#*_|>\[\]()]", "", markdown).strip()
    if not plain:
        issues.append("empty output")
    if pages and pages >= 3 and len(plain) / pages < 80:
        issues.append("very low extracted text per page")
    if markdown.count("�") > max(5, len(markdown) // 500):
        issues.append("severe replacement-character corruption")
    return issues


def validate(markdown: str, result_dir: Path) -> tuple[str, list[str]]:
    warnings: list[str] = []
    if markdown.count("```") % 2:
        markdown += "\n```\n"
        warnings.append("Closed an unterminated code fence.")
    if re.search(r"(?:[A-Za-z]:\\|file://)", markdown):
        warnings.append("Removed an absolute local path from Markdown.")
        markdown = re.sub(r"(?:file:///)?[A-Za-z]:[\\/][^\s)]+", "", markdown)
    for asset in re.findall(r"!\[[^]]*]\((assets/[^)]+)\)", markdown):
        if not (result_dir / Path(asset)).is_file():
            warnings.append(f"Missing referenced asset: {Path(asset).name}")
    return canonicalize(markdown), warnings
