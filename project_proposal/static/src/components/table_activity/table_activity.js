/** @odoo-module **/

import {registry} from "@web/core/registry";
import {SectionAndNoteFieldOne2Many} from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";
import {ListRenderer} from "@web/views/list/list_renderer";
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";

export class TableActivityRenderer extends ListRenderer {
    setup() {
        super.setup();
    }
    freezeColumnWidths() {}
    get validPercentage() {
        const total = this.props.list.records.reduce(
            (sum, rec) => sum + rec.data.percentage,
            0
        );
        return total < 100 || total > 100;
    }
    get totalAmount() {
        const total = this.props.list.records.reduce(
            (sum, rec) => sum + (rec.data.amount || 0),
            0
        );
        return new Intl.NumberFormat("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(total);
    }

    get totalPercentage() {
        const total = this.props.list.records.reduce(
            (sum, rec) => sum + (rec.data.percentage || 0),
            0
        );
        return new Intl.NumberFormat("th-TH", {}).format(total);
    }
}
TableActivityRenderer.template = "project_proposal.ListRenderer";
TableActivityRenderer.rowsTemplate = "project_proposal.ListRendererActivity.Rows";

export class Table_activity extends SectionAndNoteFieldOne2Many {
    setup() {
        super.setup();
    }
}

Table_activity.components = {
    ...X2ManyField.components,
    ListRenderer: TableActivityRenderer,
};

registry.category("fields").add("table_activity", Table_activity);
