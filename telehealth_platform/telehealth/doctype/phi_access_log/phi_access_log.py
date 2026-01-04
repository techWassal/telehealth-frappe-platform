import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

class PHIAccessLog(Document):
    def before_insert(self):
        if not self.timestamp:
            self.timestamp = now_datetime()
        if not self.ip_address:
            self.ip_address = frappe.local.get("request_ip") or "0.0.0.0"
        if not self.user_agent:
            self.user_agent = frappe.local.get("user_agent") or ""
        if not self.user_name:
            self.user_name = frappe.db.get_value("User", self.user, "full_name")
