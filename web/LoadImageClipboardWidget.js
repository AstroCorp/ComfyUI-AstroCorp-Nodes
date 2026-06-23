import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const IMAGE_WIDGET_NAME = "image";

function getImageExtension(type) {
    if (type === "image/jpeg") return "jpg";
    if (type === "image/webp") return "webp";
    if (type === "image/gif") return "gif";
    if (type === "image/bmp") return "bmp";

    return "png";
}

function getTimestamp() {
    const now = new Date();
    const pad = (value) => String(value).padStart(2, "0");

    return [
        now.getFullYear(),
        pad(now.getMonth() + 1),
        pad(now.getDate()),
        "_",
        pad(now.getHours()),
        pad(now.getMinutes()),
        pad(now.getSeconds()),
    ].join("");
}

async function readClipboardImage() {
    if (!navigator.clipboard?.read) {
        throw new Error("This browser does not allow reading images from the clipboard.");
    }

    const clipboardItems = await navigator.clipboard.read();

    for (const item of clipboardItems) {
        const imageType = item.types.find((type) => type.startsWith("image/"));

        if (imageType) {
            return {
                blob: await item.getType(imageType),
                type: imageType,
            };
        }
    }

    throw new Error("No image was found in the clipboard.");
}

async function readPastedImage(event) {
    const data = event.clipboardData || window.clipboardData;
    const items = Array.from(data?.items ?? []);
    const imageItem = items.find((item) => item.type.startsWith("image/"));

    if (!imageItem) {
        throw new Error("No image was found in the clipboard.");
    }

    const blob = imageItem.getAsFile();

    if (!blob) {
        throw new Error("Could not read the pasted image.");
    }

    return {
        blob,
        type: blob.type || imageItem.type,
    };
}

function waitForPastedImage() {
    return new Promise((resolve, reject) => {
        const timeout = window.setTimeout(() => {
            document.removeEventListener("paste", onPaste, true);
            reject(new Error("No pasted image was received."));
        }, 30000);

        const onPaste = async (event) => {
            try {
                const image = await readPastedImage(event);

                event.preventDefault();
                event.stopImmediatePropagation();
                window.clearTimeout(timeout);
                document.removeEventListener("paste", onPaste, true);

                resolve(image);
            } catch (error) {
                window.clearTimeout(timeout);
                document.removeEventListener("paste", onPaste, true);

                reject(error);
            }
        };

        document.addEventListener("paste", onPaste, true);
    });
}

async function uploadImageBlob(blob, type) {
    const extension = getImageExtension(type);
    const filename = `clipboard_${getTimestamp()}.${extension}`;
    const file = new File([blob], filename, { type });
    const formData = new FormData();

    formData.append("image", file);
    formData.append("type", "input");

    const response = await api.fetchApi("/upload/image", {
        method: "POST",
        body: formData,
    });

    if (!response.ok) {
        throw new Error(`Could not upload the clipboard image (${response.status}).`);
    }

    return await response.json();
}

async function uploadClipboardImage() {
    try {
        const { blob, type } = await readClipboardImage();

        return await uploadImageBlob(blob, type);
    } catch (error) {
        alert("The browser blocked direct clipboard access. Press Ctrl+V now to paste the image.");

        const { blob, type } = await waitForPastedImage();

        return await uploadImageBlob(blob, type);
    }
}

function getUploadedImagePath(uploadResult) {
    if (!uploadResult.subfolder) return uploadResult.name;

    const subfolder = uploadResult.subfolder.replaceAll("\\", "/").replace(/\/?$/, "/");

    return `${subfolder}${uploadResult.name}`;
}

function setImageWidgetValue(node, value) {
    const imageWidget = node.widgets?.find((widget) => widget.name === IMAGE_WIDGET_NAME);

    if (!imageWidget) return;

    const values = imageWidget.options?.values;

    if (Array.isArray(values) && !values.includes(value)) {
        values.push(value);
    }

    imageWidget.value = value;

    if (typeof imageWidget.callback === "function") {
        imageWidget.callback(value);
    }
}

app.registerExtension({
    name: "AstroCorp.LoadImageClipboardWidget",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "LoadImageClipboardNode") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);

            const useClipboardImage = async () => {
                try {
                    const uploadResult = await uploadClipboardImage();

                    setImageWidgetValue(this, getUploadedImagePath(uploadResult));
                    
                    this.setSize(this.computeSize(this.size));
                    this.setDirtyCanvas(true, true);
                } catch (error) {
                    alert(error.message ?? error);
                }
            };

            if (typeof this.addWidget === "function") {
                this.addWidget(
                    "button",
                    "Use clipboard image",
                    null,
                    useClipboardImage
                );
            }

            this.setSize(this.computeSize(this.size));
            this.setDirtyCanvas(true, false);
        };
    },
});
