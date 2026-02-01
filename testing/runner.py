"""Run test scenarios against the chat API."""

import uuid

import httpx
from fastapi import FastAPI

from observability.logger import get_logger
from schemas.tests import TestScenario, TestRunResult, TestTurn, TurnResult

logger = get_logger(__name__)


def _check_turn(turn: TestTurn, response_text: str, response_agent: str | None) -> tuple[bool, str | None]:
    """Check assertions for one turn. Returns (passed, reason)."""
    if turn.expect_agent is not None and response_agent != turn.expect_agent:
        return False, f"Expected agent {turn.expect_agent}, got {response_agent or 'None'}"
    if turn.expect_contains is not None and turn.expect_contains not in response_text:
        return False, f"Response should contain '{turn.expect_contains}'"
    if turn.expect_not_contains is not None and turn.expect_not_contains in response_text:
        return False, f"Response should not contain '{turn.expect_not_contains}'"
    return True, None


async def run_test(scenario: TestScenario, app: FastAPI) -> TestRunResult:
    """
    Run a single test scenario by POSTing each turn to /chat.

    Uses a dedicated session_id so the trace can be inspected.
    """
    session_id = f"test-{scenario.id}-{uuid.uuid4().hex[:8]}"
    turn_results: list[TurnResult] = []
    all_passed = True

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        timeout=60.0,
    ) as client:
        for i, turn in enumerate(scenario.turns):
            try:
                r = await client.post(
                    "/chat",
                    json={"session_id": session_id, "message": turn.message},
                )
                if r.status_code != 200:
                    turn_results.append(
                        TurnResult(
                            turn_index=i,
                            passed=False,
                            message=turn.message,
                            actual_response="",
                            actual_agent=None,
                            reason=f"HTTP {r.status_code}: {r.text[:200]}",
                        )
                    )
                    all_passed = False
                    continue
                data = r.json()
                response_text = data.get("response", "")
                response_agent = data.get("agent")
                passed, reason = _check_turn(turn, response_text, response_agent)
                if not passed:
                    all_passed = False
                turn_results.append(
                    TurnResult(
                        turn_index=i,
                        passed=passed,
                        message=turn.message,
                        actual_response=response_text[:500],
                        actual_agent=response_agent,
                        reason=reason,
                    )
                )
            except Exception as e:
                logger.exception("Test turn failed", test_id=scenario.id, turn=i, error=str(e))
                turn_results.append(
                    TurnResult(
                        turn_index=i,
                        passed=False,
                        message=turn.message,
                        actual_response="",
                        actual_agent=None,
                        reason=str(e),
                    )
                )
                all_passed = False

    return TestRunResult(
        test_id=scenario.id,
        passed=all_passed,
        session_id=session_id,
        turns=turn_results,
        error=None,
    )


async def run_all_tests(
    store: "TestScenarioStore",
    app: FastAPI,
    test_ids: list[str] | None = None,
) -> list[TestRunResult]:
    """Run scenarios (all or by id list). Returns list of results."""
    if test_ids:
        scenarios = [store.get(tid) for tid in test_ids]
        scenarios = [s for s in scenarios if s is not None]
    else:
        scenarios = store.list_all()
    results = []
    for scenario in scenarios:
        results.append(await run_test(scenario, app))
    return results
