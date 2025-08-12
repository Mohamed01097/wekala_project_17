from odoo import models, fields, api, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    discount_type = fields.Selection([('percent', 'Percentage'), ('amount', 'Amount')], string='Discount Type',
                                     default='percent')
    discount_rate = fields.Monetary(string='Discount Rate', digits=(16, 2), default=8.0, currency_field='currency_id')


   

    @api.depends_context('lang')
    @api.depends('order_line.taxes_id', 'order_line.price_subtotal', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals(self):
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            order.tax_totals = self.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in order_lines],
                order.currency_id or order.company_id.currency_id,
            )
            discount = 0.0
            if order.discount_type == 'amount':
                discount = order.discount_rate
            elif order.discount_type == 'percent':
                discount = order.tax_totals['amount_untaxed'] * order.discount_rate / 100.0
            order.tax_totals['amount_untaxed']= order.tax_totals['amount_untaxed'] - discount



 

    @api.depends('order_line.price_total', 'discount_type', 'discount_rate')
    def _amount_all(self):
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)

            if order.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_results = self.env['account.tax']._compute_taxes([
                    line._convert_to_tax_base_line_dict()
                    for line in order_lines
                ])
                totals = tax_results['totals']
                amount_untaxed = totals.get(order.currency_id, {}).get('amount_untaxed', 0.0)
                amount_tax = totals.get(order.currency_id, {}).get('amount_tax', 0.0)
            else:
                amount_untaxed = sum(order_lines.mapped('price_subtotal'))
                amount_tax = sum(order_lines.mapped('price_tax'))

            discount = 0.0
            if order.discount_type == 'amount':
                discount = order.discount_rate
            elif order.discount_type == 'percent':
                discount = amount_untaxed * order.discount_rate / 100.0

            order.amount_untaxed = amount_untaxed - discount
            order.amount_tax = amount_tax
            order.amount_total = order.amount_untaxed + order.amount_tax


    def _prepare_invoice(self, ):
        """Super sale order class and update with fields"""
        invoice_vals = super(PurchaseOrder, self)._prepare_invoice()
        invoice_vals.update({
            'discount_type': self.discount_type,
            'discount_rate': self.discount_rate,
        })
        return invoice_vals



class AccountMove(models.Model):
    _inherit = 'account.move'


    discount_type = fields.Selection(
        [('percent', 'Percentage'), ('amount', 'Amount')],
        string='Discount type',
        default='percent', help="Type of discount.")
    discount_rate = fields.Float('Discount Rate', digits=(16, 2),default=8.0, currency_field='currency_id',
                                 help="Give the discount rate.")
    




    def _supply_rate(self):
        """This function calculates supply rates based on change of
        discount_type,
           discount_rate and invoice_line_ids"""
        for inv in self:
            if inv.discount_type == 'percent':
                for line in inv.invoice_line_ids:
                   
                    inv.amount_discount = inv.discount_rate
                    line._compute_totals()
            else:
                total = 0.0
                print("inv.invoice_line_ids", inv.invoice_line_ids)
                
                if inv.discount_rate != 0:
                    discount = (inv.discount_rate / total) * 100
                else:
                    discount = inv.discount_rate
                for line in inv.invoice_line_ids:
                    print("line", discount)
                    line.write({'discount': discount})
                    print("line.discount", line.discount)
                    inv.amount_discount = inv.discount_rate
                    line._compute_totals()
            inv._compute_tax_totals()
        def create(self, vals):
            """Override create method to set default values for discount_type and discount_rate."""
            self._supply_rate()
            return super(AccountMove, self).create(vals)

