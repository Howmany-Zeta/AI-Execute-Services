"""
Community Analytics

Tracks decision patterns, member participation, community health metrics,
and collaboration effectiveness.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .community_manager import CommunityManager
from collections import defaultdict

from .models.community_models import DecisionStatus

logger = logging.getLogger(__name__)


class CommunityAnalytics:
    """
    Analytics engine for tracking community health and effectiveness.
    """

    def __init__(self, community_manager: Optional["CommunityManager"] = None) -> None:
        """
        Initialize community analytics.

        Args:
            community_manager: Reference to the community manager
        """
        self.community_manager = community_manager

        # Analytics caches
        self._decision_patterns_cache: Dict[str, Any] = {}
        self._participation_cache: Dict[str, Any] = {}
        self._health_metrics_cache: Dict[str, Any] = {}

        logger.info("Community analytics initialized")

    def get_decision_analytics(self, community_id: str, time_range_days: int = 30) -> Dict[str, Any]:
        """
        Get decision analytics for a community.

        Args:
            community_id: ID of the community
            time_range_days: Time range for analytics in days

        Returns:
            Decision analytics data
        """
        if not self.community_manager:
            return {}

        community = self.community_manager.communities.get(community_id)
        if not community:
            return {}

        cutoff_date = datetime.utcnow() - timedelta(days=time_range_days)

        # Collect decisions within time range
        decisions = []
        for decision in self.community_manager.decisions.values():
            if decision.created_at >= cutoff_date:
                # Check if decision belongs to this community
                if decision.proposer_id in community.members:
                    decisions.append(decision)

        # Calculate decision metrics
        total_decisions = len(decisions)
        approved = sum(1 for d in decisions if d.status == DecisionStatus.APPROVED)
        rejected = sum(1 for d in decisions if d.status == DecisionStatus.REJECTED)
        pending = sum(1 for d in decisions if d.status in [DecisionStatus.PROPOSED, DecisionStatus.VOTING])

        # Calculate average time to decision
        decision_times = []
        for decision in decisions:
            if decision.status in [
                DecisionStatus.APPROVED,
                DecisionStatus.REJECTED,
            ]:
                if decision.implemented_at or decision.created_at:
                    end_time = decision.implemented_at or datetime.utcnow()
                    duration = (end_time - decision.created_at).total_seconds() / 3600  # hours
                    decision_times.append(duration)

        avg_decision_time = sum(decision_times) / len(decision_times) if decision_times else 0

        # Decision types distribution
        decision_types: Dict[str, int] = defaultdict(int)
        for decision in decisions:
            decision_types[decision.decision_type] += 1

        # Approval rate by type
        approval_by_type = {}
        for dtype in decision_types.keys():
            type_decisions = [d for d in decisions if d.decision_type == dtype]
            type_approved = sum(1 for d in type_decisions if d.status == DecisionStatus.APPROVED)
            approval_by_type[dtype] = type_approved / len(type_decisions) if type_decisions else 0

        analytics = {
            "community_id": community_id,
            "time_range_days": time_range_days,
            "total_decisions": total_decisions,
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
            "approval_rate": (approved / total_decisions if total_decisions > 0 else 0),
            "rejection_rate": (rejected / total_decisions if total_decisions > 0 else 0),
            "average_decision_time_hours": avg_decision_time,
            "decision_types": dict(decision_types),
            "approval_rate_by_type": approval_by_type,
            "decision_velocity": (total_decisions / time_range_days if time_range_days > 0 else 0),
        }

        return analytics

    def get_member_participation_analytics(self, community_id: str, time_range_days: int = 30) -> Dict[str, Any]:
        """
        Get member participation analytics.

        Args:
            community_id: ID of the community
            time_range_days: Time range for analytics in days

        Returns:
            Participation analytics data
        """
        if not self.community_manager:
            return {}

        community = self.community_manager.communities.get(community_id)
        if not community:
            return {}

        cutoff_date = datetime.utcnow() - timedelta(days=time_range_days)

        # Member participation metrics
        member_metrics = {}
        for member_id in community.members:
            member = self.community_manager.members.get(member_id)
            if not member:
                continue

            # Count votes
            votes_cast = 0
            proposals_made = 0

            for decision in self.community_manager.decisions.values():
                if decision.created_at >= cutoff_date:
                    if member_id in decision.votes_for or member_id in decision.votes_against or member_id in decision.abstentions:
                        votes_cast += 1
                    if decision.proposer_id == member_id:
                        proposals_made += 1

            # Count resources contributed
            resources_created = sum(1 for resource in self.community_manager.resources.values() if resource.owner_id == member_id and resource.created_at >= cutoff_date)

            member_metrics[member_id] = {
                "agent_id": member.agent_id,
                "community_role": member.community_role.value,
                "votes_cast": votes_cast,
                "proposals_made": proposals_made,
                "resources_created": resources_created,
                "contribution_score": member.contribution_score,
                "reputation": member.reputation,
                "is_active": member.is_active,
                "participation_level": member.participation_level,
            }

        # Calculate aggregate metrics
        total_members = len(member_metrics)
        active_members = sum(1 for m in member_metrics.values() if m.get("is_active", False))
        total_votes = sum(int(m.get("votes_cast", 0)) for m in member_metrics.values())
        total_proposals = sum(int(m.get("proposals_made", 0)) for m in member_metrics.values())
        total_resources = sum(int(m.get("resources_created", 0)) for m in member_metrics.values())

        # Identify top contributors
        top_voters = sorted(
            member_metrics.items(),
            key=lambda x: x[1]["votes_cast"],
            reverse=True,
        )[:5]

        top_proposers = sorted(
            member_metrics.items(),
            key=lambda x: x[1]["proposals_made"],
            reverse=True,
        )[:5]

        top_contributors = sorted(
            member_metrics.items(),
            key=lambda x: x[1]["contribution_score"],
            reverse=True,
        )[:5]

        analytics = {
            "community_id": community_id,
            "time_range_days": time_range_days,
            "total_members": total_members,
            "active_members": active_members,
            "activity_rate": (active_members / total_members if total_members > 0 else 0),
            "total_votes_cast": total_votes,
            "total_proposals_made": total_proposals,
            "total_resources_created": total_resources,
            "average_votes_per_member": (total_votes / total_members if total_members > 0 else 0),
            "average_proposals_per_member": (total_proposals / total_members if total_members > 0 else 0),
            "member_metrics": member_metrics,
            "top_voters": [{"member_id": mid, **metrics} for mid, metrics in top_voters],
            "top_proposers": [{"member_id": mid, **metrics} for mid, metrics in top_proposers],
            "top_contributors": [{"member_id": mid, **metrics} for mid, metrics in top_contributors],
        }

        return analytics

    def get_community_health_metrics(self, community_id: str) -> Dict[str, Any]:
        """
        Get comprehensive community health metrics.

        Args:
            community_id: ID of the community

        Returns:
            Health metrics data
        """
        if not self.community_manager:
            return {}

        community = self.community_manager.communities.get(community_id)
        if not community:
            return {}

        # Member health
        total_members = len(community.members)
        active_members = sum(1 for mid in community.members if self.community_manager.members.get(mid) and self.community_manager.members[mid].is_active)

        # Leadership health
        has_leaders = len(community.leaders) > 0
        has_coordinators = len(community.coordinators) > 0
        ((len(community.leaders) + len(community.coordinators)) / total_members if total_members > 0 else 0)

        # Activity health
        recent_activity_days = 7
        recent_cutoff = datetime.utcnow() - timedelta(days=recent_activity_days)

        recent_decisions = sum(1 for d in self.community_manager.decisions.values() if d.created_at >= recent_cutoff and d.proposer_id in community.members)

        recent_resources = sum(1 for rid in community.shared_resources if self.community_manager.resources.get(rid) and self.community_manager.resources[rid].created_at >= recent_cutoff)

        # Diversity metrics
        role_distribution: Dict[str, int] = defaultdict(int)
        for member_id in community.members:
            member = self.community_manager.members.get(member_id)
            if member:
                role_distribution[member.community_role.value] += 1

        role_diversity = len(role_distribution) / 5  # Max 5 role types

        # Collaboration score (from community model)
        collaboration_score = community.collaboration_score

        # Calculate overall health score (0-100)
        health_components = {
            "member_activity": ((active_members / total_members * 100) if total_members > 0 else 0),
            "leadership": (100 if has_leaders and has_coordinators else 50 if has_leaders or has_coordinators else 0),
            "recent_activity": min((recent_decisions + recent_resources) * 10, 100),
            "role_diversity": role_diversity * 100,
            "collaboration": collaboration_score * 100,
        }

        overall_health = sum(health_components.values()) / len(health_components)

        # Determine health status
        if overall_health >= 80:
            health_status = "excellent"
        elif overall_health >= 60:
            health_status = "good"
        elif overall_health >= 40:
            health_status = "fair"
        elif overall_health >= 20:
            health_status = "poor"
        else:
            health_status = "critical"

        # Recommendations
        recommendations = []
        if total_members == 0:
            recommendations.append("Add members to the community to begin collaboration")
        elif active_members / total_members < 0.5:
            recommendations.append("Increase member engagement through targeted activities")
        if not has_leaders:
            recommendations.append("Assign community leaders for better coordination")
        if recent_decisions + recent_resources < 3:
            recommendations.append("Encourage more community activity and collaboration")
        if role_diversity < 0.6:
            recommendations.append("Improve role diversity by adding members with different roles")

        metrics = {
            "community_id": community_id,
            "community_name": community.name,
            "overall_health_score": round(overall_health, 2),
            "health_status": health_status,
            "health_components": health_components,
            "member_statistics": {
                "total": total_members,
                "active": active_members,
                "inactive": total_members - active_members,
                "leaders": len(community.leaders),
                "coordinators": len(community.coordinators),
            },
            "activity_statistics": {
                "recent_decisions": recent_decisions,
                "recent_resources": recent_resources,
                "total_decisions": community.decision_count,
                "total_resources": community.resource_count,
            },
            "diversity_metrics": {
                "role_distribution": dict(role_distribution),
                "role_diversity_score": round(role_diversity, 2),
            },
            "collaboration_score": collaboration_score,
            "recommendations": recommendations,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return metrics

    def get_collaboration_effectiveness(self, community_id: str, time_range_days: int = 30) -> Dict[str, Any]:
        """
        Get collaboration effectiveness metrics.

        Args:
            community_id: ID of the community
            time_range_days: Time range for analytics in days

        Returns:
            Collaboration effectiveness data
        """
        if not self.community_manager:
            return {}

        # Get decision and participation analytics
        decision_analytics = self.get_decision_analytics(community_id, time_range_days)
        participation_analytics = self.get_member_participation_analytics(community_id, time_range_days)

        # Calculate effectiveness metrics
        decision_efficiency = decision_analytics.get("decision_velocity", 0) * 10
        approval_effectiveness = decision_analytics.get("approval_rate", 0) * 100
        participation_rate = participation_analytics.get("activity_rate", 0) * 100

        # Combined effectiveness score
        effectiveness_score = decision_efficiency * 0.3 + approval_effectiveness * 0.4 + participation_rate * 0.3

        # Determine effectiveness level
        if effectiveness_score >= 80:
            effectiveness_level = "highly_effective"
        elif effectiveness_score >= 60:
            effectiveness_level = "effective"
        elif effectiveness_score >= 40:
            effectiveness_level = "moderately_effective"
        else:
            effectiveness_level = "needs_improvement"

        # Identify strengths and weaknesses
        strengths = []
        weaknesses = []

        if decision_efficiency >= 8:
            strengths.append("High decision velocity")
        else:
            weaknesses.append("Low decision-making speed")

        if approval_effectiveness >= 70:
            strengths.append("High approval rate")
        else:
            weaknesses.append("Low approval rate - may indicate alignment issues")

        if participation_rate >= 70:
            strengths.append("Strong member participation")
        else:
            weaknesses.append("Low member participation")

        metrics = {
            "community_id": community_id,
            "time_range_days": time_range_days,
            "effectiveness_score": round(effectiveness_score, 2),
            "effectiveness_level": effectiveness_level,
            "component_scores": {
                "decision_efficiency": round(decision_efficiency, 2),
                "approval_effectiveness": round(approval_effectiveness, 2),
                "participation_rate": round(participation_rate, 2),
            },
            "strengths": strengths,
            "weaknesses": weaknesses,
            "decision_summary": {
                "velocity": decision_analytics.get("decision_velocity", 0),
                "approval_rate": decision_analytics.get("approval_rate", 0),
                "avg_time_hours": decision_analytics.get("average_decision_time_hours", 0),
            },
            "participation_summary": {
                "active_members": participation_analytics.get("active_members", 0),
                "total_members": participation_analytics.get("total_members", 0),
                "avg_votes_per_member": participation_analytics.get("average_votes_per_member", 0),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        return metrics

    def get_comprehensive_report(self, community_id: str, time_range_days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive analytics report for a community.

        Args:
            community_id: ID of the community
            time_range_days: Time range for analytics in days

        Returns:
            Comprehensive analytics report
        """
        report = {
            "community_id": community_id,
            "report_date": datetime.utcnow().isoformat(),
            "time_range_days": time_range_days,
            "decision_analytics": self.get_decision_analytics(community_id, time_range_days),
            "participation_analytics": self.get_member_participation_analytics(community_id, time_range_days),
            "health_metrics": self.get_community_health_metrics(community_id),
            "collaboration_effectiveness": self.get_collaboration_effectiveness(community_id, time_range_days),
        }

        return report
