"""SVG validation: parse, structural assertions, sanitize.

This is the gatekeeper for everything Path A produces. It catches malformed
XML from Gemini, strips dangerous elements (script, foreignObject, image,
event handlers), and asserts the structural invariants the rest of the
pipeline relies on (root <svg>, at least one <g id="...">).

Path D (mixed vector + generated raster icons) embeds bitmap icons as
`<image href="data:image/...;base64,...">`. That is normally forbidden — an
`<image>` with an arbitrary href is an SSRF / data-exfil vector. When the
caller passes `allow_data_image=True`, `<image>` is permitted IFF every href
is a base64 `data:` image URI (no http/https/file/relative href ever passes).
See [[docs/progress/260601_path_d_mixed_vector_raster.md]] (H61).
"""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)

FORBIDDEN_TAGS = {
    "script",
    "foreignObject",
    "iframe",
    "embed",
    "object",
    "image",
}

# Only these href schemes are ever allowed on an <image> (and only when the
# caller opts in via allow_data_image). Intentionally strict: base64-encoded
# PNG / JPEG / WebP data URIs only. Anything else — http(s), file, relative
# path, data:text/html, non-base64 data — is rejected.
_SAFE_DATA_IMAGE_RE = re.compile(
    r"^data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=\s]+$"
)

CODE_FENCE_RE = re.compile(
    r"^\s*```(?:svg|xml|html)?\s*\n?(.*?)\n?```\s*$",
    re.DOTALL,
)


class SVGValidationError(ValueError):
    """Raised when generated SVG fails parsing, structural, or safety checks."""


def _strip_code_fence(s: str) -> str:
    m = CODE_FENCE_RE.match(s)
    if m:
        return m.group(1).strip()
    return s.strip()


def _local(tag: str) -> str:
    """Strip XML namespace from a tag like '{http://...}svg' → 'svg'."""
    return tag.rsplit("}", 1)[-1]


def _is_event_attr(attr_name: str) -> bool:
    local = attr_name.rsplit("}", 1)[-1].lower()
    return local.startswith("on")


def _image_href(elem: ET.Element) -> str | None:
    """Return an <image> element's href (plain or xlink), or None if absent."""
    return elem.get("href") or elem.get(f"{{{XLINK_NS}}}href")


def validate_and_canonicalize(raw: str, *, allow_data_image: bool = False) -> str:
    """Validate, sanitize, and re-serialize SVG.

    Returns canonical SVG string. Raises SVGValidationError on any fault.

    When `allow_data_image=True`, `<image>` elements are permitted ONLY if
    every href is a base64 `data:image/...` URI (Path D embeds generated
    raster icons this way). With the default `False`, `<image>` stays
    forbidden outright (Path A / B behaviour, unchanged).
    """
    if not raw or not raw.strip():
        raise SVGValidationError("empty SVG input")

    cleaned = _strip_code_fence(raw)
    if not cleaned:
        raise SVGValidationError("empty SVG after fence strip")

    try:
        root = ET.fromstring(cleaned)
    except ET.ParseError as exc:
        raise SVGValidationError(f"malformed XML: {exc}") from exc

    if _local(root.tag) != "svg":
        raise SVGValidationError(
            f"root element must be <svg>, got <{_local(root.tag)}>"
        )

    for elem in root.iter():
        local = _local(elem.tag)
        if local == "image":
            # <image> is forbidden unless the caller opted in AND the href is a
            # base64 data: image URI. No external/relative href ever passes.
            if not allow_data_image:
                raise SVGValidationError("forbidden element <image>")
            href = _image_href(elem)
            if href is None or not _SAFE_DATA_IMAGE_RE.match(href.strip()):
                raise SVGValidationError(
                    "<image> href must be a base64 data:image/(png|jpeg|webp) URI"
                )
        elif local in FORBIDDEN_TAGS:
            raise SVGValidationError(f"forbidden element <{local}>")
        for attr in list(elem.attrib):
            if _is_event_attr(attr):
                raise SVGValidationError(f"forbidden event attribute {attr}")
        if local == "style" and elem.text and "@import" in elem.text:
            raise SVGValidationError("@import in <style> not allowed")

    has_group_with_id = any(
        _local(e.tag) == "g" and "id" in e.attrib for e in root.iter()
    )
    if not has_group_with_id:
        raise SVGValidationError("no <g id=...> groups present")

    if not root.tag.startswith("{"):
        root.set("xmlns", SVG_NS)

    return ET.tostring(root, encoding="unicode")
