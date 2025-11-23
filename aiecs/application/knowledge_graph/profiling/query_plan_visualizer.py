"""
Query Plan Visualizer

Visualize query execution plans and performance profiles.
"""

from typing import Dict, Any, List
from aiecs.application.knowledge_graph.profiling.query_profiler import (
    QueryProfile,
)
from aiecs.domain.knowledge_graph.models.query_plan import QueryPlan


class QueryPlanVisualizer:
    """
    Visualize query plans and execution profiles

    Generates text-based visualizations of query plans and performance data.

    Example:
        ```python
        visualizer = QueryPlanVisualizer()

        # Visualize query plan
        plan_viz = visualizer.visualize_plan(query_plan)
        print(plan_viz)

        # Visualize execution profile
        profile_viz = visualizer.visualize_profile(query_profile)
        print(profile_viz)
        ```
    """

    def visualize_plan(self, plan: QueryPlan, show_costs: bool = True) -> str:
        """
        Visualize a query plan

        Args:
            plan: Query plan to visualize
            show_costs: Whether to show cost estimates

        Returns:
            Text visualization of the plan
        """
        lines = []
        lines.append("=" * 60)
        lines.append("QUERY PLAN")
        lines.append("=" * 60)

        if show_costs:
            total_cost = plan.calculate_total_cost()
            lines.append(f"Total Estimated Cost: {total_cost:.2f}")
            lines.append("")

        for i, step in enumerate(plan.steps, 1):
            lines.append(f"Step {i}: {step.operation.value}")
            lines.append(f"  Description: {step.description}")

            if show_costs:
                lines.append(f"  Estimated Cost: {step.estimated_cost:.2f}")

            if step.depends_on:
                lines.append(f"  Depends On: {', '.join(step.depends_on)}")

            if step.metadata:
                lines.append(f"  Metadata: {step.metadata}")

            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    def visualize_profile(self, profile: QueryProfile, show_steps: bool = True) -> str:
        """
        Visualize a query execution profile

        Args:
            profile: Query profile to visualize
            show_steps: Whether to show individual steps

        Returns:
            Text visualization of the profile
        """
        lines = []
        lines.append("=" * 60)
        lines.append("QUERY EXECUTION PROFILE")
        lines.append("=" * 60)
        lines.append(f"Query ID: {profile.query_id}")
        lines.append(f"Query Type: {profile.query_type}")
        lines.append(f"Total Duration: {profile.duration_ms:.2f}ms")
        lines.append("")

        if show_steps and profile.steps:
            lines.append("Execution Steps:")
            lines.append("-" * 60)

            for i, step in enumerate(profile.steps, 1):
                duration = step["duration_ms"]
                percentage = (duration / profile.duration_ms * 100) if profile.duration_ms else 0

                lines.append(f"{i}. {step['name']}")
                lines.append(f"   Duration: {duration:.2f}ms ({percentage:.1f}%)")

                # Show bar chart
                bar_length = int(percentage / 2)  # Scale to 50 chars max
                bar = "█" * bar_length
                lines.append(f"   [{bar:<50}]")

                if step.get("metadata"):
                    lines.append(f"   Metadata: {step['metadata']}")

                lines.append("")

        if profile.metadata:
            lines.append("Query Metadata:")
            for key, value in profile.metadata.items():
                lines.append(f"  {key}: {value}")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    def visualize_comparison(self, profiles: List[QueryProfile]) -> str:
        """
        Visualize comparison of multiple query profiles

        Args:
            profiles: List of profiles to compare

        Returns:
            Text visualization comparing profiles
        """
        if not profiles:
            return "No profiles to compare"

        lines = []
        lines.append("=" * 60)
        lines.append("QUERY PROFILE COMPARISON")
        lines.append("=" * 60)

        # Summary table
        lines.append(f"{'Query ID':<20} {'Type':<15} {'Duration (ms)':<15}")
        lines.append("-" * 60)

        for profile in profiles:
            duration = f"{profile.duration_ms:.2f}" if profile.duration_ms else "N/A"
            lines.append(f"{profile.query_id:<20} {profile.query_type:<15} {duration:<15}")

        lines.append("")

        # Statistics
        durations = [p.duration_ms for p in profiles if p.duration_ms]
        if durations:
            lines.append("Statistics:")
            lines.append(f"  Average: {sum(durations) / len(durations):.2f}ms")
            lines.append(f"  Min: {min(durations):.2f}ms")
            lines.append(f"  Max: {max(durations):.2f}ms")

        lines.append("=" * 60)
        return "\n".join(lines)

    def export_to_json(self, profile: QueryProfile) -> Dict[str, Any]:
        """
        Export profile to JSON format

        Args:
            profile: Query profile to export

        Returns:
            Dictionary representation suitable for JSON export
        """
        return profile.to_dict()

    def generate_flamegraph_data(self, profile: QueryProfile) -> List[Dict[str, Any]]:
        """
        Generate data for flamegraph visualization

        Args:
            profile: Query profile

        Returns:
            List of flamegraph data points
        """
        data = []

        for step in profile.steps:
            data.append(
                {
                    "name": step["name"],
                    "value": step["duration_ms"],
                    "percentage": ((step["duration_ms"] / profile.duration_ms * 100) if profile.duration_ms else 0),
                }
            )

        return data
