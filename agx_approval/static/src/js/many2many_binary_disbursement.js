/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2ManyBinaryField } from "@web/views/fields/many2many_binary/many2many_binary_field";

/**
 * Disbursement-evidence variant of the many2many_binary widget.
 *
 * The upload route (/web/binary/upload_attachment) creates every attachment
 * with res_model='approval.request' and res_id=<request id> — identical for the
 * plan attachments (attachment_ids, a res_id One2many) and the disbursement
 * evidence (disbursement_attachment_ids). Without a discriminator the freshly
 * uploaded evidence file matches the plan's One2many and shows up under the plan
 * attachments until the record is saved.
 *
 * Stamp `is_disbursement_evidence=True` on the uploaded attachment immediately
 * (before it is linked / the form re-reads), so the plan One2many — whose domain
 * excludes evidence — never picks it up.
 */
export class Many2ManyBinaryDisbursementField extends Many2ManyBinaryField {
    async onFileUploaded(files) {
        const ids = files.filter((file) => file.id && !file.error).map((file) => file.id);
        if (ids.length) {
            await this.orm.write("ir.attachment", ids, {
                is_disbursement_evidence: true,
            });
        }
        return super.onFileUploaded(files);
    }
}

registry
    .category("fields")
    .add("many2many_binary_disbursement", Many2ManyBinaryDisbursementField);
