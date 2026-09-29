/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";
import {escape} from "@web/core/utils/strings";
import {registry} from "@web/core/registry";

/**
 * Renderers open non-image files inside the viewer modal. Other modules add
 * entries here: {match(attachment) => bool, render(attachment, container)}.
 * `render` replaces the content of `container` (which shows a spinner until
 * then); it may return a promise. An attachment is a plain
 * {id, name, mimetype, accessToken} object.
 */
export const photoviewerRenderers = registry.category("agx_photoviewer.renderers");

const IMAGE_MIMETYPES = [
    "image/bmp",
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/svg+xml",
    "image/webp",
];

const DOWNLOAD_ICON =
    '<svg viewBox="0 0 24 24" class="svg-inline-icon">' +
    '<path fill="currentColor" d="M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z"></path></svg>';

export function getExtension(attachment) {
    const match = /\.([^.]+)$/.exec(attachment.name || "");
    return match ? match[1].toLowerCase() : "";
}

export function getUrl(attachment, download = false) {
    const token = attachment.accessToken
        ? `&access_token=${attachment.accessToken}`
        : "";
    return `/web/content/${attachment.id}?download=${download}${token}`;
}

export function isImage(attachment) {
    return IMAGE_MIMETYPES.includes(attachment.mimetype);
}

function getRenderer(attachment) {
    return photoviewerRenderers.getAll().find((renderer) => renderer.match(attachment));
}

export function isPreviewable(attachment) {
    return isImage(attachment) || Boolean(getRenderer(attachment));
}

function downloadButton(getAttachment) {
    return {
        title: _t("Download"),
        text: DOWNLOAD_ICON,
        click(viewer) {
            const link = document.createElement("a");
            link.href = getUrl(getAttachment(viewer), true);
            link.click();
        },
    };
}

function openRenderer(renderer, attachment) {
    return new window.PhotoViewer([{src: "", title: escape(attachment.name || "")}], {
        movable: false,
        keyboard: false,
        fixedModalSize: true,
        modalWidth: Math.round(window.innerWidth * 0.7),
        modalHeight: Math.round(window.innerHeight * 0.85),
        // An iframe would swallow the mouse events of a drag started elsewhere.
        dragHandle: ".photoviewer-header",
        headerToolbar: ["download", "maximize", "close"],
        footerToolbar: [],
        customButtons: {download: downloadButton(() => attachment)},
        callbacks: {
            opened(viewer) {
                const modal = viewer.$photoviewer;
                const container = document.createElement("div");
                container.className = "o_agx_photoviewer_content";
                container.innerHTML =
                    '<i class="fa fa-spin fa-spinner fa-2x m-auto"></i>';
                modal.addClass("o_agx_photoviewer_embed");
                viewer.$stage[0].after(container);
                // Keep the pointer events of the content frozen while dragging
                // or resizing so the mouseup always reaches the document.
                modal.on("mousedown", () => {
                    modal.addClass("o_agx_photoviewer_busy");
                    document.addEventListener(
                        "mouseup",
                        () => modal.removeClass("o_agx_photoviewer_busy"),
                        {once: true}
                    );
                });
                modal.on("keydown", (ev) => ev.key === "Escape" && viewer.close());
                Promise.resolve(renderer.render(attachment, container)).catch(
                    (error) => {
                        console.error(error);
                        container.innerHTML = `<div class="m-auto text-center p-3">${escape(
                            _t("This file cannot be previewed.")
                        )}</div>`;
                    }
                );
            },
        },
    });
}

/**
 * Open `current` in the viewer: files with a registered renderer are shown on
 * their own, images are shown as a gallery with the other images of the list.
 */
export function openPhotoViewer(attachments, current) {
    const renderer = getRenderer(current);
    if (renderer) {
        return openRenderer(renderer, current);
    }
    const images = attachments.filter(isImage);
    return new window.PhotoViewer(
        images.map((image) => ({src: getUrl(image), title: escape(image.name || "")})),
        {
            index: images.findIndex((image) => image.id === current.id),
            headerToolbar: ["download", "maximize", "close"],
            customButtons: {download: downloadButton((viewer) => images[viewer.index])},
        }
    );
}
