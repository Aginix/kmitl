/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";
import {escape, sprintf} from "@web/core/utils/strings";
import {registry} from "@web/core/registry";

/**
 * Renderers open non-image files inside the viewer modal; files without a
 * matching renderer show an "unsupported" message. Other modules add
 * entries here: {match(attachment) => bool, render(attachment, page)}.
 * `render` replaces the content of `page` (which shows a spinner until
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

// The modal can be resized freely down to this size.
const MIN_WIDTH = 280;
const MIN_HEIGHT = 180;

// Height of the thumbnail strip; keep in sync with $thumbnail-strip-height.
const THUMBNAIL_STRIP_HEIGHT = 68;

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

export function getRenderer(attachment) {
    return photoviewerRenderers.getAll().find((renderer) => renderer.match(attachment));
}

const unsupportedRenderer = {
    render(attachment, page) {
        const type = attachment.mimetype || getExtension(attachment);
        page.innerHTML = `<div class="m-auto text-center p-3 text-muted">${escape(
            sprintf(_t("Preview is not supported for file type %s"), type)
        )}</div>`;
    },
};

const downloadButton = {
    title: _t("Download"),
    text: DOWNLOAD_ICON,
    click(viewer) {
        const link = document.createElement("a");
        link.href = getUrl(viewer.images[viewer.index].attachment, true);
        link.click();
    },
};

function createThumbnails(viewer) {
    const strip = document.createElement("div");
    strip.className = "o_agx_photoviewer_thumbnails";
    // Clicking or scrolling the strip must not drag the modal.
    for (const type of ["mousedown", "touchstart"]) {
        strip.addEventListener(type, (ev) => ev.stopPropagation(), {passive: true});
    }
    strip.addEventListener(
        "wheel",
        (ev) => {
            if (!ev.deltaX) {
                strip.scrollLeft += ev.deltaY;
                ev.preventDefault();
            }
        },
        {passive: false}
    );
    viewer.images.forEach(({attachment}, index) => {
        const thumbnail = document.createElement("button");
        thumbnail.type = "button";
        thumbnail.className = "o_agx_photoviewer_thumbnail";
        thumbnail.title = attachment.name || "";
        thumbnail.addEventListener("click", () => viewer.jumpTo(index));
        if (isImage(attachment)) {
            const image = document.createElement("img");
            image.loading = "lazy";
            const token = attachment.accessToken
                ? `?access_token=${attachment.accessToken}`
                : "";
            image.src = `/web/image/${attachment.id}/96x96${token}`;
            thumbnail.append(image);
        } else {
            // Icon of the file type, styled by the "o_image" mimetype rules.
            const icon = document.createElement("span");
            icon.className = "o_image";
            icon.dataset.mimetype = attachment.mimetype || "";
            icon.dataset.ext = getExtension(attachment);
            icon.title = attachment.name || "";
            thumbnail.append(icon);
        }
        strip.append(thumbnail);
    });
    return strip;
}

/**
 * Show the item being loaded: images use the native stage, files are rendered
 * into a container placed below the header by their renderer.
 */
function showItem(viewer, state) {
    const item = viewer.images[viewer.index];
    const modal = viewer.$photoviewer;
    if (!state.container) {
        if (viewer.images.length === 1) {
            modal.addClass("o_agx_photoviewer_single");
        }
        if (state.hasFiles) {
            // Keep the size chosen at opening whatever image is shown and
            // let the resize handles go down to the minimum.
            viewer.options.modalWidth = MIN_WIDTH;
            viewer.options.modalHeight = MIN_HEIGHT;
            viewer.isOpened = true;
            viewer.resize = () => {};
        }
        if (viewer.images.length > 1) {
            state.thumbnails = createThumbnails(viewer);
            modal.addClass("o_agx_photoviewer_has_thumbnails");
            modal[0].querySelector(".photoviewer-inner").append(state.thumbnails);
            // The stage size was measured before the strip existed.
            viewer._stageEdgeValue.vertical += THUMBNAIL_STRIP_HEIGHT;
        }
        state.container = document.createElement("div");
        state.container.className = "o_agx_photoviewer_content";
        viewer.$stage[0].after(state.container);
        // Keep the pointer events of the content frozen while dragging or
        // resizing so the mouseup always reaches the document; clicks inside
        // the content itself must still reach it.
        modal.on("mousedown", (ev) => {
            if (state.container.contains(ev.target)) {
                return;
            }
            modal.addClass("o_agx_photoviewer_busy");
            document.addEventListener(
                "mouseup",
                () => modal.removeClass("o_agx_photoviewer_busy"),
                {once: true}
            );
        });
        modal.on("keydown", (ev) => {
            if (ev.key === "Escape") {
                // Keep Odoo's hotkeys from also closing a dialog below.
                ev.stopPropagation();
                viewer.close();
            }
        });
    }
    if (state.thumbnails) {
        for (const [index, thumbnail] of [...state.thumbnails.children].entries()) {
            thumbnail.classList.toggle("active", index === viewer.index);
        }
        state.thumbnails.children[viewer.index].scrollIntoView({
            block: "nearest",
            inline: "center",
        });
    }
    if (!item.renderer) {
        modal.removeClass("o_agx_photoviewer_embed");
        state.container.replaceChildren();
        return;
    }
    modal.addClass("o_agx_photoviewer_embed");
    // Each file renders in its own page: a late render of a file the user
    // already left only touches a detached page.
    const page = document.createElement("div");
    page.className = "o_agx_photoviewer_page";
    page.innerHTML = '<i class="fa fa-spin fa-spinner fa-2x m-auto"></i>';
    state.container.replaceChildren(page);
    Promise.resolve(item.renderer.render(item.attachment, page)).catch((error) => {
        console.error(error);
        page.innerHTML = `<div class="m-auto text-center p-3">${escape(
            _t("This file cannot be previewed.")
        )}</div>`;
    });
}

/**
 * Open `current` in the viewer, navigating through the `attachments` in order.
 */
export function openPhotoViewer(attachments, current) {
    const items = attachments.map((attachment) => ({
        src: isImage(attachment) ? getUrl(attachment) : "",
        title: escape(attachment.name || ""),
        attachment,
        renderer: isImage(attachment)
            ? null
            : getRenderer(attachment) || unsupportedRenderer,
    }));
    const hasFiles = items.some((item) => item.renderer);
    const state = {hasFiles};
    return new window.PhotoViewer(items, {
        index: Math.max(
            items.findIndex((item) => item.attachment.id === current.id),
            0
        ),
        headerToolbar: ["download", "maximize", "close"],
        customButtons: {download: downloadButton},
        // Files need a stable, roomy modal; images alone fit the modal to
        // the picture. The initial size doubles as the minimum size, so it
        // is lowered again in the first `beforeChange`.
        modalWidth: hasFiles ? Math.round(window.innerWidth * 0.7) : MIN_WIDTH,
        modalHeight: hasFiles ? Math.round(window.innerHeight * 0.85) : MIN_HEIGHT,
        fixedModalPos: hasFiles,
        // An iframe would swallow the mouse events of a drag started elsewhere.
        dragHandle: hasFiles ? ".photoviewer-header" : null,
        callbacks: {
            beforeChange(viewer) {
                showItem(viewer, state);
            },
        },
    });
}
