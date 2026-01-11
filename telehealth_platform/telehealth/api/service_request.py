import frappe
from frappe import _
from frappe.utils import now_datetime

@frappe.whitelist()
def create_service_request(patient, order_template, order_template_type="Lab Test Template", encounter=None, practitioner=None):
    """
    Creates a new Service Request (standard Frappe Health DocType).
    """
    if not frappe.has_permission("Service Request", "create"):
        frappe.throw(_("Not authorized to create Service Requests"), frappe.PermissionError)

    if not practitioner:
        practitioner = frappe.db.get_value("Healthcare Practitioner", {"user_id": frappe.session.user}, "name")
        if not practitioner:
            frappe.throw(_("Healthcare Practitioner record not found for this user"))

    request = frappe.get_doc({
        "doctype": "Service Request",
        "patient": patient,
        "practitioner": practitioner,
        "encounter": encounter,
        "order_template_type": order_template_type,
        "order_template": order_template,
        "status": "Active",
        "intent": "Order",
        "priority": "Routine",
        "authored_on": now_datetime()
    })

    request.insert()
    frappe.db.commit()

    return request.as_dict()

@frappe.whitelist()
def search_service_templates(text, type="Lab Test Template"):
    """
    Searches for service templates (Lab Tests, Procedures, etc.).
    """
    return frappe.get_all(type,
        filters={"name": ["like", f"%{text}%"]},
        fields=["name"],
        limit=20
    )
