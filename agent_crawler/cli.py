import argparse
import json
import logging

from dotenv import load_dotenv

from .config import load_settings
from .crawler import run


def main():
    parser = argparse.ArgumentParser(description="Inventory publicly documented named AI agents")
    parser.add_argument("--config", help="JSON configuration (environment overrides its values)")
    parser.add_argument("--output", help="Override output CSV path")
    args = parser.parse_args()
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        settings = load_settings(args.config)
        if args.output:
            settings.output_file = args.output
        _, summary = run(settings)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Configuration/output error: {exc}\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
