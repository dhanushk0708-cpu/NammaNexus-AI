import sys
from pathlib import Path

# Ensure backend directory is in sys.path when executed directly
backend_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.nammaserve.ai.evaluation.runner import EvaluationRunner


def main():
    """Run NammaServe AI Intent Extraction Evaluation CLI."""
    print("Starting NammaServe AI Intent Extraction Evaluation...")
    runner = EvaluationRunner()
    report = runner.run_sync()
    print("\n" + report.summary_text() + "\n")


if __name__ == "__main__":
    main()
