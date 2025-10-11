# Community Analytics

## Overview

The Community Analytics module provides comprehensive tracking and analysis capabilities for community health, member participation, decision patterns, and collaboration effectiveness. This module helps monitor and optimize community performance.

> **Status**: ✅ The `CommunityAnalytics` class is now **available in the public API**.

## CommunityAnalytics Class

### Initialization

```python
class CommunityAnalytics:
    def __init__(self, community_manager=None)
```

**Parameters:**
- `community_manager` (Optional): Reference to the community manager instance

### Key Features

1. **Decision Analytics** - Track decision patterns and effectiveness
2. **Participation Metrics** - Monitor member engagement and contributions
3. **Health Metrics** - Assess community health and vitality
4. **Collaboration Effectiveness** - Measure collaboration quality and outcomes

## Methods

### get_decision_analytics

Get comprehensive decision analytics for a community.

```python
def get_decision_analytics(
    self,
    community_id: str,
    time_range_days: int = 30
) -> Dict[str, Any]
```

**Parameters:**
- `community_id` (str): ID of the community
- `time_range_days` (int): Time range for analytics in days (default: 30)

**Returns:** Dictionary containing:
- `total_decisions`: Total number of decisions
- `approved`: Number of approved decisions
- `rejected`: Number of rejected decisions
- `pending`: Number of pending decisions
- `avg_decision_time`: Average time to reach a decision (hours)
- `decision_types`: Distribution of decision types
- `approval_by_type`: Approval rates by decision type
- `participation_rate`: Average member participation in voting
- `consensus_level`: Average consensus level achieved

**Example:**

```python
analytics = CommunityAnalytics(community_manager)
decision_metrics = analytics.get_decision_analytics("community_001", time_range_days=60)

print(f"Total decisions: {decision_metrics['total_decisions']}")
print(f"Approval rate: {decision_metrics['approved'] / decision_metrics['total_decisions']:.2%}")
print(f"Average decision time: {decision_metrics['avg_decision_time']:.1f} hours")
```

### get_participation_metrics

Get member participation metrics for a community.

```python
def get_participation_metrics(
    self,
    community_id: str,
    time_range_days: int = 30
) -> Dict[str, Any]
```

**Parameters:**
- `community_id` (str): ID of the community
- `time_range_days` (int): Time range for metrics in days (default: 30)

**Returns:** Dictionary containing:
- `active_members`: Number of active members
- `inactive_members`: Number of inactive members
- `participation_rate`: Overall participation rate
- `avg_contributions`: Average contributions per member
- `top_contributors`: List of top contributing members
- `engagement_score`: Community engagement score
- `participation_by_role`: Participation breakdown by role

**Example:**

```python
participation = analytics.get_participation_metrics("community_001")

print(f"Active members: {participation['active_members']}")
print(f"Participation rate: {participation['participation_rate']:.2%}")
print(f"Top contributors: {participation['top_contributors']}")
```

### get_community_health_metrics

Get overall community health metrics.

```python
def get_community_health_metrics(
    self,
    community_id: str
) -> Dict[str, Any]
```

**Parameters:**
- `community_id` (str): ID of the community

**Returns:** Dictionary containing:
- `health_score`: Overall community health score (0-100)
- `vitality`: Community vitality indicator
- `growth_rate`: Member growth rate
- `retention_rate`: Member retention rate
- `activity_level`: Activity level indicator
- `collaboration_quality`: Quality of collaboration
- `decision_effectiveness`: Decision-making effectiveness
- `resource_utilization`: Resource utilization rate
- `recommendations`: List of recommendations for improvement

**Example:**

```python
health = analytics.get_community_health_metrics("community_001")

print(f"Health score: {health['health_score']}/100")
print(f"Activity level: {health['activity_level']}")
print(f"Recommendations: {health['recommendations']}")
```

### get_collaboration_effectiveness

Measure collaboration effectiveness within the community.

```python
def get_collaboration_effectiveness(
    self,
    community_id: str,
    time_range_days: int = 30
) -> Dict[str, Any]
```

**Parameters:**
- `community_id` (str): ID of the community
- `time_range_days` (int): Time range for analysis in days (default: 30)

**Returns:** Dictionary containing:
- `collaboration_sessions`: Number of collaboration sessions
- `avg_session_duration`: Average session duration
- `session_completion_rate`: Session completion rate
- `collaboration_score`: Overall collaboration effectiveness score
- `resource_sharing_rate`: Rate of resource sharing
- `knowledge_sharing_score`: Knowledge sharing effectiveness
- `communication_quality`: Communication quality metrics

**Example:**

```python
effectiveness = analytics.get_collaboration_effectiveness("community_001")

print(f"Collaboration score: {effectiveness['collaboration_score']}/100")
print(f"Sessions completed: {effectiveness['collaboration_sessions']}")
print(f"Resource sharing rate: {effectiveness['resource_sharing_rate']:.2%}")
```

### get_member_analytics

Get detailed analytics for a specific member.

```python
def get_member_analytics(
    self,
    community_id: str,
    member_id: str,
    time_range_days: int = 30
) -> Dict[str, Any]
```

**Parameters:**
- `community_id` (str): ID of the community
- `member_id` (str): ID of the member
- `time_range_days` (int): Time range for analytics in days (default: 30)

**Returns:** Dictionary containing:
- `contribution_score`: Member's contribution score
- `participation_rate`: Member's participation rate
- `decisions_proposed`: Number of decisions proposed
- `votes_cast`: Number of votes cast
- `resources_shared`: Number of resources shared
- `collaboration_sessions`: Number of sessions participated in
- `reputation_score`: Member's reputation score
- `specializations`: Member's areas of expertise
- `activity_timeline`: Activity timeline data

**Example:**

```python
member_stats = analytics.get_member_analytics("community_001", "member_001")

print(f"Contribution score: {member_stats['contribution_score']}")
print(f"Decisions proposed: {member_stats['decisions_proposed']}")
print(f"Resources shared: {member_stats['resources_shared']}")
```

### get_trend_analysis

Get trend analysis for community metrics over time.

```python
def get_trend_analysis(
    self,
    community_id: str,
    metrics: List[str],
    time_range_days: int = 90
) -> Dict[str, List[Any]]
```

**Parameters:**
- `community_id` (str): ID of the community
- `metrics` (List[str]): List of metrics to analyze
- `time_range_days` (int): Time range for analysis in days (default: 90)

**Returns:** Dictionary mapping metric names to time-series data

**Available Metrics:**
- `member_count`: Number of members over time
- `activity_level`: Activity level over time
- `decision_rate`: Decision-making rate over time
- `participation_rate`: Participation rate over time
- `resource_creation`: Resource creation rate over time

**Example:**

```python
trends = analytics.get_trend_analysis(
    "community_001",
    metrics=["member_count", "activity_level", "decision_rate"],
    time_range_days=90
)

# Plot trends
import matplotlib.pyplot as plt

plt.plot(trends['member_count'], label='Members')
plt.plot(trends['activity_level'], label='Activity')
plt.legend()
plt.show()
```

## Analytics Metrics Reference

### Health Score Components

The community health score (0-100) is calculated from:

1. **Activity Level (25%)** - Recent activity frequency and intensity
2. **Participation Rate (25%)** - Member engagement in decisions and discussions
3. **Collaboration Quality (20%)** - Effectiveness of collaborative efforts
4. **Decision Effectiveness (15%)** - Quality and timeliness of decisions
5. **Resource Utilization (15%)** - Usage of shared resources and knowledge

### Vitality Indicators

- **Growing**: Increasing membership and activity
- **Stable**: Consistent membership and activity
- **Declining**: Decreasing membership or activity
- **Inactive**: Minimal recent activity

### Engagement Score Calculation

```
Engagement Score = (
    0.3 × Participation Rate +
    0.3 × Contribution Frequency +
    0.2 × Resource Sharing +
    0.2 × Collaboration Sessions
) × 100
```

## Usage Examples

### Complete Analytics Report

```python
async def generate_community_report(community_id: str):
    """Generate a comprehensive community analytics report."""
    
    analytics = CommunityAnalytics(community_manager)
    
    # Get all metrics
    decision_metrics = analytics.get_decision_analytics(community_id, time_range_days=30)
    participation = analytics.get_participation_metrics(community_id, time_range_days=30)
    health = analytics.get_community_health_metrics(community_id)
    effectiveness = analytics.get_collaboration_effectiveness(community_id, time_range_days=30)
    
    # Generate report
    report = {
        "community_id": community_id,
        "report_date": datetime.utcnow().isoformat(),
        "summary": {
            "health_score": health['health_score'],
            "vitality": health['vitality'],
            "active_members": participation['active_members'],
            "total_decisions": decision_metrics['total_decisions'],
            "collaboration_sessions": effectiveness['collaboration_sessions']
        },
        "decisions": decision_metrics,
        "participation": participation,
        "health": health,
        "collaboration": effectiveness,
        "recommendations": health['recommendations']
    }
    
    return report
```

### Real-time Monitoring

```python
async def monitor_community_health(community_id: str):
    """Monitor community health in real-time."""
    
    analytics = CommunityAnalytics(community_manager)
    
    while True:
        health = analytics.get_community_health_metrics(community_id)
        
        # Alert on low health score
        if health['health_score'] < 50:
            print(f"⚠️ WARNING: Community health score is low: {health['health_score']}")
            print(f"Recommendations: {health['recommendations']}")
        
        # Alert on declining vitality
        if health['vitality'] == "declining":
            print(f"⚠️ WARNING: Community vitality is declining")
        
        # Sleep for monitoring interval
        await asyncio.sleep(3600)  # Check every hour
```

### Member Performance Review

```python
async def review_member_performance(community_id: str, member_id: str):
    """Generate a performance review for a member."""
    
    analytics = CommunityAnalytics(community_manager)
    
    # Get member analytics for different time ranges
    month_stats = analytics.get_member_analytics(community_id, member_id, time_range_days=30)
    quarter_stats = analytics.get_member_analytics(community_id, member_id, time_range_days=90)
    
    review = {
        "member_id": member_id,
        "review_date": datetime.utcnow().isoformat(),
        "monthly_performance": month_stats,
        "quarterly_performance": quarter_stats,
        "growth": {
            "contribution": quarter_stats['contribution_score'] - month_stats['contribution_score'],
            "participation": quarter_stats['participation_rate'] - month_stats['participation_rate']
        },
        "strengths": _identify_strengths(month_stats),
        "areas_for_improvement": _identify_improvements(month_stats)
    }
    
    return review
```

## Import and Usage

The `CommunityAnalytics` class is now available in the public API:

```python
# Import from domain.community
from aiecs.domain.community import CommunityAnalytics

# Or import from domain
from aiecs.domain import CommunityAnalytics

# Initialize
analytics = CommunityAnalytics(community_manager)

# Use analytics methods
health = analytics.get_community_health_metrics("community_001")
```

## Notes

- Analytics data is cached for performance optimization
- Cache expiration can be configured per analytics instance
- Historical data storage depends on the underlying persistence layer
- Real-time metrics are computed on-demand
- Trend analysis requires sufficient historical data
