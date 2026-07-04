"""
Formatting helpers for PATCC reports.
"""


def print_header(title: str):

    line = "=" * 60

    print()
    print(line)
    print(title.upper())
    print(line)


def print_subheader(title: str):

    print()
    print(title)
    print("-" * len(title))
