/** @odoo-module **/

import {ListRenderer} from "@web/views/list/list_renderer";
import {SectionAndNoteFieldOne2Many} from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {registry} from "@web/core/registry";

export class ProjectPlanRenderer extends ListRenderer {
    setup() {
        super.setup();
    }
}
ProjectPlanRenderer.template = "kmitl_project.ListRenderer";

export class ProjectPlan extends SectionAndNoteFieldOne2Many {
    setup() {
        super.setup();
    }
}

ProjectPlan.components = {
    ...X2ManyField.components,
    ListRenderer: ProjectPlanRenderer,
};

registry.category("fields").add("project_plan", ProjectPlan);
