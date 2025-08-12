/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";

// Helper: حوّل {field: value} إلى {default_field: normalizedValue}
function toDefaultsContext(values) {
    const ctx = {};
    for (const [name, val] of Object.entries(values)) {
        // many2one في الـ list state بتبقى غالبًا [id, display_name]
        if (Array.isArray(val) && val.length >= 1 && typeof val[0] === "number") {
            ctx[`default_${name}`] = val[0];
        } else if (typeof val === "string" || typeof val === "number" || typeof val === "boolean") {
            ctx[`default_${name}`] = val;
        }
        // تجاهل الأنواع المعقدة (one2many/many2many/objects) عشان ما تعملش أوامر غير مقصودة
    }
    return ctx;
}

patch(ListRenderer.prototype, {
    setup() {
        super.setup();
        console.log("Tree Copy Last Line: ListRenderer patched");
    },

    add(params = {}) {
        const list = this.props.list;
        let defaultsCtx = {};

        try {
            // استخراج السجل الأخير من الـ Tree View
            const last = list?.records?.length ? list.records[list.records.length - 1] : null;

            if (last && last.data) {
                const fieldsToSkip = new Set([
                    "id", "display_name", "__last_update", "create_date", "write_date",
                    "create_uid", "write_uid", "__domain", "__context", "sequence"
                ]);

                const valuesToCopy = {};
                for (const [field, value] of Object.entries(last.data)) {
                    if (fieldsToSkip.has(field)) continue;
                    if (value === false || value === null || value === undefined) continue;

                    if (Array.isArray(value) || ["string", "number", "boolean"].includes(typeof value)) {
                        valuesToCopy[field] = value;
                    }
                }

                defaultsCtx = toDefaultsContext(valuesToCopy);
            }
        } catch (err) {
            console.warn("Tree Copy Last Line: failed to build defaults context:", err);
        }

        const nextParams = {
            ...params,
            context: {
                ...(params?.context || {}),
                ...defaultsCtx,
            },
        };

        console.log("Tree Copy Last Line: calling super.add with defaults", nextParams.context);
        return super.add(nextParams);
    },

    onCellKeydown(ev, group = null, record = null) {
        if (ev.key === "Tab") {
            console.log("Tree Copy Last Line: Tab pressed");
        }
        return super.onCellKeydown(ev, group, record);
    },
});

console.log("Tree Copy Last Line: Module JavaScript loaded");
