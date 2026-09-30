/** @odoo-module **/

import {openPhotoViewer} from "@agx_photoviewer/js/photoviewer";
import {isEventHandled} from "@mail/utils/utils";
import {registerPatch} from "@mail/model/model_core";

/**
 * Whether the photo viewer takes over `attachment` from the native mail
 * viewer: every stored file, except links and files of a channel (which
 * needs a route we do not use).
 */
function isOpenable(attachment) {
    return Boolean(
        attachment &&
            !attachment.isUploading &&
            attachment.type !== "url" &&
            (attachment.accessToken ||
                attachment.originThread?.model !== "mail.channel")
    );
}

function openInPhotoViewer(attachmentList, attachment) {
    if (!isOpenable(attachment)) {
        return false;
    }
    const toPlain = (record) => ({
        id: record.id,
        name: record.displayName || "",
        mimetype: record.mimetype,
        accessToken: record.accessToken,
    });
    openPhotoViewer(
        attachmentList.attachments.filter(isOpenable).map(toPlain),
        toPlain(attachment)
    );
    return true;
}

// Show the zoom cursor on every attachment the viewer opens.
registerPatch({
    name: "Attachment",
    fields: {
        isViewable: {
            compute() {
                return this._super() || isOpenable(this);
            },
        },
    },
});

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
