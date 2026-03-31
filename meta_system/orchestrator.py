import argparse
import json
from pathlib import Path

from .executor import Executor
from .spec_loader import SpecLoader


def main() -> int:
    parser = argparse.ArgumentParser(description="Meta system orchestrator")
    parser.add_argument("--specs-dir", default="specs/apps/", help="Directory containing app specs")
    parser.add_argument("--apps-dir", default="apps/", help="Output directory for apps")
    parser.add_argument("--meta-dir", default="meta_system/", help="Output directory for meta system artifacts")
    parser.add_argument("--workers", type=int, default=4, help="Parallel worker count")
    parser.add_argument("--output", default="meta_system/results.json", help="Results output path")
    args = parser.parse_args()

    loader = SpecLoader(args.specs_dir)
    specs = [s.raw for s in loader.load()]

    executor = Executor(max_workers=args.workers, apps_dir=args.apps_dir, meta_dir=args.meta_dir)
    results = executor.run_many(specs)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")

    print(json.dumps({"results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
