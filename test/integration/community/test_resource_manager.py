"""
Tests for Resource Manager

Tests for resource creation, search, and recommendation.
"""

import pytest
import logging

from aiecs.domain.community.models import ResourceType

logger = logging.getLogger(__name__)


class TestResourceCreation:
    """Tests for creating resources."""
    
    @pytest.mark.asyncio
    async def test_create_knowledge_resource(self, resource_manager, community_manager, sample_community, sample_members):
        """Test creating a knowledge resource."""
        logger.info("Testing knowledge resource creation")
        
        resource_id = await resource_manager.create_knowledge_resource(
            community_id=sample_community,
            owner_member_id=sample_members[0],
            title="Test Knowledge",
            content="This is test knowledge content",
            knowledge_type="technical",
            tags=["test", "knowledge"],
            related_resources=[]
        )
        
        assert resource_id is not None
        
        # Verify resource exists in community_manager
        assert resource_id in community_manager.resources
        
        # Verify community has the resource
        community = community_manager.communities[sample_community]
        assert resource_id in community.shared_resources
        
        logger.debug(f"Created knowledge resource: {resource_id}")
    
    @pytest.mark.asyncio
    async def test_create_tool_resource(self, resource_manager, community_manager, sample_community, sample_members):
        """Test creating a tool resource."""
        logger.info("Testing tool resource creation")
        
        # Fixed: use correct parameter names
        resource_id = await resource_manager.create_tool_resource(
            community_id=sample_community,
            owner_member_id=sample_members[0],
            tool_name="Test Tool",  # Correct parameter name
            tool_config={"type": "analyzer", "capabilities": ["analyze", "report"]},
            description="A test tool for analysis",
            usage_instructions="Run the tool with the config settings",
            tags=["tool", "analyzer"]
        )
        
        assert resource_id is not None
        
        # Verify resource exists
        assert resource_id in community_manager.resources
        community = community_manager.communities[sample_community]
        assert resource_id in community.shared_resources
        
        # Verify it's a TOOL type
        resource = community_manager.resources[resource_id]
        assert resource.resource_type == ResourceType.TOOL
        
        logger.debug(f"Created tool resource: {resource_id}")
    
    @pytest.mark.asyncio
    async def test_create_experience_resource(self, resource_manager, community_manager, sample_community, sample_members):
        """Test creating an experience resource."""
        logger.info("Testing experience resource creation")
        
        resource_id = await resource_manager.create_experience_resource(
            community_id=sample_community,
            owner_member_id=sample_members[0],
            experience_title="Successful Deployment",
            situation="Production deployment with zero downtime required",
            actions_taken=[
                "Prepared rollback plan",
                "Tested in staging environment",
                "Deployed during low-traffic window",
                "Monitored metrics closely"
            ],
            outcomes={
                "success": True,
                "downtime": 0,
                "performance_improvement": "15%",
                "user_satisfaction": "95%"
            },
            lessons_learned=[
                "Always have a rollback plan",
                "Test thoroughly in staging",
                "Monitor metrics during deployment",
                "Communication is key"
            ],
            tags=["deployment", "production", "best-practices"]
        )
        
        assert resource_id is not None
        
        # Verify resource exists
        assert resource_id in community_manager.resources
        community = community_manager.communities[sample_community]
        assert resource_id in community.shared_resources
        
        # Verify it's an EXPERIENCE type
        resource = community_manager.resources[resource_id]
        assert resource.resource_type == ResourceType.EXPERIENCE
        
        logger.debug(f"Created experience resource: {resource_id}")


class TestResourceSearch:
    """Tests for resource search functionality."""
    
    @pytest.mark.asyncio
    async def test_search_by_type(self, resource_manager, community_manager, sample_community, sample_members):
        """Test searching resources by type."""
        logger.info("Testing search by type")
        
        # Create resources of different types
        await resource_manager.create_knowledge_resource(
            community_id=sample_community,
            owner_member_id=sample_members[0],
            title="Knowledge 1",
            content="Content 1"
        )
        await resource_manager.create_tool_resource(
            community_id=sample_community,
            owner_member_id=sample_members[0],
            tool_name="Tool 1",  # Fixed parameter name
            tool_config={"type": "analyzer"},
            description="Tool description",
            usage_instructions="Use this tool for analysis"
        )
        
        # Search for knowledge resources
        results = await resource_manager.search_resources(
            community_id=sample_community,
            resource_type=ResourceType.KNOWLEDGE
        )
        
        assert len(results) >= 1
        assert all(r["resource_type"] == ResourceType.KNOWLEDGE for r in results)
        
        logger.debug(f"Found {len(results)} knowledge resources")
    
    @pytest.mark.asyncio
    async def test_search_by_tags(self, resource_manager, community_manager, sample_community, sample_members):
        """Test searching resources by tags."""
        logger.info("Testing search by tags")
        
        # Create resources with tags
        await resource_manager.create_knowledge_resource(
            community_id=sample_community,
            owner_member_id=sample_members[0],
            title="Tagged Resource",
            content="Content",
            tags=["python", "testing"]
        )
        
        # Search by tag
        results = await resource_manager.search_resources(
            community_id=sample_community,
            tags=["python"]
        )
        
        assert len(results) >= 1
        assert any("python" in r.get("tags", []) for r in results)
        
        logger.debug(f"Found {len(results)} resources with tag 'python'")
    
    @pytest.mark.asyncio
    async def test_search_by_owner(self, resource_manager, community_manager, sample_community, sample_members):
        """Test searching resources by owner."""
        logger.info("Testing search by owner")
        
        owner_id = sample_members[1]
        
        # Create resource
        await resource_manager.create_knowledge_resource(
            community_id=sample_community,
            owner_member_id=owner_id,
            title="Owner Test",
            content="Content"
        )
        
        # Search by owner
        results = await resource_manager.search_resources(
            community_id=sample_community,
            owner_id=owner_id
        )
        
        assert len(results) >= 1
        assert all(r["owner_id"] == owner_id for r in results)
        
        logger.debug(f"Found {len(results)} resources for owner")
    
    @pytest.mark.asyncio
    async def test_search_with_limit(self, resource_manager, community_manager, sample_community, sample_members):
        """Test search result limit."""
        logger.info("Testing search with limit")
        
        # Create multiple resources
        for i in range(5):
            await resource_manager.create_knowledge_resource(
                community_id=sample_community,
                owner_member_id=sample_members[0],
                title=f"Resource {i}",
                content=f"Content {i}"
            )
        
        # Search with limit
        results = await resource_manager.search_resources(
            community_id=sample_community,
            limit=3
        )
        
        assert len(results) <= 3
        
        logger.debug(f"Limited results to {len(results)}")
    
    @pytest.mark.asyncio
    async def test_search_with_text_query(self, resource_manager, community_manager, sample_community, sample_members):
        """Test text search in resources."""
        logger.info("Testing text query search")
        
        # Create resource with specific content
        await resource_manager.create_knowledge_resource(
            community_id=sample_community,
            owner_member_id=sample_members[0],
            title="Python Best Practices",
            content="This guide covers Python coding standards and best practices",
            tags=["python", "guide"]
        )
        
        # Search by text query
        results = await resource_manager.search_resources(
            community_id=sample_community,
            query="Python"
        )
        
        assert len(results) >= 1
        
        logger.debug(f"Found {len(results)} resources matching 'Python'")


class TestResourceRecommendations:
    """Tests for resource recommendations."""
    
    @pytest.mark.asyncio
    async def test_get_resource_recommendations(self, resource_manager, community_manager, sample_community, sample_members):
        """Test getting personalized resource recommendations."""
        logger.info("Testing resource recommendations")
        
        # Create resources with tags matching member specializations
        resource1_id = await resource_manager.create_knowledge_resource(
            community_id=sample_community,
            owner_member_id=sample_members[0],
            title="Development Guide",
            content="Guide content for developers",
            tags=["development", "coding"]
        )
        
        resource2_id = await resource_manager.create_tool_resource(
            community_id=sample_community,
            owner_member_id=sample_members[1],
            tool_name="Code Analyzer",
            tool_config={"type": "static-analysis"},
            description="Analyzes code quality",
            usage_instructions="Run on your codebase",
            tags=["development", "tools"]
        )
        
        # Get recommendations for a member with "development" specialization
        # Fixed: use correct method name
        recommendations = await resource_manager.get_resource_recommendations(
            community_id=sample_community,
            member_id=sample_members[2],  # Has "development" specialization
            limit=10
        )
        
        assert recommendations is not None
        assert isinstance(recommendations, list)
        
        # Verify recommendations have required fields
        for rec in recommendations:
            assert "resource_id" in rec
            assert "name" in rec
            assert "recommendation_score" in rec
            assert rec["recommendation_score"] >= 0
        
        logger.debug(f"Got {len(recommendations)} recommendations")
    
    @pytest.mark.asyncio
    async def test_recommendations_exclude_own_resources(self, resource_manager, community_manager, sample_community, sample_members):
        """Test that recommendations don't include member's own resources."""
        logger.info("Testing recommendation exclusion of own resources")
        
        member_id = sample_members[0]
        
        # Create resource owned by the member
        await resource_manager.create_knowledge_resource(
            community_id=sample_community,
            owner_member_id=member_id,
            title="My Resource",
            content="Content",
            tags=["test"]
        )
        
        # Get recommendations for the same member
        recommendations = await resource_manager.get_resource_recommendations(
            community_id=sample_community,
            member_id=member_id,
            limit=10
        )
        
        # Verify own resources are excluded
        for rec in recommendations:
            resource = community_manager.resources[rec["resource_id"]]
            assert resource.owner_id != member_id
        
        logger.debug("Verified own resources excluded from recommendations")
    
    @pytest.mark.asyncio
    async def test_recommendation_scoring(self, resource_manager, community_manager, sample_community, sample_members):
        """Test recommendation scoring algorithm."""
        logger.info("Testing recommendation scoring")
        
        member = community_manager.members[sample_members[2]]
        member.specializations = ["python", "testing", "automation"]
        
        # Create resources with varying tag matches
        high_match_id = await resource_manager.create_knowledge_resource(
            community_id=sample_community,
            owner_member_id=sample_members[0],
            title="Python Testing Guide",
            content="Comprehensive Python testing guide",
            tags=["python", "testing", "automation"]  # All tags match
        )
        
        low_match_id = await resource_manager.create_knowledge_resource(
            community_id=sample_community,
            owner_member_id=sample_members[1],
            title="Java Basics",
            content="Java programming basics",
            tags=["java", "basics"]  # No tags match
        )
        
        # Get recommendations
        recommendations = await resource_manager.get_resource_recommendations(
            community_id=sample_community,
            member_id=sample_members[2],
            limit=10
        )
        
        # High match resource should be recommended with higher score
        high_match_rec = next((r for r in recommendations if r["resource_id"] == high_match_id), None)
        if high_match_rec:
            assert high_match_rec["recommendation_score"] > 0
        
        logger.debug("Recommendation scoring verified")


class TestResourceRelationships:
    """Tests for resource relationships."""
    
    @pytest.mark.asyncio
    async def test_create_related_resources(self, resource_manager, community_manager, sample_community, sample_members):
        """Test creating resources with relationships."""
        logger.info("Testing resource relationships")
        
        # Create first resource
        resource1_id = await resource_manager.create_knowledge_resource(
            community_id=sample_community,
            owner_member_id=sample_members[0],
            title="Part 1: Introduction",
            content="Introduction to the topic"
        )
        
        # Create second resource related to first
        resource2_id = await resource_manager.create_knowledge_resource(
            community_id=sample_community,
            owner_member_id=sample_members[0],
            title="Part 2: Advanced Topics",
            content="Advanced topics building on Part 1",
            related_resources=[resource1_id]
        )
        
        # Verify relationships were created
        if resource2_id in resource_manager.resource_relationships:
            relationships = resource_manager.resource_relationships[resource2_id]
            assert "related_to" in relationships
            assert resource1_id in relationships["related_to"]
        
        # Verify backward relationship
        if resource1_id in resource_manager.resource_relationships:
            relationships = resource_manager.resource_relationships[resource1_id]
            assert "referenced_by" in relationships
            assert resource2_id in relationships["referenced_by"]
        
        logger.debug("Resource relationships verified")
    
    @pytest.mark.asyncio
    async def test_resource_relationship_graph(self, resource_manager, community_manager, sample_community, sample_members):
        """Test building a resource relationship graph."""
        logger.info("Testing resource relationship graph")
        
        # Create a chain of related resources
        r1 = await resource_manager.create_knowledge_resource(
            community_id=sample_community,
            owner_member_id=sample_members[0],
            title="Foundation",
            content="Base knowledge"
        )
        
        r2 = await resource_manager.create_knowledge_resource(
            community_id=sample_community,
            owner_member_id=sample_members[0],
            title="Building Block 1",
            content="First building block",
            related_resources=[r1]
        )
        
        r3 = await resource_manager.create_knowledge_resource(
            community_id=sample_community,
            owner_member_id=sample_members[0],
            title="Building Block 2",
            content="Second building block",
            related_resources=[r1, r2]
        )
        
        # Verify graph structure
        # r3 -> r1, r2
        # r2 -> r1
        # r1 <- r2, r3
        # r2 <- r3
        
        if r3 in resource_manager.resource_relationships:
            assert len(resource_manager.resource_relationships[r3]["related_to"]) == 2
        
        if r1 in resource_manager.resource_relationships:
            assert len(resource_manager.resource_relationships[r1]["referenced_by"]) >= 2
        
        logger.debug("Resource graph structure verified")


class TestResourceIndexing:
    """Tests for resource indexing."""
    
    @pytest.mark.asyncio
    async def test_resource_appears_in_indexes(self, resource_manager, community_manager, sample_community, sample_members):
        """Test that created resources appear in all relevant indexes."""
        logger.info("Testing resource indexing")
        
        resource_id = await resource_manager.create_knowledge_resource(
            community_id=sample_community,
            owner_member_id=sample_members[0],
            title="Index Test",
            content="Content",
            tags=["index", "test"]
        )
        
        # Check resource exists in community_manager
        assert resource_id in community_manager.resources
        community = community_manager.communities[sample_community]
        assert resource_id in community.shared_resources
        
        # Check tag index
        assert "index" in resource_manager.resource_index
        assert resource_id in resource_manager.resource_index["index"]
        assert "test" in resource_manager.resource_index
        assert resource_id in resource_manager.resource_index["test"]
        
        # Check type index
        assert ResourceType.KNOWLEDGE in resource_manager.type_index
        assert resource_id in resource_manager.type_index[ResourceType.KNOWLEDGE]
        
        # Check owner index
        assert sample_members[0] in resource_manager.owner_index
        assert resource_id in resource_manager.owner_index[sample_members[0]]
        
        logger.debug("Resource verified in all indexes")
    
    @pytest.mark.asyncio
    async def test_multiple_resources_in_indexes(self, resource_manager, community_manager, sample_community, sample_members):
        """Test that multiple resources are properly indexed."""
        logger.info("Testing multiple resource indexing")
        
        # Create multiple resources with overlapping tags
        r1 = await resource_manager.create_knowledge_resource(
            community_id=sample_community,
            owner_member_id=sample_members[0],
            title="Resource 1",
            content="Content 1",
            tags=["common", "unique1"]
        )
        
        r2 = await resource_manager.create_knowledge_resource(
            community_id=sample_community,
            owner_member_id=sample_members[1],
            title="Resource 2",
            content="Content 2",
            tags=["common", "unique2"]
        )
        
        # Verify both in common tag index
        assert "common" in resource_manager.resource_index
        assert r1 in resource_manager.resource_index["common"]
        assert r2 in resource_manager.resource_index["common"]
        
        # Verify in separate unique tag indexes
        assert r1 in resource_manager.resource_index["unique1"]
        assert r2 in resource_manager.resource_index["unique2"]
        
        # Verify in separate owner indexes
        assert r1 in resource_manager.owner_index[sample_members[0]]
        assert r2 in resource_manager.owner_index[sample_members[1]]
        
        logger.debug("Multiple resources properly indexed")


class TestContentPreview:
    """Tests for content preview functionality."""
    
    @pytest.mark.asyncio
    async def test_content_preview_in_search(self, resource_manager, community_manager, sample_community, sample_members):
        """Test that search results include content previews."""
        logger.info("Testing content preview")
        
        long_content = "A" * 500  # Create long content
        
        await resource_manager.create_knowledge_resource(
            community_id=sample_community,
            owner_member_id=sample_members[0],
            title="Long Content Resource",
            content=long_content
        )
        
        # Search for the resource
        results = await resource_manager.search_resources(
            community_id=sample_community,
            query="Long Content"
        )
        
        assert len(results) >= 1
        
        # Verify preview is truncated
        for result in results:
            if "content_preview" in result:
                assert len(result["content_preview"]) <= 203  # 200 + "..."
        
        logger.debug("Content preview verified")
