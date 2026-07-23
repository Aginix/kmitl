/** @odoo-module **/

import {ListRenderer} from "@web/views/list/list_renderer";
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {registry} from "@web/core/registry";

/**
 * Editable allocation list grouped by recipient. Records are displayed sorted by
 * partner so each recipient's rows stay contiguous even after a new line is
 * appended locally (the server _order only re-applies on reload). A section
 * header precedes each recipient's first row; a footer under each group offers
 * "เพิ่มรายการ", which adds a row with the recipient pre-filled so the name is
 * not re-entered. Standard embedded o2m can't group_by (StaticList), so the
 * headers/footers are injected in an overridden rows template.
 */
export class AllocationGroupedRenderer extends ListRenderer {
    /** Records ordered by recipient (then sequence) for display. */
    get displayRecords() {
        const partnerId = (r) => (r.data.partner_id ? r.data.partner_id[0] : 0);
        return [...this.props.list.records].sort(
            (a, b) =>
                partnerId(a) - partnerId(b) ||
                (a.data.sequence || 0) - (b.data.sequence || 0)
        );
    }

    /**
     * Recipient label to render as a section header before `record`
     * (its group's first row), or a falsy value otherwise.
     */
    getGroupHeader(record) {
        const records = this.displayRecords;
        const index = records.indexOf(record);
        const currentId = record.data.partner_id ? record.data.partner_id[0] : false;
        if (index > 0) {
            const previous = records[index - 1].data.partner_id;
            const previousId = previous ? previous[0] : false;
            if (currentId === previousId) {
                return false;
            }
        }
        return record.data.partner_id
            ? record.data.partner_id[1]
            : "(ยังไม่ระบุผู้รับเงิน)";
    }

    /**
     * The recipient `[id, name]` when `record` is the last row of its group (so
     * the per-group "add line" footer renders after it), or false otherwise.
     * Only groups with a recipient get a footer.
     */
    getGroupFooter(record) {
        const records = this.displayRecords;
        const index = records.indexOf(record);
        const partner = record.data.partner_id;
        const currentId = partner ? partner[0] : false;
        if (!currentId) {
            return false;
        }
        if (index < records.length - 1) {
            const next = records[index + 1].data.partner_id;
            if ((next ? next[0] : false) === currentId) {
                return false;
            }
        }
        return partner;
    }

    /** Add an allocation row with the recipient pre-filled. */
    addLineForPartner(partnerId) {
        this.add({context: {default_partner_id: partnerId}});
    }
}
AllocationGroupedRenderer.rowsTemplate = "agx_approval.AllocationGrouped.Rows";

export class AllocationGrouped extends X2ManyField {}
AllocationGrouped.components = {
    ...X2ManyField.components,
    ListRenderer: AllocationGroupedRenderer,
};

registry.category("fields").add("allocation_grouped", AllocationGrouped);
