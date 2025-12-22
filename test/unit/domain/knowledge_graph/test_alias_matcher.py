"""
Unit tests for AliasMatcher

Tests alias-based entity matching, O(1) lookup,
and alias propagation during entity merge.
"""

import pytest

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.application.knowledge_graph.fusion.alias_matcher import (
    AliasMatcher,
    get_known_aliases,
    set_known_aliases,
    add_known_alias,
    merge_aliases,
)


class TestAliasMatcher:
    """Test AliasMatcher class"""

    @pytest.fixture
    def matcher(self):
        """Create AliasMatcher instance"""
        return AliasMatcher()

    @pytest.fixture
    def sample_entities(self):
        """Create sample entities for testing"""
        return [
            Entity(
                id="person_123",
                entity_type="Person",
                properties={
                    "name": "Albert Einstein",
                    "_known_aliases": ["A. Einstein", "Einstein"],
                },
            ),
            Entity(
                id="org_456",
                entity_type="Organization",
                properties={
                    "name": "Massachusetts Institute of Technology",
                    "_known_aliases": ["MIT"],
                },
            ),
            Entity(
                id="person_789",
                entity_type="Person",
                properties={
                    "name": "John Smith",
                    "_aliases": ["J. Smith"],  # Historical alias from merge
                },
            ),
        ]

    # --- Build Index ---

    @pytest.mark.asyncio
    async def test_build_index(self, matcher, sample_entities):
        """Test building alias index from entities"""
        count = await matcher.build_index(sample_entities)
        
        # Each entity has name + aliases
        # Einstein: 3 (name + 2 known)
        # MIT: 2 (name + 1 known)
        # Smith: 2 (name + 1 historical)
        assert count == 7

    @pytest.mark.asyncio
    async def test_build_index_empty(self, matcher):
        """Test building index with no entities"""
        count = await matcher.build_index([])
        assert count == 0

    # --- Lookup ---

    @pytest.mark.asyncio
    async def test_lookup_by_name(self, matcher, sample_entities):
        """Test lookup by entity name"""
        await matcher.build_index(sample_entities)
        
        match = await matcher.lookup("Albert Einstein")
        assert match is not None
        assert match.entity_id == "person_123"

    @pytest.mark.asyncio
    async def test_lookup_by_known_alias(self, matcher, sample_entities):
        """Test lookup by known alias"""
        await matcher.build_index(sample_entities)
        
        match = await matcher.lookup("A. Einstein")
        assert match is not None
        assert match.entity_id == "person_123"

    @pytest.mark.asyncio
    async def test_lookup_by_historical_alias(self, matcher, sample_entities):
        """Test lookup by historical alias from merge"""
        await matcher.build_index(sample_entities)
        
        match = await matcher.lookup("J. Smith")
        assert match is not None
        assert match.entity_id == "person_789"

    @pytest.mark.asyncio
    async def test_lookup_case_insensitive(self, matcher, sample_entities):
        """Test case-insensitive lookup"""
        await matcher.build_index(sample_entities)
        
        match = await matcher.lookup("albert einstein")
        assert match is not None
        assert match.entity_id == "person_123"
        
        match = await matcher.lookup("MIT")
        assert match is not None
        assert match.entity_id == "org_456"

    @pytest.mark.asyncio
    async def test_lookup_not_found(self, matcher, sample_entities):
        """Test lookup for nonexistent alias"""
        await matcher.build_index(sample_entities)
        
        match = await matcher.lookup("Unknown Person")
        assert match is None

    # --- Add Entity ---

    @pytest.mark.asyncio
    async def test_add_entity(self, matcher):
        """Test adding a single entity"""
        entity = Entity(
            id="person_999",
            entity_type="Person",
            properties={
                "name": "Marie Curie",
                "_known_aliases": ["M. Curie"],
            },
        )
        
        count = await matcher.add_entity(entity)
        assert count == 2  # name + alias
        
        match = await matcher.lookup("Marie Curie")
        assert match is not None
        assert match.entity_id == "person_999"

    # --- Remove Entity ---

    @pytest.mark.asyncio
    async def test_remove_entity(self, matcher, sample_entities):
        """Test removing entity aliases"""
        await matcher.build_index(sample_entities)

        # Verify entity exists
        match = await matcher.lookup("Albert Einstein")
        assert match is not None

        # Remove entity
        removed = await matcher.remove_entity("person_123")
        assert removed == 3  # name + 2 aliases

        # Verify removed
        match = await matcher.lookup("Albert Einstein")
        assert match is None
        match = await matcher.lookup("A. Einstein")
        assert match is None


class TestAliasPropagation:
    """Test alias propagation during entity merge"""

    @pytest.fixture
    def matcher(self):
        """Create AliasMatcher instance"""
        return AliasMatcher()

    @pytest.mark.asyncio
    async def test_propagate_aliases(self, matcher):
        """Test alias propagation from source to target"""
        # Create source and target entities
        source = Entity(
            id="person_dup",
            entity_type="Person",
            properties={
                "name": "A. Einstein",
                "_known_aliases": ["Einstein"],
            },
        )
        target = Entity(
            id="person_main",
            entity_type="Person",
            properties={
                "name": "Albert Einstein",
            },
        )

        # Add both to index
        await matcher.add_entity(source)
        await matcher.add_entity(target)

        # Verify source aliases exist
        match = await matcher.lookup("A. Einstein")
        assert match.entity_id == "person_dup"

        # Propagate aliases
        propagated = await matcher.propagate_aliases("person_dup", "person_main")
        assert propagated == 2  # name + alias

        # Verify aliases now point to target
        match = await matcher.lookup("A. Einstein")
        assert match.entity_id == "person_main"
        match = await matcher.lookup("Einstein")
        assert match.entity_id == "person_main"

    @pytest.mark.asyncio
    async def test_propagate_no_aliases(self, matcher):
        """Test propagation when source has no aliases"""
        propagated = await matcher.propagate_aliases("nonexistent", "target")
        assert propagated == 0

    @pytest.mark.asyncio
    async def test_get_entity_aliases(self, matcher):
        """Test getting all aliases for an entity"""
        entity = Entity(
            id="person_123",
            entity_type="Person",
            properties={
                "name": "Albert Einstein",
                "_known_aliases": ["A. Einstein", "Einstein"],
            },
        )

        await matcher.add_entity(entity)

        aliases = await matcher.get_entity_aliases("person_123")
        assert len(aliases) == 3
        assert "albert einstein" in aliases
        assert "a. einstein" in aliases
        assert "einstein" in aliases


class TestFindMatchingEntity:
    """Test finding entities by multiple candidate names"""

    @pytest.fixture
    def matcher(self):
        """Create AliasMatcher instance"""
        return AliasMatcher()

    @pytest.mark.asyncio
    async def test_find_first_match(self, matcher):
        """Test finding entity with first matching name"""
        entity = Entity(
            id="org_123",
            entity_type="Organization",
            properties={
                "name": "MIT",
            },
        )
        await matcher.add_entity(entity)

        # First name doesn't match, second does
        match = await matcher.find_matching_entity([
            "Unknown Org",
            "MIT",
            "Another Org",
        ])

        assert match is not None
        assert match.entity_id == "org_123"

    @pytest.mark.asyncio
    async def test_find_no_match(self, matcher):
        """Test when no candidate names match"""
        match = await matcher.find_matching_entity([
            "Unknown 1",
            "Unknown 2",
        ])
        assert match is None


class TestEntityAliasHelpers:
    """Test helper functions for entity alias management"""

    @pytest.fixture
    def entity(self):
        """Create sample entity"""
        return Entity(
            id="person_123",
            entity_type="Person",
            properties={"name": "John Doe"},
        )

    def test_get_known_aliases_empty(self, entity):
        """Test getting aliases when none exist"""
        aliases = get_known_aliases(entity)
        assert aliases == []

    def test_set_known_aliases(self, entity):
        """Test setting known aliases"""
        set_known_aliases(entity, ["J. Doe", "Johnny"])

        aliases = get_known_aliases(entity)
        assert len(aliases) == 2
        assert "J. Doe" in aliases
        assert "Johnny" in aliases

    def test_add_known_alias(self, entity):
        """Test adding a single alias"""
        add_known_alias(entity, "J. Doe")
        add_known_alias(entity, "Johnny")

        aliases = get_known_aliases(entity)
        assert len(aliases) == 2

    def test_add_known_alias_no_duplicates(self, entity):
        """Test that duplicate aliases are not added"""
        add_known_alias(entity, "J. Doe")
        add_known_alias(entity, "J. Doe")  # Duplicate

        aliases = get_known_aliases(entity)
        assert len(aliases) == 1


class TestMergeAliases:
    """Test alias merging during entity merge"""

    def test_merge_aliases_basic(self):
        """Test basic alias merge"""
        target = Entity(
            id="person_main",
            entity_type="Person",
            properties={
                "name": "Albert Einstein",
            },
        )
        source = Entity(
            id="person_dup",
            entity_type="Person",
            properties={
                "name": "A. Einstein",
                "_known_aliases": ["Einstein"],
            },
        )

        new_aliases = merge_aliases(target, source)

        assert len(new_aliases) == 2
        assert "A. Einstein" in new_aliases
        assert "Einstein" in new_aliases

        # Verify target was updated
        target_aliases = get_known_aliases(target)
        assert "A. Einstein" in target_aliases
        assert "Einstein" in target_aliases

    def test_merge_aliases_no_duplicates(self):
        """Test that duplicate aliases are not added during merge"""
        target = Entity(
            id="person_main",
            entity_type="Person",
            properties={
                "name": "Albert Einstein",
                "_known_aliases": ["Einstein"],  # Already has this alias
            },
        )
        source = Entity(
            id="person_dup",
            entity_type="Person",
            properties={
                "name": "A. Einstein",
                "_known_aliases": ["Einstein"],  # Duplicate
            },
        )

        new_aliases = merge_aliases(target, source)

        # Only A. Einstein is new
        assert len(new_aliases) == 1
        assert "A. Einstein" in new_aliases

    def test_merge_aliases_includes_historical(self):
        """Test that historical _aliases are included in merge"""
        target = Entity(
            id="person_main",
            entity_type="Person",
            properties={"name": "John Smith"},
        )
        source = Entity(
            id="person_dup",
            entity_type="Person",
            properties={
                "name": "J. Smith",
                "_aliases": ["Johnny"],  # Historical from previous merge
            },
        )

        new_aliases = merge_aliases(target, source)

        assert "J. Smith" in new_aliases
        assert "Johnny" in new_aliases

    def test_merge_aliases_skips_target_name(self):
        """Test that target's name is not added as alias"""
        target = Entity(
            id="person_main",
            entity_type="Person",
            properties={"name": "John Smith"},
        )
        source = Entity(
            id="person_dup",
            entity_type="Person",
            properties={
                "name": "john smith",  # Same as target (different case)
            },
        )

        new_aliases = merge_aliases(target, source)

        # Source name matches target name, should not be added
        assert len(new_aliases) == 0

