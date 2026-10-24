# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import base64
import io
import re
import zipfile
from collections import Counter

import xlrd
import xlsxwriter
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import clean_context

from odoo.addons.base.models.res_bank import sanitize_account_number

# Template columns, in order.
STUDENT, AMOUNT, BANK, ACCOUNT, NATIONAL_ID, DESCRIPTION = range(6)


def _cell_text(cell):
    """A cell as text; a number typed into a text column loses its ``.0``."""
    if cell is None:
        return ""
    if cell.ctype == xlrd.XL_CELL_NUMBER:
        value = cell.value
        return str(int(value)) if float(value).is_integer() else str(value)
    if cell.ctype == xlrd.XL_CELL_TEXT:
        return cell.value.strip()
    return ""


def _cell_amount(cell):
    if cell is None:
        return 0.0
    if cell.ctype == xlrd.XL_CELL_NUMBER:
        return cell.value
    try:
        return float(_cell_text(cell).replace(",", "") or 0.0)
    except ValueError:
        return 0.0


def _valid_thai_id(vat):
    """13 digits whose last one is the checksum of the first twelve."""
    if not re.fullmatch(r"\d{13}", vat):
        return False
    total = sum(int(vat[i]) * (13 - i) for i in range(12))
    return (11 - total % 11) % 10 == int(vat[12])


class DisbursementStudentImport(models.TransientModel):
    """A student list import: one request line per ready row of the
    requester's Excel file, appended to a draft student-type request.

    Checked first (nothing written), then imported. A requester can neither
    create contacts nor write bank accounts, so the import writes those under
    sudo — only for someone who may edit this draft request, never deleting
    or overwriting anything already on a contact.
    """

    _name = "disbursement.student.import"
    _description = "Import Students into a Disbursement Request"

    request_id = fields.Many2one(
        "disbursement.request",
        string="Disbursement Request",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(related="request_id.company_id")
    product_id = fields.Many2one(
        "product.product",
        string="Expense Item",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    file = fields.Binary(string="Excel File", attachment=False)
    filename = fields.Char()
    state = fields.Selection(
        [("upload", "Upload"), ("preview", "Preview")],
        default="upload",
        required=True,
    )
    line_ids = fields.One2many(
        "disbursement.student.import.line",
        "wizard_id",
        string="Rows",
    )
    count_ready = fields.Integer(compute="_compute_summary", string="Ready")
    count_warning = fields.Integer(compute="_compute_summary", string="With Warnings")
    count_skip = fields.Integer(compute="_compute_summary", string="Skipped")
    amount_ready = fields.Float(compute="_compute_summary", string="Amount to Import")

    @api.depends("line_ids.status", "line_ids.amount")
    def _compute_summary(self):
        for wizard in self:
            ready = wizard.line_ids.filtered(lambda r: r.status != "skip")
            wizard.count_ready = len(ready)
            wizard.count_warning = len(ready.filtered(lambda r: r.status == "warning"))
            wizard.count_skip = len(wizard.line_ids) - len(ready)
            wizard.amount_ready = sum(ready.mapped("amount"))

    # -------------------------------------------------------------------------
    # Template
    # -------------------------------------------------------------------------
    @api.model
    def _template_xlsx(self):
        """The import template: fixed columns, text-formatted codes (so leading
        zeros survive) and the bank picked from the banks known to Odoo."""
        buffer = io.BytesIO()
        book = xlsxwriter.Workbook(buffer, {"in_memory": True})
        sheet = book.add_worksheet(_("Students"))
        head = book.add_format({"bold": True, "bg_color": "#D9E1F2", "border": 1})
        text = book.add_format({"num_format": "@"})
        money = book.add_format({"num_format": "#,##0.00"})
        sheet.write_row(
            0,
            0,
            [
                _("Student ID"),
                _("Amount"),
                _("Bank"),
                _("Account Number"),
                _("National ID"),
                _("Description"),
            ],
            head,
        )
        sheet.set_column(STUDENT, STUDENT, 16, text)
        sheet.set_column(AMOUNT, AMOUNT, 14, money)
        sheet.set_column(BANK, BANK, 32)
        sheet.set_column(ACCOUNT, ACCOUNT, 20, text)
        sheet.set_column(NATIONAL_ID, NATIONAL_ID, 18, text)
        sheet.set_column(DESCRIPTION, DESCRIPTION, 40)
        sheet.freeze_panes(1, 0)
        names = self.env["res.bank"].search([]).mapped("name")
        if names:
            banks = book.add_worksheet("Banks")
            banks.write_column(0, 0, names)
            banks.hide()
            sheet.data_validation(
                1,
                BANK,
                1000,
                BANK,
                {"validate": "list", "source": "=Banks!$A$1:$A$%d" % len(names)},
            )
        book.close()
        return buffer.getvalue()

    def action_download_template(self):
        return {
            "type": "ir.actions.act_url",
            "url": "/disbursement_student_import/template",
            "target": "new",
        }

    # -------------------------------------------------------------------------
    # Check
    # -------------------------------------------------------------------------
    def _check_request(self):
        request = self.request_id
        if request.state != "draft" or not request.is_student_payee:
            raise UserError(
                _("Students can only be imported into a draft request paying students.")
            )
        request.check_access_rights("write")
        request.check_access_rule("write")
        return request

    def _read_rows(self):
        try:
            book = xlrd.open_workbook(file_contents=base64.b64decode(self.file))
        except (xlrd.XLRDError, zipfile.BadZipFile) as error:
            raise UserError(
                _("Cannot read the file; upload the Excel import template.")
            ) from error
        sheet = book.sheet_by_index(0)
        rows = []
        for rowx in range(1, sheet.nrows):
            cells = [
                sheet.cell(rowx, colx) if colx < sheet.ncols else None
                for colx in range(6)
            ]
            texts = [_cell_text(cell) for cell in cells]
            if not any(texts):
                continue
            rows.append(
                {
                    "row_number": rowx + 1,
                    "student_code": texts[STUDENT],
                    "amount": _cell_amount(cells[AMOUNT]),
                    "bank_name": texts[BANK],
                    "acc_number": texts[ACCOUNT],
                    "vat": re.sub(r"\D", "", texts[NATIONAL_ID]),
                    "description": texts[DESCRIPTION],
                }
            )
        return rows

    def _resolve(self, rows, request):
        """Preview values for ``rows``: each one's student, bank account,
        status and message. Writes nothing; students are matched in one batch
        and only student IDs no contact carries are looked up (in one batch)."""
        Partner = self.env["res.partner"].sudo()
        student_type = self.env.ref("partner_type_kmitl.partner_type_student")
        vat_by_code = {}
        for row in rows:
            code = row["student_code"]
            if code and code not in vat_by_code:
                vat_by_code[code] = row["vat"] if _valid_thai_id(row["vat"]) else None
        partners = Partner._kmitl_student_match(vat_by_code)
        unknown = [code for code in vat_by_code if code not in partners]
        looked_up = Partner._kmitl_student_lookup(unknown) if unknown else {}
        banks = {
            bank.name.strip().lower(): bank for bank in self.env["res.bank"].search([])
        }
        counts = Counter(row["student_code"] for row in rows)
        on_request = set(request.line_ids.partner_id.mapped("student_code"))

        result = []
        for row in rows:
            code = row["student_code"]
            partner = partners.get(code) or Partner
            skip, warn = [], []
            vals = dict(row)
            if not code:
                skip.append(_("No student ID"))
            elif partner:
                vals["student_name"] = partner.name
                if not partner.active:
                    skip.append(_("%s is archived") % partner.display_name)
                elif partner.partner_type_id != student_type:
                    skip.append(_("%s is not a student contact") % partner.display_name)
            elif code in looked_up:
                vals.update(looked_up[code])
                vals["student_name"] = vals.pop("name")
            else:
                skip.append(_("Student ID not found"))
            if row["amount"] <= 0:
                skip.append(_("No amount"))

            # The row's own account (reused if the student has it, else added
            # on import), or the one the student already has.
            accounts = partner.bank_ids.filtered(
                lambda b: not b.company_id or b.company_id == request.company_id
            )
            bank = banks.get(row["bank_name"].lower())
            vals["bank_id"] = bank.id if bank else False
            if row["acc_number"]:
                acc = sanitize_account_number(row["acc_number"])
                account = accounts.filtered(
                    lambda b, acc=acc: b.sanitized_acc_number == acc
                )[:1]
                vals["partner_bank_id"] = account.id
                taken = partner.with_context(active_test=False).bank_ids.mapped(
                    "sanitized_acc_number"
                )
                if not account and acc in taken:
                    skip.append(_("Account is archived or belongs to another company"))
                elif not account and not bank:
                    skip.append(_("Bank of the new account not recognised"))
            elif accounts:
                vals["partner_bank_id"] = accounts[:1].id
            elif "student_name" in vals:
                skip.append(_("No bank account"))

            vat = row["vat"]
            if vat and not _valid_thai_id(vat):
                warn.append(_("National ID %s is not valid and is not saved") % vat)
                vat = ""
            partner_vat = re.sub(r"\D", "", partner.vat or "")
            if vat and partner_vat and vat != partner_vat:
                warn.append(_("National ID differs from the one on record (kept)"))
            if request.has_tax and not vat and not partner_vat:
                warn.append(_("No national ID"))
            vals["vat"] = vat
            if code and (counts[code] > 1 or code in on_request):
                warn.append(_("Student ID appears more than once"))

            vals["partner_id"] = partner.id
            vals["status"] = "skip" if skip else "warning" if warn else "ready"
            vals["message"] = "; ".join(skip + warn)
            result.append(vals)
        return result

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Import Students"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_check(self):
        self.ensure_one()
        request = self._check_request()
        if not self.product_id:
            raise UserError(_("Choose the expense item."))
        if not self.file:
            raise UserError(_("Upload the Excel file."))
        rows = self._read_rows()
        if not rows:
            raise UserError(_("The file has no student rows."))
        self.line_ids = [(5, 0, 0)] + [
            (0, 0, vals) for vals in self._resolve(rows, request)
        ]
        self.state = "preview"
        return self._reopen()

    def action_back(self):
        self.ensure_one()
        self.write({"state": "upload", "line_ids": [(5, 0, 0)]})
        return self._reopen()

    # -------------------------------------------------------------------------
    # Import
    # -------------------------------------------------------------------------
    def action_import(self):
        self.ensure_one()
        # The action's default_* keys must not leak into what is created here.
        self = self.with_context(clean_context(self.env.context))
        request = self._check_request()
        rows = self.line_ids.filtered(lambda r: r.status != "skip").sorted("row_number")
        if not rows:
            raise UserError(_("No row is ready to import."))
        Partner = self.env["res.partner"].sudo()
        Bank = self.env["res.partner.bank"].sudo()
        student_type = self.env.ref("partner_type_kmitl.partner_type_student")
        product = self.product_id
        expense_account = (
            product.property_account_expense_id
            or product.categ_id.property_account_expense_categ_id
        )
        partners, accounts, commands = {}, {}, []
        for row in rows:
            partner = partners.get(row.student_code) or row.partner_id.sudo()
            if not partner:
                partner = Partner.create(
                    {
                        "name": row.student_name,
                        "company_type": "person",
                        "partner_type_id": student_type.id,
                        "student_code": row.student_code,
                        "student_faculty": row.student_faculty,
                        "student_curriculum": row.student_curriculum,
                    }
                )
            partners[row.student_code] = partner
            if not partner.student_code:
                partner.student_code = row.student_code
            if row.vat and not partner.vat:
                partner.vat = row.vat
            account = row.partner_bank_id
            if not account:
                # A new account: the row named its bank and number.
                key = (partner.id, sanitize_account_number(row.acc_number))
                account = accounts.get(key) or Bank.create(
                    {
                        "partner_id": partner.id,
                        "bank_id": row.bank_id.id,
                        "acc_number": row.acc_number,
                        "company_id": request.company_id.id,
                    }
                )
                accounts[key] = account
            commands.append(
                (
                    0,
                    0,
                    {
                        "partner_id": partner.id,
                        "product_id": product.id,
                        "name": row.description or product.display_name,
                        "quantity": 1.0,
                        "price_unit": row.amount,
                        "partner_bank_id": account.id,
                        "account_id": expense_account.id,
                        "analytic_distribution": request.analytic_distribution,
                    },
                )
            )
        request.write({"line_ids": commands})
        request.message_post(body=self._import_note(rows), subtype_xmlid="mail.mt_note")
        return {"type": "ir.actions.act_window_close"}

    def _import_note(self, rows):
        body = Markup("<p>%s</p>") % (
            _("%(count)s students imported from %(file)s, %(amount)s in total.")
            % {
                "count": len(rows),
                "file": self.filename or _("an Excel file"),
                "amount": "{:,.2f}".format(sum(rows.mapped("amount"))),
            }
        )
        skipped = self.line_ids.filtered(lambda r: r.status == "skip")
        if skipped:
            body += Markup("<p>%s</p><ul>%s</ul>") % (
                _("Rows skipped:"),
                Markup("").join(
                    Markup("<li>%s</li>")
                    % (
                        _("Row %(row)s %(code)s: %(message)s")
                        % {
                            "row": row.row_number,
                            "code": row.student_code or "",
                            "message": row.message,
                        }
                    )
                    for row in skipped
                ),
            )
        return body


class DisbursementStudentImportLine(models.TransientModel):
    """One row of the file, as the preview shows it."""

    _name = "disbursement.student.import.line"
    _description = "Student List Import Row"
    _order = "row_number"

    wizard_id = fields.Many2one(
        "disbursement.student.import",
        required=True,
        ondelete="cascade",
    )
    row_number = fields.Integer(string="Row")
    student_code = fields.Char(string="Student ID")
    student_name = fields.Char(string="Name")
    student_faculty = fields.Char(string="Faculty")
    student_curriculum = fields.Char(string="Curriculum")
    # Empty for a student who gets a contact on import.
    partner_id = fields.Many2one("res.partner", string="Student")
    amount = fields.Float()
    bank_name = fields.Char(string="Bank")
    bank_id = fields.Many2one("res.bank", string="Bank Record")
    acc_number = fields.Char(string="Account Number")
    # Empty for a new account, created on import.
    partner_bank_id = fields.Many2one("res.partner.bank", string="Bank Account")
    vat = fields.Char(string="National ID")
    description = fields.Char()
    status = fields.Selection(
        [("ready", "Ready"), ("warning", "Warning"), ("skip", "Skipped")],
        required=True,
        default="ready",
    )
    message = fields.Char()
