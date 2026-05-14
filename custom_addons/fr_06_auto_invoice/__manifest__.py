{
    "name": "FR-06 Automatic Sales Invoice",
    "summary": "Automatically create and post unique invoices for completed sales deliveries.",
    "version": "17.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "IF3141 K01 G04",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "sale_stock",
        "account",
    ],
    "data": [
        "data/ir_cron.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": True,
}
