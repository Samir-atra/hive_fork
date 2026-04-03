"""CLI commands for AI model versioning and rollback."""

import argparse
import json

from framework.llm.versioning import ModelVersionManager


def handle_register(args: argparse.Namespace) -> int:
    """Handle the 'version register' command."""
    manager = ModelVersionManager.default()

    metrics = {}
    if args.metrics:
        try:
            metrics = json.loads(args.metrics)
        except json.JSONDecodeError:
            print("Error: Metrics must be a valid JSON string.")
            return 1

    manager.register_version(
        model_id=args.model_id,
        version=args.version,
        provider_model_id=args.provider_model_id,
        metrics=metrics,
    )
    print(
        f"Successfully registered model '{args.model_id}' "
        f"version '{args.version}' mapping to '{args.provider_model_id}'."
    )
    return 0


def handle_switch(args: argparse.Namespace) -> int:
    """Handle the 'version switch' command."""
    manager = ModelVersionManager.default()
    try:
        manager.switch_version(model_id=args.model_id, version=args.version)
        print(f"Successfully switched model '{args.model_id}' to version '{args.version}'.")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1


def handle_rollback(args: argparse.Namespace) -> int:
    """Handle the 'version rollback' command."""
    manager = ModelVersionManager.default()
    try:
        success = manager.rollback(model_id=args.model_id)
        if success:
            current = manager.get_version_info(args.model_id)
            if current and current.get("active_version"):
                print(
                    f"Rolled back model '{args.model_id}'. "
                    f"Active version is now '{current['active_version']}'."
                )
            return 0
        else:
            print(f"Rollback failed or no older versions exist for '{args.model_id}'.")
            return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def handle_list(args: argparse.Namespace) -> int:
    """Handle the 'version list' command."""
    manager = ModelVersionManager.default()
    if getattr(args, "model_id", None):
        info = manager.get_version_info(args.model_id)
        if not info:
            print(f"No version information found for model '{args.model_id}'.")
            return 1
        print(json.dumps(info, indent=2))
    else:
        models = manager.list_models()
        if not models:
            print("No models registered.")
            return 0
        print(json.dumps(models, indent=2))
    return 0


def register_version_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register 'version' commands with the main CLI parser."""
    version_parser = subparsers.add_parser("version", help="Manage AI model versions and rollbacks")
    version_subparsers = version_parser.add_subparsers(dest="version_command", required=True)

    # register command
    register_parser = version_subparsers.add_parser("register", help="Register a new model version")
    register_parser.add_argument("model_id", help="Conceptual model ID")
    register_parser.add_argument("version", help="Version identifier (e.g., 'v1', 'v2')")
    register_parser.add_argument("provider_model_id", help="Actual provider model ID")
    register_parser.add_argument("--metrics", help="Optional JSON string of metrics")
    register_parser.set_defaults(func=handle_register)

    # switch command
    switch_parser = version_subparsers.add_parser(
        "switch", help="Switch the active version of a model"
    )
    switch_parser.add_argument("model_id", help="Conceptual model ID")
    switch_parser.add_argument("version", help="Version identifier to switch to")
    switch_parser.set_defaults(func=handle_switch)

    # rollback command
    rollback_parser = version_subparsers.add_parser(
        "rollback", help="Rollback to a previous version"
    )
    rollback_parser.add_argument("model_id", help="Conceptual model ID")
    rollback_parser.set_defaults(func=handle_rollback)

    # list command
    list_parser = version_subparsers.add_parser("list", help="List registered models and versions")
    list_parser.add_argument("model_id", nargs="?", help="Specific model ID to list")
    list_parser.set_defaults(func=handle_list)
