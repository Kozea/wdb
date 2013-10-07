import sys

python_version = sys.version_info[0]

if python_version == 2:
    division_by_zero_message = 'integer division or modulo by zero'
elif python_version == 3:
    division_by_zero_message = 'division by zero'
