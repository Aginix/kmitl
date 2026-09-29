/** @odoo-module **/

import {isPreviewable, openPhotoViewer} from "@agx_photoviewer/js/photoviewer";
import {isEventHandled} from "@mail/utils/utils";
import {registerPatch} from "@mail/model/model_core";

/**
 * Open `attachment` in the photo viewer instead of the native mail viewer.
 * Returns false when the attachment must be left to the native behaviour.
 */
function openInPhotoViewer(attachmentList, attachment) {
    if (
        !attachment ||
        attachment.isUploading ||
        (!attachment.accessToken && attachment.originThread?.model === "mail.channel")
    ) {
        return false;
    }
    const toPlain = (record) => ({
        id: record.id,
        name: record.displayName || "",
        mimetype: record.mimetype,
        accessToken: record.accessToken,
    });
    const current = toPlain(attachment);
    if (!isPreviewable(current)) {
        return false;
    }
    openPhotoViewer(
        attachmentList.attachments.filter((record) => !record.isUploading).map(toPlain),
        current
    );
    return true;
}

registerPatch({
    name: "AttachmentImage",
    recordMethods: {
        onClickImage(ev) {
            const isActionClick =
                isEventHandled(ev, "AttachmentImage.onClickDownload") ||
                isEventHandled(ev, "AttachmentImage.onClickUnlink");
            if (
                !isActionClick &&
                openInPhotoViewer(this.attachmentList, this.attachment)
            ) {
                return;
            }
            this._super(ev);
        },
    },
});

registerPatch({
    name: "AttachmentCard",
    recordMethods: {
        onClickImage() {
            if (openInPhotoViewer(this.attachmentList, this.attachment)) {
                return;
            }
            this._super(...arguments);
        },
    },
});
