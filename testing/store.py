"""In-memory store for test scenarios with optional load from golden files."""

import json
from pathlib import Path

from observability.logger import get_logger
from schemas.tests import TestScenario

logger = get_logger(__name__)

GOLDEN_DIR = Path(__file__).resolve().parent.parent / "tests" / "golden"


class TestScenarioStore:
    """In-memory store for test scenarios. Loads golden tests on init."""

    def __init__(self):
        self._scenarios: dict[str, TestScenario] = {}
        self._load_golden()

    def _load_golden(self) -> None:
        """Load all JSON files from tests/golden/."""
        if not GOLDEN_DIR.is_dir():
            logger.info("No golden test directory", path=str(GOLDEN_DIR))
            return
        for path in GOLDEN_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                items = data if isinstance(data, list) else [data]
                for item in items:
                    scenario = TestScenario.model_validate(item)
                    self._scenarios[scenario.id] = scenario
                    logger.info("Loaded golden test", path=path.name, id=scenario.id)
            except Exception as e:
                logger.warning("Failed to load golden test", path=path.name, error=str(e))

    def list_all(self) -> list[TestScenario]:
        """Return all scenarios."""
        return list(self._scenarios.values())

    def get(self, test_id: str) -> TestScenario | None:
        """Get scenario by ID."""
        return self._scenarios.get(test_id)

    def put(self, scenario: TestScenario) -> None:
        """Create or update scenario."""
        self._scenarios[scenario.id] = scenario

    def delete(self, test_id: str) -> bool:
        """Delete scenario. Returns True if existed."""
        if test_id in self._scenarios:
            del self._scenarios[test_id]
            return True
        return False
