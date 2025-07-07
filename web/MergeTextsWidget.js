import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

const TypeSlot = {
    Input: 1,
    Output: 2,
};

const TypeSlotEvent = {
    Connect: true,
    Disconnect: false,
};

const _PREFIX = "text";
const _TYPE = "STRING";
const _COLOR_OFF = "#666666";

app.registerExtension({
    name: "AstroCorp.MergeTextsWidget",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "MergeTextsNode") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            onNodeCreated?.apply(this, arguments);

            this.addInput(_PREFIX, _TYPE);

            const slot = this.inputs[this.inputs.length - 1];

            if (slot) {
                slot.color_off = _COLOR_OFF;
            }

            this.setSize(this.computeSize(this.size));
            this.setDirtyCanvas(true, false);

            if (!this.textarea) {
                const textareaWidget = ComfyWidgets.STRING(this, "text", ["STRING", {multiline: true}], app);
                this.textarea = textareaWidget.widget;

                this.textarea.inputEl.placeholder = "Result...";
                this.textarea.inputEl.readOnly = true;
            }
        }

        const onConnectionsChange = nodeType.prototype.onConnectionsChange
        nodeType.prototype.onConnectionsChange = function (slotType, slot_idx, event, link_info, node_slot) {
            const me = onConnectionsChange?.apply(this, arguments);

            if (slotType === TypeSlot.Input) {
                if (link_info && event === TypeSlotEvent.Connect) {
                    // Obtenemos el nodo padre del link (el nodo que está a la izquierda)
                    const fromNode = this.graph._nodes.find((otherNode) => otherNode.id == link_info.origin_id);

                    if (fromNode) {
                        // Aseguramos que haya un padre para el link
                        const parent_link = fromNode.outputs[link_info.origin_slot];
                        const only_one_input = this.inputs.filter(input => input.name.startsWith(_PREFIX)).length === 1;

                        if (parent_link) {
                            node_slot.type = parent_link.type;
                            node_slot.name =  `${_PREFIX}_${only_one_input ? '1' : ''}`;
                        }
                    }
                } else if (event === TypeSlotEvent.Disconnect) {
                    this.removeInput(slot_idx);
                }

                // Rastreamos cada nombre de slot para poder indexar los únicos
                let idx = 0;
                let slot_tracker = {};

                for(const slot of this.inputs) {
                    if (slot.link === null) {
                        this.removeInput(idx);
                        continue;
                    }

                    idx += 1;

                    const name = slot.name.split('_')[0];

                    // Incrementamos el contador en slot_tracker
                    let count = (slot_tracker[name] || 0) + 1;

                    slot_tracker[name] = count;

                    // Actualizamos el nombre del slot con el contador si es mayor que 1
                    slot.name = `${name}_${count}`;
                }

                // Verificamos que el último slot sea dinámico
                let last = this.inputs[this.inputs.length - 1];

                if (last === undefined || (last.name != _PREFIX || last.type != _TYPE)) {
                    this.addInput(_PREFIX, _TYPE);

		            // Establecemos el slot sin conexión en gris
                    last = this.inputs[this.inputs.length - 1];

                    if (last) {
                        last.color_off = _COLOR_OFF;
                    }
                }

                this?.graph?.setDirtyCanvas(true);

                return me;
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
