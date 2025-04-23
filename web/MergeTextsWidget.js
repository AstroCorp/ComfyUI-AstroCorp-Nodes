import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "AstroCorp.MergeTextsWidget",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "MergeTextsNode") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            onNodeCreated?.apply(this, arguments);

            this.setSize(this.computeSize(this.size));
            this.setDirtyCanvas(true, false);

            if (!this.textarea) {
                const textareaWidget = ComfyWidgets.STRING(this, "text", ["STRING", {multiline: true}], app);
                this.textarea = textareaWidget.widget;

                this.textarea.inputEl.placeholder = "Result...";
                this.textarea.inputEl.readOnly = true;
            }
        }

        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function(texts) {
            const hasText = Array.isArray(texts?.string) ? texts?.string.some(text => text.length > 0) : texts?.string.length > 0;
            
            if (hasText) {
                this.textarea.inputEl.value = texts?.string;
            }

            onExecuted?.apply(this, arguments);
        };
    }
});
