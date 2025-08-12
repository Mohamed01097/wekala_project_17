# -*- coding: utf-8 -*-
{
    'name': "daily_journal_agency",

    'summary': """ """,

    'description': """
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '17.0.1.0.0',

    'depends': ['base','sale','mail','contacts','stock','sale_order_commission','purchase','account','web_tree_dynamic_colored_field'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/views.xml',
        'views/menu.xml',
        'views/create_sale_order.xml',
        'views/create_purchase_order.xml',
        'views/create_delivery.xml',
        'views/create_receipt.xml',
    ],

}
