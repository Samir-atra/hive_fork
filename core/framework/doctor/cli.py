import argparse

from framework.doctor.checks import cmd_doctor


def register_doctor_commands(subparsers: argparse._SubParsersAction) -> None:
    """
    Register the doctor command with the main CLI.

    Args:
        subparsers: The subparsers action from the main parser.
    """
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Run a full health check across the development environment.",
        description="Diagnose the environment and report what is broken with fixes.",
    )
    doctor_parser.add_argument(
        "--json",
        action="store_true",
        help="Output the results in JSON format.",
    )
    doctor_parser.set_defaults(func=cmd_doctor)
