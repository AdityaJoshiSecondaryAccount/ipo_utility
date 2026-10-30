#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import io


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'userproject.settings')

    if sys.stdout is None:
        sys.stdout = io.StringIO()
    if sys.stderr is None:
        sys.stderr = io.StringIO()

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    try:
        execute_from_command_line(sys.argv)
    except Exception:
        import traceback
        traceback.print_exc(file=sys.stderr)
        try:
            sys.stderr.flush()
        except Exception:
            pass
        sys.exit(1)


# Main Program
if __name__ == '__main__':
    main()
