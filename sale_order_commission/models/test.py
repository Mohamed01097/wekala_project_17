from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    num_members = fields.Integer(string="Number of Members", default=1)
    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute='_compute_amount',
        store=True
    )

    @api.depends('num_members', 'price_unit', 'product_uom_qty', 'discount', 'tax_id')
    def _compute_amount(self):
        for line in self:
            # Compute subtotal based on number of members
            line.price_subtotal = line.num_members * line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            # Compute taxes (if needed)
            taxes = line.tax_id.compute_all(
                line.price_unit,
                line.order_id.currency_id,
                quantity=line.num_members,
                product=line.product_id,
                partner=line.order_id.partner_shipping_id
            ) if line.tax_id else {'total_excluded': 0.0, 'total_included': 0.0}

            line.price_tax = taxes['total_included'] - taxes['total_excluded']
            line.price_total = taxes['total_included']



class SaleOrder(models.Model):
    _inherit = 'sale.order'

    amount_untaxed = fields.Monetary(
        string="Untaxed Amount",
        store=True,
        compute='_compute_amounts'
    )
    amount_total = fields.Monetary(
        string="Total",
        store=True,
        compute='_compute_amounts'
    )
    amount_tax = fields.Monetary(
        string="Taxes",
        store=True,
        compute='_compute_amounts'
    )

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'order_line.price_total','order_line.num_members')
    def _compute_amounts(self):
        super()._compute_amounts()

        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            if order.company_id.tax_calculation_rounding_method == 'round_globally':
                amount_untaxed = sum(order_lines.mapped('price_subtotal'))
                order.amount_untaxed = amount_untaxed

