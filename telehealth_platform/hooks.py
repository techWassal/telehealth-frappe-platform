app_name = "telehealth_platform"
app_title = "Telehealth Platform"
app_publisher = "Antigravity"
app_description = "Telehealth Extension for Frappe Healthcare"
app_email = "admin@example.com"
app_license = "mit"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/telehealth_platform/css/telehealth_platform.css"
# app_include_js = "/assets/telehealth_platform/js/telehealth_platform.js"

# include js, css files in header of web template
# web_include_css = "/assets/telehealth_platform/css/telehealth_platform.css"
# web_include_js = "/assets/telehealth_platform/js/telehealth_platform.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# Website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "telehealth_platform.utils.jinja_methods",
# 	"filters": "telehealth_platform.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "telehealth_platform.install.before_install"
# after_install = "telehealth_platform.install.after_install"

# Uninstallation
# --------------

# before_uninstall = "telehealth_platform.uninstall.before_uninstall"
# after_uninstall = "telehealth_platform.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To setup dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "telehealth_platform.utils.before_app_install"
# after_app_install = "telehealth_platform.utils.after_app_install"

# Integration Cleanup
# -------------------
# To cleanup dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "telehealth_platform.utils.before_app_uninstall"
# after_app_uninstall = "telehealth_platform.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "telehealth_platform.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in Python
# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype class

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
# 	"all": [
# 		"telehealth_platform.tasks.all"
# 	],
# 	"daily": [
# 		"telehealth_platform.tasks.daily"
# 	],
 	"hourly": [
 		"telehealth_platform.telehealth.api.video_session.cleanup_expired_sessions"
 	],
# 	"weekly": [
# 		"telehealth_platform.tasks.weekly"
# 	],
# 	"monthly": [
# 		"telehealth_platform.tasks.monthly"
# 	],
}

# Testing
# -------

# before_tests = "telehealth_platform.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "telehealth_platform.event.get_events"
# }
#
# each method should be in the typing python module
# override_doctype_dashboards = {
# 	"ToDo": "telehealth_platform.dashboards.get_dashboards_for_todo"
# }

# exempt from gatekeeper as it is a public api
# fi_exempt_from_gatekeeper = [
# 	"telehealth_platform.telehealth.api"
# ]

# Authentication and Authorization
# --------------------------------

# auth_hooks = [
# 	"telehealth_platform.auth.validate"
# ]

website_route_rules = [
    {"from_route": "/api/v1/<path:path>", "to_route": "telehealth_platform.telehealth.api.router"},
]
