from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().splitlines()

setup(
	name="telehealth_platform",
	version="0.0.1",
	description="Telehealth Extension for Frappe Healthcare",
	author="Antigravity",
	author_email="admin@example.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires,
)
