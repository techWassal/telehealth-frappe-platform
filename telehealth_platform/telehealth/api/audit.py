import frappe
from frappe import _

@frappe.whitelist()
def search_logs(user_id=None, patient_id=None, from_date=None, to_date=None):
    """
    Search audit logs. Requires Admin role.
    """
    if not ("System Manager" in frappe.get_roles() or "Administrator" in frappe.get_roles()):
        frappe.local.response.http_status_code = 403
        return {"error": "Forbidden", "message": _("Admin access required")}

    filters = {}
    if user_id: filters["user"] = user_id
    if patient_id: filters["patient"] = patient_id
    if from_date and to_date:
        filters["timestamp"] = ["between", [from_date, to_date]]

    logs = frappe.get_all("PHI Access Log", 
        fields=["name", "timestamp", "user", "user_name", "action", "resource_type", "patient", "ip_address"],
        filters=filters,
        order_by="timestamp desc"
    )

    return [format_log(l) for l in logs]

@frappe.whitelist()
def get_log_detail(id):
    """
    Get audit log detail. Requires Admin role.
    """
    if not ("System Manager" in frappe.get_roles() or "Administrator" in frappe.get_roles()):
        frappe.local.response.http_status_code = 403
        return {"error": "Forbidden", "message": _("Admin access required")}

    if not frappe.db.exists("PHI Access Log", id):
        frappe.local.response.http_status_code = 404
        return {"error": "Not Found", "message": _("Log entry not found")}

    log = frappe.get_doc("PHI Access Log", id)
    return format_log(log)

def format_log(l):
    """
    Helper to format log entry according to contract.
    """
    return {
        "id": l.name,
        "timestamp": str(l.timestamp),
        "user_id": l.user,
        "user_name": l.user_name,
        "action": l.action,
        "resource_type": l.resource_type,
        "resource_id": getattr(l, "resource_id", ""),
        "patient_id": l.patient,
        "ip_address": l.ip_address,
        "user_agent": l.user_agent if hasattr(l, "user_agent") else "",
        "metadata": l.metadata if hasattr(l, "metadata") else {}
    }
