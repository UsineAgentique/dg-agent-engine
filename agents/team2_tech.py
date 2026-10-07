'''team2_tech Pole

This module defines the entry point for the Tech, Infrastructure & Architecture pole (Team 2).
It aggregates three logical sub‑agents:

1. CTO & Lead Architect
2. DevOps & CI/CD Specialist
3. Data & Security Engineer

Each sub‑agent is represented as a lightweight class with a `run` method. The top‑level
function `run_mission` receives a free‑form mission string, parses a simple command
prefix and forwards the request to the appropriate sub‑agent. The design is deliberately
minimal – all heavy‑lifting (actual Render/Supabase monitoring, CI pipelines, security
checks) will be implemented in dedicated agents later. This file therefore satisfies
the immediate requirement of being a self‑contained, executable Python script with the
required signature.
''' 

from __future__ import annotations
import re
from typing import Any, Dict

# ---------------------------------------------------------------------------
# Sub‑agent definitions (stubs – extend as needed)
# ---------------------------------------------------------------------------

class CTOLeadArchitect:
    """Designs system architecture and ensures scalability.

    In a full implementation this would contain methods to generate
    infrastructure diagrams, evaluate technology stacks, and produce
    scalability reports.
    """

    def run(self, mission: str) -> str:
        # Simple placeholder logic – echo the mission with a tag.
        return f"[CTO/Architect] Mission received: {mission}"


class DevOpsCICDSpecialist:
    """Handles monitoring of Render, Supabase and CI/CD pipeline health.
    """

    def run(self, mission: str) -> str:
        return f"[DevOps/CI‑CD] Mission received: {mission}"


class DataSecurityEngineer:
    """Ensures data integrity in Supabase and enforces security best practices.
    """

    def run(self, mission: str) -> str:
        return f"[Data/Security] Mission received: {mission}"


# Mapping of command prefixes to sub‑agents
_SUBAGENT_MAP: Dict[str, Any] = {
    "cto": CTOLeadArchitect(),
    "devops": DevOpsCICDSpecialist(),
    "data": DataSecurityEngineer(),
}


def _dispatch(mission: str) -> str:
    """Dispatches the mission to the appropriate sub‑agent.

    Expected format: "<prefix>: <actual mission>" where <prefix> is one of
    'cto', 'devops', or 'data'. If the prefix is missing or unknown, the function
    returns a helpful error message.
    """
    match = re.match(r"^(?P<prefix>\w+):\s*(?P<body>.+)$", mission.strip(), re.IGNORECASE)
    if not match:
        return (
            "[Error] Mission format invalid. Expected '<prefix>: <description>'. "
            "Available prefixes: cto, devops, data."
        )
    prefix = match.group("prefix").lower()
    body = match.group("body")
    agent = _SUBAGENT_MAP.get(prefix)
    if not agent:
        return f"[Error] Unknown sub‑agent prefix '{prefix}'. Valid: cto, devops, data."
    return agent.run(body)


def run_mission(mission: str) -> str:
    """Entry point for the pole.

    Parameters
    ----------
    mission: str
        A free‑form description prefixed by the target sub‑agent.

    Returns
    -------
    str
        The response from the delegated sub‑agent or an error description.
    """
    if not mission:
        return "[Error] No mission provided."
    return _dispatch(mission)


# ---------------------------------------------------------------------------
# Self‑test block (executed only when run directly)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Simple demo – can be removed in production.
    examples = [
        "cto: design a multi‑region micro‑service architecture",
        "devops: check Render deployment health",
        "data: verify Supabase row‑level security policies",
        "unknown: test",
        "malformed mission",
    ]
    for ex in examples:
        print(f"Mission: {ex}\nResult: {run_mission(ex)}\n{'-'*40}")
