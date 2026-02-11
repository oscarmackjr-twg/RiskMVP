"""Scenario management service for stress testing and what-if analysis.

Provides CRUD operations for scenario definitions and scenario execution.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Any
import json
import hashlib
from datetime import datetime

from services.common.db import db_conn


class ScenarioService:
    """Scenario definition and management (SCEN-01, SCEN-02, SCEN-04)."""

    def create_scenario(self, scenario_def: Dict[str, Any]) -> str:
        """Create new scenario definition.

        Args:
            scenario_def: Scenario definition with structure:
                {{
                    'name': str,
                    'type': 'STRESS' | 'WHAT_IF' | 'HISTORICAL',
                    'scenario_set': Optional[str],  # e.g., 'CCAR', 'DFAST'
                    'shocks': Dict[str, Any],  # Market shocks to apply
                    'description': Optional[str]
                }}

        Returns:
            scenario_id (UUID string)
        """
        # Validate required fields
        if 'name' not in scenario_def:
            raise ValueError("Scenario must have 'name'")
        if 'type' not in scenario_def:
            raise ValueError("Scenario must have 'type'")
        if 'shocks' not in scenario_def:
            raise ValueError("Scenario must have 'shocks'")

        # Generate scenario_id from content hash
        content = json.dumps(scenario_def, sort_keys=True)
        scenario_id = hashlib.sha256(content.encode()).hexdigest()[:16]

        with db_conn() as conn:
            with conn.cursor() as cur:
                # Create table if needed
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS scenario (
                        scenario_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        type TEXT NOT NULL,
                        scenario_set TEXT,
                        shocks JSONB NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP
                    )
                """)

                cur.execute("""
                    INSERT INTO scenario (scenario_id, name, type, scenario_set, shocks, description, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (scenario_id) DO NOTHING
                    RETURNING scenario_id
                """, (
                    scenario_id,
                    scenario_def['name'],
                    scenario_def['type'],
                    scenario_def.get('scenario_set'),
                    json.dumps(scenario_def['shocks']),
                    scenario_def.get('description'),
                    datetime.utcnow()
                ))

        return scenario_id

    def get_scenario(self, scenario_id: str) -> Dict[str, Any]:
        """Retrieve scenario definition."""
        with db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT scenario_id, name, type, scenario_set, shocks, description, created_at
                    FROM scenario WHERE scenario_id = %s
                """, (scenario_id,))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Scenario not found: {{scenario_id}}")
                return {{
                    'scenario_id': row['scenario_id'],
                    'name': row['name'],
                    'type': row['type'],
                    'scenario_set': row['scenario_set'],
                    'shocks': json.loads(row['shocks']) if isinstance(row['shocks'], str) else row['shocks'],
                    'description': row['description']
                }}

    def list_scenarios(self, scenario_set: Optional[str] = None) -> List[Dict[str, Any]]:
        """List scenarios."""
        with db_conn() as conn:
            with conn.cursor() as cur:
                if scenario_set:
                    cur.execute("SELECT * FROM scenario WHERE scenario_set = %s ORDER BY name", (scenario_set,))
                else:
                    cur.execute("SELECT * FROM scenario ORDER BY scenario_set, name")
                return [dict(row) for row in cur.fetchall()]

    def create_stress_test(self, shocks: Dict[str, float], name: str = "Custom Stress") -> Dict[str, Any]:
        """Create stress test scenario (SCEN-02)."""
        scenario_def = {{
            'name': name,
            'type': 'STRESS',
            'shocks': shocks,
            'description': f"Stress test with shocks: {{shocks}}"
        }}
        scenario_id = self.create_scenario(scenario_def)
        return {{**scenario_def, 'scenario_id': scenario_id}}

    def run_what_if(self, base_run_id: str, modifications: Dict[str, Any]) -> str:
        """Create what-if scenario (SCEN-04)."""
        what_if_run_id = f"{{base_run_id}}-whatif-{{hashlib.sha256(json.dumps(modifications).encode()).hexdigest()[:8]}}"
        return what_if_run_id
