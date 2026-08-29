from __future__ import annotations


def main() -> None:
    """Run the DSA CLI after the package bootstrap registers vendored modules."""
    from dsa_evaluation.cli import main as evaluation_main

    evaluation_main()
