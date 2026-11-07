/** @odoo-module **/

import {registry} from "@web/core/registry";
import {
    SectionAndNoteFieldOne2Many,
    SectionAndNoteListRenderer,
} from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";

// The request line's visible text column is ``note`` (``name`` is filled from
// the account and hidden), so sections and notes are typed there.
export class DisbursementSectionAndNoteListRenderer extends SectionAndNoteListRenderer {
    setup() {
        super.setup();
        this.titleField = "note";
    }
}

export class DisbursementSectionAndNoteFieldOne2Many extends SectionAndNoteFieldOne2Many {}
DisbursementSectionAndNoteFieldOne2Many.components = {
    ...SectionAndNoteFieldOne2Many.components,
    ListRenderer: DisbursementSectionAndNoteListRenderer,
};

registry
    .category("fields")
    .add(
        "disbursement_section_and_note_one2many",
        DisbursementSectionAndNoteFieldOne2Many
    );
