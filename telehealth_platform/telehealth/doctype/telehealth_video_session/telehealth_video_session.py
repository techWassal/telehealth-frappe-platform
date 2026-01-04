import frappe
from frappe.model.document import Document
from frappe.utils import time_diff_in_seconds

class TelehealthVideoSession(Document):
    def validate(self):
        self.calculate_duration()

    def calculate_duration(self):
        if self.started_at and self.ended_at:
            self.duration = time_diff_in_seconds(self.ended_at, self.started_at)
