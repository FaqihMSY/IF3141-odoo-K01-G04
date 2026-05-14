{
    "name": "FR-08/09 Procurement",
    "summary": "Manage suppliers and purchase orders for procurement.",
    "version": "17.0.1.0.0",
    "category": "Purchase",
    "author": "IF3141 K01 G04",
    "license": "LGPL-3",
    "depends": [
        "purchase",
        "raw_material_inventory",
    ],
    "data": [
        "security/procurement_groups.xml",
        "security/ir.model.access.csv",
        "data/procurement_sequence.xml",
        "views/procurement_supplier_views.xml",
        "views/procurement_purchase_order_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": True,
}
