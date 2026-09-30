# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging
import os
import subprocess
import tempfile

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Office mimetypes we know LibreOffice can render. Kept in one place so the
# controller and the frontend can agree on what is "previewable" without a
# download.
OFFICE_MIMETYPES = frozenset(
    {
        # MS Office (OOXML)
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        # MS Office (legacy binary)
        "application/msword",
        "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint",
        # OpenDocument
        "application/vnd.oasis.opendocument.text",
        "application/vnd.oasis.opendocument.spreadsheet",
        "application/vnd.oasis.opendocument.presentation",
        # RTF and CSV (soffice handles these too)
        "application/rtf",
        "text/rtf",
        "text/csv",
    }
)

_LIBREOFFICE_BINARIES = ("soffice", "libreoffice")
_LIBREOFFICE_TIMEOUT = 120


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    # Cache of the LibreOffice-converted PDF. Stored in the filestore
    # (attachment=True) so a large deck doesn't bloat the DB row.
    preview_pdf = fields.Binary(attachment=True)
    # Checksum of the source bytes captured when preview_pdf was generated.
    # Compared against the current source checksum to detect a stale cache
    # after the user re-uploads the file.
    preview_pdf_checksum = fields.Char()

    def get_preview_pdf(self):
        """Return raw PDF bytes suitable for inline preview, or None.

        - PDF attachment → its own bytes.
        - Office / ODF attachment → LibreOffice-converted PDF (cached on the
          record; regenerated when the source checksum changes).
        - Anything else → None, meaning the frontend must fall back to a
          download link.
        """
        self.ensure_one()
        if not self.mimetype:
            return None
        if self.mimetype == "application/pdf":
            return self.raw or None
        if self.mimetype not in OFFICE_MIMETYPES:
            return None
        if (
            self.preview_pdf
            and self.preview_pdf_checksum
            and self.preview_pdf_checksum == self.checksum
        ):
            return base64.b64decode(self.preview_pdf)
        pdf_bytes = self._convert_to_pdf_via_libreoffice()
        # sudo so a portal user with read access to a PDF-worthy attachment
        # still gets the cache populated for the next viewer.
        self.sudo().write(
            {
                "preview_pdf": base64.b64encode(pdf_bytes),
                "preview_pdf_checksum": self.checksum,
            }
        )
        return pdf_bytes

    def _convert_to_pdf_via_libreoffice(self):
        """Shell out to LibreOffice headless to convert the attachment to PDF.

        Raises UserError with a clear message on any failure (binary missing,
        non-zero exit, timeout, or no PDF produced) so the caller can surface
        it as a normal Odoo notification instead of a 500."""
        self.ensure_one()
        raw = self.raw
        if not raw:
            raise UserError(
                _("Attachment %s has no content to preview.") % (self.name or self.id)
            )
        binary = self._find_libreoffice_binary()
        with tempfile.TemporaryDirectory(prefix="ac_preview_") as tmpdir:
            src_name = self.name or "attachment"
            src_path = os.path.join(tmpdir, src_name)
            with open(src_path, "wb") as fh:
                fh.write(raw)
            try:
                completed = subprocess.run(
                    [
                        binary,
                        "--headless",
                        "--convert-to",
                        "pdf",
                        "--outdir",
                        tmpdir,
                        src_path,
                    ],
                    check=True,
                    timeout=_LIBREOFFICE_TIMEOUT,
                    capture_output=True,
                )
            except FileNotFoundError as e:
                raise UserError(
                    _(
                        "LibreOffice (%s) is not installed on the server; "
                        "cannot preview %s."
                    )
                    % (binary, src_name)
                ) from e
            except subprocess.TimeoutExpired as e:
                raise UserError(
                    _("LibreOffice timed out while converting %s.") % src_name
                ) from e
            except subprocess.CalledProcessError as e:
                _logger.warning(
                    "soffice convert failed for %s: %s", src_name, e.stderr
                )
                raise UserError(
                    _("LibreOffice failed to convert %s to PDF.") % src_name
                ) from e
            _logger.debug("soffice stdout: %s", completed.stdout)
            pdf_path = os.path.splitext(src_path)[0] + ".pdf"
            if not os.path.exists(pdf_path):
                raise UserError(
                    _("LibreOffice did not produce a PDF for %s.") % src_name
                )
            with open(pdf_path, "rb") as fh:
                return fh.read()

    @staticmethod
    def _find_libreoffice_binary():
        """Prefer `soffice` (canonical name), fall back to `libreoffice`."""
        from shutil import which

        for name in _LIBREOFFICE_BINARIES:
            if which(name):
                return name
        # Return the first name so the FileNotFoundError message stays useful.
        return _LIBREOFFICE_BINARIES[0]
