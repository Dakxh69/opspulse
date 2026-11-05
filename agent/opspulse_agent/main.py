"""
OpsPulse Host Monitoring Agent — Main Entry Point

CLI usage:
    python -m opspulse_agent.main
    python -m opspulse_agent.main --config /path/to/config.yaml
"""

from __future__ import annotations

import argparse
import logging
import sys

from opspulse_agent.config import AgentConfig
from opspulse_agent.scheduler import AgentScheduler


def configure_logging(level_name: str) -> None:
    """Configures console logging for the host agent."""
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def main() -> None:
    """Parses command-line arguments and boots the agent runtime."""
    parser = argparse.ArgumentParser(description="OpsPulse Linux Host Monitoring Agent")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="Path to YAML configuration file (e.g. config.yaml)",
    )
    args = parser.parse_args()

    config = AgentConfig.load_from_file(args.config)
    configure_logging(config.logging.level)

    scheduler = AgentScheduler(config)
    scheduler.run()


if __name__ == "__main__":
    main()

