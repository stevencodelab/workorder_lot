{
    "name": "Split MRP Work Order",
    "summary": "Split Work Orders",
    "version": "14.0.1.0.0",
    "author": "Steven Morison (stevenmorizon123@gmail.com)",
    "website": "",
    "license": "AGPL-3",
    "category": "Manufacturing",
    "depends": ["mrp","product","stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/inherit_mrp_production_views.xml",
        "views/inherit_mrp_workorder.xml",
        "wizard/mrp_split_workorder.xml",
    ],
    
    'auto_install': False,
    'installable': True,
    'application': True,
}
