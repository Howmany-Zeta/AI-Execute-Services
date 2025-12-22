"""
Tests for CommunityBuilder

Comprehensive tests for the fluent interface community builder.
"""

import pytest
import logging
from datetime import datetime, timedelta

from aiecs.domain.community.community_builder import CommunityBuilder, builder
from aiecs.domain.community.models.community_models import GovernanceType, CommunityRole

logger = logging.getLogger(__name__)


class TestCommunityBuilderBasics:
    """Test basic builder functionality."""
    
    @pytest.mark.asyncio
    async def test_simple_community_creation(self, community_integration):
        """Test creating a simple community."""
        logger.info("Testing simple community creation")
        
        community_builder = CommunityBuilder(community_integration)
        community_id = await community_builder\
            .with_name("Test Community")\
            .with_description("A test community")\
            .build()
        
        assert community_id is not None
        community = community_integration.community_manager.communities[community_id]
        assert community.name == "Test Community"
        assert community.description == "A test community"
        assert community.governance_type == GovernanceType.DEMOCRATIC  # default
    
    @pytest.mark.asyncio
    async def test_builder_convenience_function(self, community_integration):
        """Test the builder() convenience function."""
        logger.info("Testing builder() convenience function")
        
        community_id = await builder(community_integration)\
            .with_name("Quick Community")\
            .build()
        
        assert community_id is not None
        community = community_integration.community_manager.communities[community_id]
        assert community.name == "Quick Community"
    
    @pytest.mark.asyncio
    async def test_missing_name_raises_error(self, community_integration):
        """Test that building without a name raises ValueError."""
        logger.info("Testing missing name error")
        
        with pytest.raises(ValueError, match="Community name is required"):
            await builder(community_integration)\
                .with_description("No name community")\
                .build()
    
    @pytest.mark.asyncio
    async def test_builder_reuse(self, community_integration):
        """Test that builder can be reused after build."""
        logger.info("Testing builder reuse")
        
        community_builder = CommunityBuilder(community_integration)
        
        # Build first community
        community_id_1 = await community_builder\
            .with_name("Community 1")\
            .with_description("First community")\
            .build()
        
        # Build second community with same builder
        community_id_2 = await community_builder\
            .with_name("Community 2")\
            .with_description("Second community")\
            .build()
        
        assert community_id_1 != community_id_2
        
        community_1 = community_integration.community_manager.communities[community_id_1]
        community_2 = community_integration.community_manager.communities[community_id_2]
        
        assert community_1.name == "Community 1"
        assert community_2.name == "Community 2"


class TestCommunityConfiguration:
    """Test community configuration options."""
    
    @pytest.mark.asyncio
    async def test_governance_type_configuration(self, community_integration):
        """Test setting different governance types."""
        logger.info("Testing governance type configuration")
        
        for governance_type in [GovernanceType.CONSENSUS, GovernanceType.HIERARCHICAL, 
                               GovernanceType.HYBRID, GovernanceType.DEMOCRATIC]:
            community_id = await builder(community_integration)\
                .with_name(f"Community {governance_type.value}")\
                .with_governance(governance_type)\
                .build()
            
            community = community_integration.community_manager.communities[community_id]
            assert community.governance_type == governance_type
    
    @pytest.mark.asyncio
    async def test_single_role_addition(self, community_integration):
        """Test adding a single agent role."""
        logger.info("Testing single role addition")
        
        community_id = await builder(community_integration)\
            .with_name("Single Role Community")\
            .add_agent_role("researcher")\
            .build()
        
        assert community_id is not None
        # Roles are stored during build, check it was processed
    
    @pytest.mark.asyncio
    async def test_multiple_roles_addition(self, community_integration):
        """Test adding multiple agent roles."""
        logger.info("Testing multiple roles addition")
        
        roles = ["researcher", "analyst", "writer"]
        community_id = await builder(community_integration)\
            .with_name("Multi Role Community")\
            .add_agent_roles(roles)\
            .build()
        
        assert community_id is not None
    
    @pytest.mark.asyncio
    async def test_duplicate_role_prevention(self, community_integration):
        """Test that duplicate roles are prevented."""
        logger.info("Testing duplicate role prevention")
        
        community_builder = CommunityBuilder(community_integration)
        community_builder\
            .with_name("Dedupe Test")\
            .add_agent_role("researcher")\
            .add_agent_role("researcher")  # duplicate
        
        # Check internal state
        assert community_builder._agent_roles.count("researcher") == 1
    
    @pytest.mark.asyncio
    async def test_creator_agent_setting(self, community_integration):
        """Test setting creator agent."""
        logger.info("Testing creator agent setting")
        
        creator_id = "agent-creator-123"
        community_id = await builder(community_integration)\
            .with_name("Created Community")\
            .with_creator(creator_id)\
            .build()
        
        # Creator agent ID is passed to create_agent_community
        # The builder method successfully processes it
        assert community_id is not None
    
    @pytest.mark.asyncio
    async def test_metadata_addition(self, community_integration):
        """Test adding metadata to community."""
        logger.info("Testing metadata addition")
        
        community_id = await builder(community_integration)\
            .with_name("Metadata Community")\
            .with_metadata("priority", "high")\
            .with_metadata("department", "research")\
            .with_metadata("cost_center", "CC-123")\
            .build()
        
        community = community_integration.community_manager.communities[community_id]
        assert community.metadata["priority"] == "high"
        assert community.metadata["department"] == "research"
        assert community.metadata["cost_center"] == "CC-123"


class TestTemporaryCommunities:
    """Test temporary community creation."""
    
    @pytest.mark.asyncio
    async def test_temporary_community_creation(self, community_integration):
        """Test creating a temporary community with duration."""
        logger.info("Testing temporary community creation")
        
        community_id = await builder(community_integration)\
            .with_name("Temporary Community")\
            .with_duration(minutes=30, auto_cleanup=True)\
            .build()
        
        community = community_integration.community_manager.communities[community_id]
        assert community.name == "Temporary Community"
        # Temporary community should have metadata
        assert community.metadata.get("temporary") == True
        assert community.metadata.get("created_for_duration") == 30
        assert "cleanup_at" in community.metadata
    
    @pytest.mark.asyncio
    async def test_temporary_community_no_auto_cleanup(self, community_integration):
        """Test temporary community without auto cleanup."""
        logger.info("Testing temporary community without auto cleanup")
        
        community_id = await builder(community_integration)\
            .with_name("Manual Cleanup Community")\
            .with_duration(minutes=60, auto_cleanup=False)\
            .build()
        
        community = community_integration.community_manager.communities[community_id]
        # Temporary flag should still be set
        assert community.metadata.get("temporary") == True
        assert community.metadata.get("created_for_duration") == 60


class TestTemplates:
    """Test preset community templates."""
    
    @pytest.mark.asyncio
    async def test_research_template(self, community_integration):
        """Test research community template."""
        logger.info("Testing research template")
        
        community_id = await builder(community_integration)\
            .with_name("Research Team")\
            .use_template("research", 
                         topic="AI Safety",
                         questions=["How to ensure AI alignment?"],
                         methodologies=["theoretical analysis", "experiments"])\
            .build()
        
        community = community_integration.community_manager.communities[community_id]
        assert community.governance_type == GovernanceType.CONSENSUS
        assert community.metadata["type"] == "research"
        assert community.metadata["research_topic"] == "AI Safety"
        assert community.metadata["research_questions"] == ["How to ensure AI alignment?"]
        assert community.metadata["methodologies"] == ["theoretical analysis", "experiments"]
    
    @pytest.mark.asyncio
    async def test_research_template_default_roles(self, community_integration):
        """Test research template with default roles."""
        logger.info("Testing research template default roles")
        
        community_id = await builder(community_integration)\
            .with_name("Research Team Default")\
            .use_template("research", topic="LLMs")\
            .build()
        
        community = community_integration.community_manager.communities[community_id]
        assert community.metadata["research_topic"] == "LLMs"
    
    @pytest.mark.asyncio
    async def test_development_template(self, community_integration):
        """Test development community template."""
        logger.info("Testing development template")
        
        community_id = await builder(community_integration)\
            .with_name("Dev Team")\
            .use_template("development",
                         project_name="MyApp",
                         goal="Build scalable API",
                         deadline="2025-12-31",
                         tech_stack=["Python", "FastAPI", "PostgreSQL"])\
            .build()
        
        community = community_integration.community_manager.communities[community_id]
        assert community.governance_type == GovernanceType.HIERARCHICAL
        assert community.metadata["type"] == "development"
        assert community.metadata["project_name"] == "MyApp"
        assert community.metadata["project_goal"] == "Build scalable API"
        assert community.metadata["project_deadline"] == "2025-12-31"
        assert community.metadata["tech_stack"] == ["Python", "FastAPI", "PostgreSQL"]
    
    @pytest.mark.asyncio
    async def test_support_template(self, community_integration):
        """Test support community template."""
        logger.info("Testing support template")
        
        community_id = await builder(community_integration)\
            .with_name("Support Team")\
            .use_template("support",
                         support_level="L2",
                         coverage_hours="24/7")\
            .build()
        
        community = community_integration.community_manager.communities[community_id]
        assert community.governance_type == GovernanceType.DEMOCRATIC
        assert community.metadata["type"] == "support"
        assert community.metadata["support_level"] == "L2"
        assert community.metadata["coverage_hours"] == "24/7"
    
    @pytest.mark.asyncio
    async def test_creative_template(self, community_integration):
        """Test creative community template."""
        logger.info("Testing creative template")
        
        community_id = await builder(community_integration)\
            .with_name("Creative Team")\
            .use_template("creative",
                         project_type="Marketing Campaign",
                         style_guidelines="Modern, minimalist")\
            .build()
        
        community = community_integration.community_manager.communities[community_id]
        assert community.governance_type == GovernanceType.HYBRID
        assert community.metadata["type"] == "creative"
        assert community.metadata["project_type"] == "Marketing Campaign"
        assert community.metadata["style_guidelines"] == "Modern, minimalist"
    
    @pytest.mark.asyncio
    async def test_unknown_template_warning(self, community_integration, caplog):
        """Test that unknown template logs a warning."""
        logger.info("Testing unknown template warning")
        
        with caplog.at_level(logging.WARNING):
            community_id = await builder(community_integration)\
                .with_name("Unknown Template Community")\
                .use_template("unknown_template")\
                .build()
            
            assert "Unknown template: unknown_template" in caplog.text
        
        # Should still create community
        assert community_id is not None


class TestTemplateCustomization:
    """Test template customization options."""
    
    @pytest.mark.asyncio
    async def test_template_with_custom_roles(self, community_integration):
        """Test using template with custom roles override."""
        logger.info("Testing template with custom roles")
        
        custom_roles = ["senior_researcher", "junior_researcher", "data_scientist"]
        community_id = await builder(community_integration)\
            .with_name("Custom Research Team")\
            .use_template("research", 
                         roles=custom_roles,
                         topic="Quantum Computing")\
            .build()
        
        community = community_integration.community_manager.communities[community_id]
        assert community.metadata["research_topic"] == "Quantum Computing"
    
    @pytest.mark.asyncio
    async def test_template_with_additional_config(self, community_integration):
        """Test adding configuration after template."""
        logger.info("Testing template with additional config")
        
        community_id = await builder(community_integration)\
            .with_name("Extended Dev Team")\
            .use_template("development", project_name="SuperApp")\
            .add_agent_role("security_expert")\
            .with_metadata("security_level", "high")\
            .build()
        
        community = community_integration.community_manager.communities[community_id]
        assert community.metadata["project_name"] == "SuperApp"
        assert community.metadata["security_level"] == "high"
        assert community.metadata["type"] == "development"


class TestComplexScenarios:
    """Test complex builder scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_configuration_chain(self, community_integration):
        """Test a full configuration with all options."""
        logger.info("Testing full configuration chain")
        
        community_id = await builder(community_integration)\
            .with_name("Full Featured Community")\
            .with_description("A fully configured community")\
            .with_governance(GovernanceType.HYBRID)\
            .add_agent_roles(["role1", "role2", "role3"])\
            .with_creator("creator-agent-xyz")\
            .with_metadata("key1", "value1")\
            .with_metadata("key2", "value2")\
            .build()
        
        community = community_integration.community_manager.communities[community_id]
        assert community.name == "Full Featured Community"
        assert community.description == "A fully configured community"
        assert community.governance_type == GovernanceType.HYBRID
        assert community.metadata["key1"] == "value1"
        assert community.metadata["key2"] == "value2"
    
    @pytest.mark.asyncio
    async def test_temporary_community_with_template(self, community_integration):
        """Test combining temporary community with template."""
        logger.info("Testing temporary community with template")
        
        community_id = await builder(community_integration)\
            .with_name("Temporary Research Sprint")\
            .use_template("research", topic="Quick Analysis")\
            .with_duration(minutes=120, auto_cleanup=True)\
            .build()
        
        community = community_integration.community_manager.communities[community_id]
        assert community.metadata["type"] == "research"
        assert community.metadata["temporary"] == True
        assert community.metadata["research_topic"] == "Quick Analysis"
    
    @pytest.mark.asyncio
    async def test_all_templates_sequential(self, community_integration):
        """Test creating communities with all templates sequentially."""
        logger.info("Testing all templates sequentially")
        
        templates = ["research", "development", "support", "creative"]
        community_ids = []
        
        for template in templates:
            community_id = await builder(community_integration)\
                .with_name(f"{template.capitalize()} Community")\
                .use_template(template)\
                .build()
            
            community_ids.append(community_id)
        
        assert len(community_ids) == 4
        assert len(set(community_ids)) == 4  # All unique
        
        # Verify each has correct type
        for i, template in enumerate(templates):
            community = community_integration.community_manager.communities[community_ids[i]]
            assert community.metadata["type"] == template


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.mark.asyncio
    async def test_empty_description_uses_default(self, community_integration):
        """Test that empty description generates a default."""
        logger.info("Testing default description generation")
        
        community_id = await builder(community_integration)\
            .with_name("No Description Community")\
            .build()
        
        community = community_integration.community_manager.communities[community_id]
        assert community.description == "Community: No Description Community"
    
    @pytest.mark.asyncio
    async def test_empty_roles_list(self, community_integration):
        """Test creating community with no roles."""
        logger.info("Testing empty roles list")
        
        community_id = await builder(community_integration)\
            .with_name("No Roles Community")\
            .build()
        
        assert community_id is not None
        # Should create successfully even without roles
    
    @pytest.mark.asyncio
    async def test_metadata_overwrite(self, community_integration):
        """Test that metadata can be overwritten."""
        logger.info("Testing metadata overwrite")
        
        community_builder = CommunityBuilder(community_integration)
        community_builder\
            .with_name("Metadata Test")\
            .with_metadata("key", "value1")\
            .with_metadata("key", "value2")  # overwrite
        
        assert community_builder._metadata["key"] == "value2"
    
    @pytest.mark.asyncio
    async def test_long_community_name(self, community_integration):
        """Test creating community with very long name."""
        logger.info("Testing long community name")
        
        long_name = "A" * 200
        community_id = await builder(community_integration)\
            .with_name(long_name)\
            .build()
        
        community = community_integration.community_manager.communities[community_id]
        assert community.name == long_name
    
    @pytest.mark.asyncio
    async def test_special_characters_in_name(self, community_integration):
        """Test creating community with special characters in name."""
        logger.info("Testing special characters in name")
        
        special_name = "Test-Community_2025 (AI/ML) [Alpha]"
        community_id = await builder(community_integration)\
            .with_name(special_name)\
            .build()
        
        community = community_integration.community_manager.communities[community_id]
        assert community.name == special_name

