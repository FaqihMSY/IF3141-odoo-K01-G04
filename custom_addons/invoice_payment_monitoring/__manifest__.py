{
    "name": "Invoice Payment Monitoring",
    "summary": "Record customer invoice payments and monitor settlement history.",
    "version": "17.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "IF3141 K01 G04",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/invoice_payment_log_views.xml",
        "wizards/register_invoice_payment_wizard_views.xml",
    ],
    "installable": True,
    "application": True,
}
