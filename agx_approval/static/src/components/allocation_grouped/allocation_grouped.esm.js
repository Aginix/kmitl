/** @odoo-module **/

import {ListRenderer} from "@web/views/list/list_renderer";
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {registry} from "@web/core/registry";

/**
 * Editable allocation list that shows a section header row before each
 * recipient's first line (records are ordered by partner_id so each
 * recipient's rows are contiguous). Standard embedded o2m can't group_by,
 * so we inject the header in an overridden rows template instead.
 */
export class AllocationGroupedRenderer extends ListRenderer {
    /**
     * Recipient label to render as a section header before `record`
     * (its group's first row), or a falsy value otherwise.
     */
    getGroupHeader(record) {
        const records = this.props.list.records;
        const index = records.indexOf(record);
        const partner = record.data.partner_id;
        const currentId = partner ? partner[0] : false;
        if (index > 0) {
            const previous = records[index - 1].data.partner_id;
            const previousId = previous ? previous[0] : false;
            if (currentId === previousId) {
                return false;
            }
        }
        return partner ? partner[1] : "(ยังไม่ระบุผู้รับเงิน)";
    }
}
AllocationGroupedRenderer.rowsTemplate = "agx_approval.AllocationGrouped.Rows";

export class AllocationGrouped extends X2ManyField {}
AllocationGrouped.components = {
    ...X2ManyField.components,
    ListRenderer: AllocationGroupedRenderer,
};

registry.category("fields").add("allocation_grouped", AllocationGrouped);
