import logging

from markupsafe import Markup, escape

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """``introduction`` turned from Text into Html (same ``text`` column).
    Convert the existing plain text so its line breaks survive: one ``<p>``
    per line, leading spaces kept as ``&nbsp;``."""
    if not version:
        return
    cr.execute(
        # Every value is still plain text: the field was Text until now.
        "SELECT id, introduction FROM kmitl_project WHERE introduction IS NOT NULL"
    )
    rows = cr.fetchall()
    for project_id, text in rows:
        paragraphs = []
        for line in text.replace("\r", "").rstrip("\n").split("\n"):
            stripped = line.lstrip(" ")
            content = Markup("&nbsp;") * (len(line) - len(stripped)) + escape(stripped)
            paragraphs.append("<p>%s</p>" % (content or "<br>"))
        cr.execute(
            "UPDATE kmitl_project SET introduction = %s WHERE id = %s",
            ("".join(paragraphs), project_id),
        )
    _logger.info("kmitl_project: converted %s introductions to HTML", len(rows))
