import argparse
import json
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import server  # noqa: E402


def configure_base_dir(base_dir):
    base = Path(base_dir).resolve()
    server.BASE_DIR = base
    return base


def write_report(base_dir, report):
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    report_path = logs_dir / f"rdp_env_link_report_{time.strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report_path


def main():
    parser = argparse.ArgumentParser(description="Upgrade rdp.csv rows with explicit environment ownership.")
    parser.add_argument("--base-dir", default=str(REPO_ROOT), help="EnvPortal runtime directory containing data.csv and rdp.csv.")
    parser.add_argument("--dry-run", action="store_true", help="Analyze and report without writing rdp.csv.")
    parser.add_argument("--report-json", action="store_true", help="Print the report as JSON.")
    parser.add_argument("--fail-on-dirty", action="store_true", help="Exit with status 2 when dirty RDP rows remain.")
    args = parser.parse_args()

    base_dir = configure_base_dir(args.base_dir)
    data_rows = server.read_csv_records("data.csv", server.PORTAL_CSV_FIELDS)
    rdp_rows = server.read_csv_records("rdp.csv", server.RDP_CSV_FIELDS)
    upgraded_rows, report = server.upgrade_rdp_env_links(data_rows, rdp_rows)
    report["baseDir"] = str(base_dir)
    report["dryRun"] = bool(args.dry_run)

    if not args.dry_run and report["updatedRows"]:
        server.write_csv_records("rdp.csv", server.RDP_CSV_FIELDS, upgraded_rows)

    report_path = write_report(base_dir, report)
    report["reportPath"] = str(report_path)

    if args.report_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"checked={report['checkedRows']} updated={report['updatedRows']} dirty={report['dirtyRows']}")
        print(f"report={report_path}")

    if args.fail_on_dirty and report["dirtyRows"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
