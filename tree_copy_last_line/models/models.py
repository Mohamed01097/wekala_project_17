# -*- coding: utf-8 -*-
from odoo import models, api, fields


class AutoCopyLastLineMixin(models.AbstractModel):
    """
    Reusable mixin to auto-fill new records with values copied from the
    most recent record ("last line"), both in:
      - normal forms opened from list views (via default_get),
      - inline editable list (tree) views (via create).

    Behavior:
      - Chooses the "last line" constrained by parent M2O defaults if present
        (e.g., default_order_id for one2many), otherwise falls back to the
        last record created by the current user.
      - Copies only safe field types by default (scalars, M2O, M2M, JSON).
      - Skips non-stored computed fields and common technical fields.

    Enable/disable:
      - Context key `copy_last_line` (default: True).
    Customize:
      - Set `__copy_last_line_fields__` in the inheriting model for a whitelist.
    """
    _name = "auto.copy.last.line.mixin"
    _description = "Auto copy last line defaults (form + inline create)"

    # Optional whitelist. If None, a safe auto-selection is used.
    __copy_last_line_fields__ = None

    # -----------------------------
    # Configuration helpers
    # -----------------------------
    def _is_copy_enabled(self):
        """Check if feature is enabled for this request (context flag)."""
        return self.env.context.get("copy_last_line", True)

    def _copy_last_line_domain(self):
        """
        Build a domain to pick the "last line" to copy from:
          - If any `default_<m2o>` is present in context, constrain on it
            (this captures the one2many parent).
          - Else, constrain by `create_uid = current user` (list view fallback).
        """
        ctx = self.env.context
        domain = []
        for name, field in self._fields.items():
            if isinstance(field, fields.Many2one):
                key = f"default_{name}"
                if key in ctx and ctx[key]:
                    domain.append((name, "=", ctx[key]))
        if not domain:
            domain = [("create_uid", "=", self.env.user.id)]
        return domain

    def _fields_to_copy(self):
        """
        Determine fields to be copied.
        If a whitelist is provided on the inheriting model, use it.
        Otherwise select safe field types and skip common technical fields.
        """
        if self.__copy_last_line_fields__:
            return [f for f in self.__copy_last_line_fields__ if f in self._fields]

        skip = {
            "id", "display_name", "__last_update",
            "create_date", "write_date", "create_uid", "write_uid",
            "sequence", "state",
        }
        allowed = []
        for name, field in self._fields.items():
            if name in skip:
                continue
            if isinstance(field, (
                fields.Char, fields.Text, fields.Integer, fields.Float,
                fields.Boolean, fields.Selection, fields.Many2one,
                fields.Many2many, fields.Json
            )):
                allowed.append(name)
        return allowed

    def _prepare_copy_values_from_record(self, last, fields_list=None):
        """
        Convert the source record into create/default_get-friendly values:
          - M2O  -> ID
          - M2M  -> [(6, 0, ids)]
          - JSON -> plain dict (copy)
          - Scalars as-is
        Non-stored computed fields are skipped.
        If `fields_list` is provided, restrict to it (used by default_get).
        """
        vals = {}
        allowed = set(self._fields_to_copy())
        if fields_list:
            allowed &= set(fields_list)

        for name in allowed:
            field = self._fields[name]

            # Skip non-stored computed fields (UI-only, not in DB)
            if getattr(field, "compute", False) and not getattr(field, "store", False):
                continue

            value = last[name]
            if isinstance(field, fields.Many2one):
                vals[name] = value.id or False
            elif isinstance(field, fields.Many2many):
                vals[name] = [(6, 0, value.ids)]
            elif isinstance(field, fields.Json):
                vals[name] = dict(value) if isinstance(value, dict) else (value or {})
            else:
                vals[name] = value
        return vals

    # -----------------------------
    # Default values (form create)
    # -----------------------------
    @api.model
    def default_get(self, fields_list):
        """
        When opening a form in create mode (from a non-editable list),
        fill defaults from the last matching line.
        """
        res = super().default_get(fields_list)
        if not self._is_copy_enabled():
            return res

        last = self.search(self._copy_last_line_domain(), order="id desc", limit=1)
        if not last:
            return res

        # NOTE: This overwrites existing values from super() if present.
        # If you want "fill only empty", replace `res.update(...)`
        # with a selective merge that checks emptiness first.
        res.update(self._prepare_copy_values_from_record(last, fields_list))
        return res

    # -----------------------------
    # Inline create (editable tree)
    # -----------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """
        When creating records inline (editable tree),
        complete missing values from the last matching line.
        """
        if not self._is_copy_enabled():
            return super().create(vals_list)

        last = self.search(self._copy_last_line_domain(), order="id desc", limit=1)
        if not last:
            return super().create(vals_list)

        fill_vals = self._prepare_copy_values_from_record(last)
        fields_can_fill = set(self._fields_to_copy())

        new_vals_list = []
        for vals in vals_list:
            merged = dict(vals)
            for f in fields_can_fill:
                if f not in merged or merged[f] in (False, None, [], ""):
                    if f in fill_vals:
                        merged[f] = fill_vals[f]
            new_vals_list.append(merged)

        return super().create(new_vals_list)


# ------------------------------------------------------------
# Apply the mixin to an existing model
# ------------------------------------------------------------
class DailyJournalAgency(models.Model):
    """
    Extend the existing 'daily.journal.agency' model with the auto-copy mixin.
    """
    _name = "daily.journal.agency"
    _inherit = ["daily.journal.agency", "auto.copy.last.line.mixin"]

    __copy_last_line_fields__ = [
        "customer_code", "farmer_code", "product_code", "box_type",
        "quantity", "box_type_qty", "price_unit", "commission_value",
        "product_id", "date",
    ]
