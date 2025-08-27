import os
import pkg_resources
import subprocess
import sys
from pathlib import Path

def get_installed_packages():
    """Get all installed packages in the current environment."""
    installed_packages = []
    for dist in pkg_resources.working_set:
        installed_packages.append(f"{dist.project_name}=={dist.version}")
    return sorted(installed_packages)

def find_django_packages(installed_packages):
    """Filter to Django-related packages."""
    django_keywords = ['django', 'drf', 'celery', 'psycopg2', 'mysql', 'pillow', 'gunicorn']
    django_packages = []
    
    for package in installed_packages:
        lower_package = package.lower()
        if any(keyword in lower_package for keyword in django_keywords):
            django_packages.append(package)
    
    return django_packages

def main():
    """Main function to generate requirements.txt."""
    print("Analyzing your Python environment for Django packages...")
    
    # Get all installed packages
    all_packages = get_installed_packages()
    django_packages = find_django_packages(all_packages)
    
    # Write to requirements.txt
    requirements_path = Path('requirements.txt')
    with open(requirements_path, 'w') as f:
        f.write("# Django project requirements\n")
        f.write("# Generated from current environment\n\n")
        for package in django_packages:
            f.write(f"{package}\n")
    
    print(f"Generated requirements.txt with {len(django_packages)} Django-related packages")
    print(f"File saved to: {requirements_path}")
    
    # Show the generated content
    print("\nGenerated requirements:")
    print("=" * 40)
    with open(requirements_path, 'r') as f:
        print(f.read())

if __name__ == "__main__":
    main()