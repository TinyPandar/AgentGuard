"""Actual ledger shortfalls distinguish global and every local ancestor cap."""

from contextlib import contextmanager

import pytest
from run_controlled_model_comparison_v1 import global_budget_blocked
from sujie_demo_agent.model_budget import BudgetError, ModelBudget


def charge(budget, units):
    ticket = budget.reserve("SUBAGENT", units)
    budget.settle(ticket, status="RETURNED", reported_tokens=None)


def refusal(actor, code):
    return {
        "records": [
            {
                "event_type": "MODEL_EGRESS_BLOCKED",
                "subject_id": actor,
                "metadata": {"code": code, "direction": "REQUEST"},
            }
        ]
    }


@contextmanager
def unit_hierarchy(kind, root_remaining):
    shared = ModelBudget(max_requests=100, max_units=300000)
    run = shared.child("task-run", max_requests=12, max_units=200000)
    task = {"grant": {"subject_id": "main"}, "agent": {}, "delegations": [], "memory_sessions": []}
    if kind == "memory":
        prior = run.child("capture", max_requests=6, max_units=150000)
        charge(prior, 140000)
        leaf = run.child("reconcile", max_requests=6, max_units=150000)
        actor, requested, local_limit = "reconcile", 90000, 60000
        remaining_before_other = 160000
        task["memory_sessions"] = [
            {"name": "capture", "grant": {"subject_id": "capture"}, "budget": prior.view()},
            {"name": "reconcile", "grant": {"subject_id": actor}, "budget": leaf.view()},
        ]
    else:
        review = run.child("review", max_requests=6, max_units=120000)
        charge(review, 90000)
        leaf = review.child("verify", max_requests=3, max_units=60000)
        actor, requested, local_limit = "verify", 40000, 30000
        remaining_before_other = 210000
        task["delegations"] = [
            {
                "subject_id": "review",
                "parent_subject_id": "main",
                "role": "review",
                "model_budget": review.view(),
            },
            {
                "subject_id": actor,
                "parent_subject_id": "review",
                "role": "verify",
                "model_budget": leaf.view(),
            },
        ]
    outside_charge = remaining_before_other - root_remaining
    assert outside_charge >= 0
    if outside_charge:
        unrelated = shared.child("prior-task", max_requests=12, max_units=200000)
        charge(unrelated, outside_charge)
    task["agent"]["budget"] = run.view()
    try:
        with pytest.raises(BudgetError, match="MODEL_BUDGET_UNITS_EXHAUSTED"):
            leaf.reserve("SUBAGENT", requested)
        assert shared.view()["remaining_units"] == root_remaining
        assert leaf.view()["remaining_units"] > local_limit
        yield task, refusal(actor, "MODEL_BUDGET_UNITS_EXHAUSTED"), shared.view(), requested
    finally:
        shared.ledger.close()


@pytest.mark.parametrize("root_remaining", [50000, 60000, 100000, 160000])
def test_memory_run_ancestor_shortfall_is_global_only_when_root_also_tightest(root_remaining):
    with unit_hierarchy("memory", root_remaining) as (task, audit, shared, requested):
        if root_remaining > 60000:
            assert shared["remaining_units"] >= requested  # Root could admit the rejected request.
        assert global_budget_blocked(task, audit, shared) is (root_remaining <= 60000)


@pytest.mark.parametrize("root_remaining", [20000, 30000, 50000, 210000])
def test_nested_verify_includes_review_and_run_ancestors(root_remaining):
    with unit_hierarchy("delegated", root_remaining) as (task, audit, shared, requested):
        if root_remaining > 30000:
            assert shared["remaining_units"] >= requested
        assert global_budget_blocked(task, audit, shared) is (root_remaining <= 30000)


@pytest.mark.parametrize("global_requests", [2, 3])
def test_request_count_exhaustion_also_follows_the_run_ancestor(global_requests):
    shared = ModelBudget(max_requests=global_requests, max_units=300000)
    try:
        run = shared.child("run", max_requests=2, max_units=200000)
        review = run.child("review", max_requests=6, max_units=120000)
        charge(review, 1)
        charge(review, 1)
        verify = review.child("verify", max_requests=3, max_units=60000)
        with pytest.raises(BudgetError, match="MODEL_BUDGET_REQUESTS_EXHAUSTED"):
            verify.reserve("SUBAGENT", 1)
        task = {
            "grant": {"subject_id": "main"},
            "agent": {"budget": run.view()},
            "delegations": [
                {
                    "subject_id": "review",
                    "parent_subject_id": "main",
                    "model_budget": review.view(),
                },
                {
                    "subject_id": "verify",
                    "parent_subject_id": "review",
                    "model_budget": verify.view(),
                },
            ],
        }
        assert global_budget_blocked(
            task, refusal("verify", "MODEL_BUDGET_REQUESTS_EXHAUSTED"), shared.view()
        ) is (global_requests == 2)
    finally:
        shared.ledger.close()


@pytest.mark.parametrize(
    "mutation", ["missing-parent", "cycle", "missing-parent-budget", "missing-run-budget"]
)
def test_incomplete_role_chains_cannot_invent_a_global_refusal(mutation):
    with unit_hierarchy("delegated", 20000) as (task, audit, shared, _):
        if mutation == "missing-parent":
            task["delegations"][1]["parent_subject_id"] = "unknown"
        elif mutation == "cycle":
            task["delegations"][0]["parent_subject_id"] = "verify"
        elif mutation == "missing-parent-budget":
            del task["delegations"][0]["model_budget"]["remaining_units"]
        else:
            task["agent"]["budget"] = {}
        assert not global_budget_blocked(task, audit, shared)


def test_nonbudget_model_failure_does_not_stop_batch_as_global():
    with unit_hierarchy("memory", 50000) as (task, _, shared, _):
        assert not global_budget_blocked(
            task, refusal("reconcile", "BAILIAN_TRANSPORT_ERROR"), shared
        )
