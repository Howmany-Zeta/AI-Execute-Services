"""
Unit tests for SkillRegistry.
"""

import pytest
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from aiecs.domain.agent.skills.registry import SkillRegistry, SkillRegistryError
from aiecs.domain.agent.skills.models import SkillDefinition, SkillMetadata


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset registry before and after each test."""
    SkillRegistry.reset_instance()
    yield
    SkillRegistry.reset_instance()


@pytest.fixture
def sample_skill():
    """Create a sample skill for testing."""
    metadata = SkillMetadata(
        name="test-skill",
        description="A test skill",
        version="1.0.0",
        tags=["test", "sample"],
        recommended_tools=["tool1", "tool2"]
    )
    return SkillDefinition(
        metadata=metadata,
        skill_path=Path("/path/to/skill")
    )


@pytest.fixture
def another_skill():
    """Create another sample skill for testing."""
    metadata = SkillMetadata(
        name="another-skill",
        description="Another test skill",
        version="2.0.0",
        tags=["python", "coding"],
        dependencies=["test-skill"]
    )
    return SkillDefinition(
        metadata=metadata,
        skill_path=Path("/path/to/another")
    )


class TestSkillRegistrySingleton:
    """Tests for singleton pattern."""
    
    def test_get_instance_returns_singleton(self):
        """Test that get_instance always returns same instance."""
        registry1 = SkillRegistry.get_instance()
        registry2 = SkillRegistry.get_instance()
        assert registry1 is registry2
    
    def test_direct_instantiation_returns_singleton(self):
        """Test that direct instantiation returns singleton."""
        registry1 = SkillRegistry()
        registry2 = SkillRegistry()
        assert registry1 is registry2
    
    def test_reset_instance_creates_new_instance(self):
        """Test that reset_instance creates a new instance."""
        registry1 = SkillRegistry.get_instance()
        SkillRegistry.reset_instance()
        registry2 = SkillRegistry.get_instance()
        assert registry1 is not registry2


class TestSkillRegistration:
    """Tests for skill registration."""
    
    def test_register_skill(self, sample_skill):
        """Test registering a skill."""
        registry = SkillRegistry.get_instance()
        registry.register_skill(sample_skill)
        
        assert registry.has_skill("test-skill")
        assert registry.skill_count() == 1
    
    def test_register_duplicate_raises_error(self, sample_skill):
        """Test that registering duplicate skill raises error."""
        registry = SkillRegistry.get_instance()
        registry.register_skill(sample_skill)
        
        with pytest.raises(SkillRegistryError, match="already registered"):
            registry.register_skill(sample_skill)
    
    def test_unregister_skill(self, sample_skill):
        """Test unregistering a skill."""
        registry = SkillRegistry.get_instance()
        registry.register_skill(sample_skill)
        
        assert registry.unregister_skill("test-skill")
        assert not registry.has_skill("test-skill")
        assert registry.skill_count() == 0
    
    def test_unregister_nonexistent_returns_false(self):
        """Test unregistering nonexistent skill returns False."""
        registry = SkillRegistry.get_instance()
        assert not registry.unregister_skill("nonexistent")


class TestSkillLookup:
    """Tests for skill lookup."""
    
    def test_get_skill(self, sample_skill):
        """Test getting a skill by name."""
        registry = SkillRegistry.get_instance()
        registry.register_skill(sample_skill)
        
        skill = registry.get_skill("test-skill")
        assert skill is sample_skill
    
    def test_get_nonexistent_skill_returns_none(self):
        """Test getting nonexistent skill returns None."""
        registry = SkillRegistry.get_instance()
        assert registry.get_skill("nonexistent") is None
    
    def test_get_skills(self, sample_skill, another_skill):
        """Test getting multiple skills by name."""
        registry = SkillRegistry.get_instance()
        registry.register_skill(sample_skill)
        registry.register_skill(another_skill)
        
        skills = registry.get_skills(["test-skill", "another-skill"])
        assert len(skills) == 2
    
    def test_get_skills_skips_missing(self, sample_skill):
        """Test that get_skills skips missing skills."""
        registry = SkillRegistry.get_instance()
        registry.register_skill(sample_skill)
        
        skills = registry.get_skills(["test-skill", "nonexistent"])
        assert len(skills) == 1
        assert skills[0] is sample_skill
    
    def test_has_skill(self, sample_skill):
        """Test checking if skill exists."""
        registry = SkillRegistry.get_instance()
        registry.register_skill(sample_skill)

        assert registry.has_skill("test-skill")
        assert not registry.has_skill("nonexistent")


class TestSkillListing:
    """Tests for skill listing and filtering."""

    def test_list_skills(self, sample_skill, another_skill):
        """Test listing all skills."""
        registry = SkillRegistry.get_instance()
        registry.register_skill(sample_skill)
        registry.register_skill(another_skill)

        skills = registry.list_skills()
        assert len(skills) == 2

    def test_list_skills_by_tags(self, sample_skill, another_skill):
        """Test listing skills filtered by tags."""
        registry = SkillRegistry.get_instance()
        registry.register_skill(sample_skill)
        registry.register_skill(another_skill)

        # Filter by "python" tag - only another_skill has it
        skills = registry.list_skills(tags=["python"])
        assert len(skills) == 1
        assert skills[0].name == "another-skill"

    def test_list_skills_no_matches(self, sample_skill):
        """Test listing skills with no tag matches."""
        registry = SkillRegistry.get_instance()
        registry.register_skill(sample_skill)

        skills = registry.list_skills(tags=["nonexistent"])
        assert len(skills) == 0

    def test_list_skill_names(self, sample_skill, another_skill):
        """Test listing skill names."""
        registry = SkillRegistry.get_instance()
        registry.register_skill(sample_skill)
        registry.register_skill(another_skill)

        names = registry.list_skill_names()
        assert set(names) == {"test-skill", "another-skill"}

    def test_get_all_skills(self, sample_skill, another_skill):
        """Test getting all skills."""
        registry = SkillRegistry.get_instance()
        registry.register_skill(sample_skill)
        registry.register_skill(another_skill)

        skills = registry.get_all_skills()
        assert len(skills) == 2

    def test_skill_count(self, sample_skill, another_skill):
        """Test getting skill count."""
        registry = SkillRegistry.get_instance()
        assert registry.skill_count() == 0

        registry.register_skill(sample_skill)
        assert registry.skill_count() == 1

        registry.register_skill(another_skill)
        assert registry.skill_count() == 2

    def test_clear(self, sample_skill, another_skill):
        """Test clearing all skills."""
        registry = SkillRegistry.get_instance()
        registry.register_skill(sample_skill)
        registry.register_skill(another_skill)

        registry.clear()
        assert registry.skill_count() == 0

    def test_get_skills_by_tag(self, sample_skill, another_skill):
        """Test getting skills by specific tag."""
        registry = SkillRegistry.get_instance()
        registry.register_skill(sample_skill)
        registry.register_skill(another_skill)

        skills = registry.get_skills_by_tag("test")
        assert len(skills) == 1
        assert skills[0].metadata.name == "test-skill"

    def test_get_skill_metadata(self, sample_skill):
        """Test getting skill metadata only."""
        registry = SkillRegistry.get_instance()
        registry.register_skill(sample_skill)

        metadata = registry.get_skill_metadata("test-skill")
        assert metadata is not None
        assert metadata.name == "test-skill"
        assert metadata.version == "1.0.0"

    def test_find_skills_with_tool(self, sample_skill, another_skill):
        """Test finding skills that recommend a specific tool."""
        registry = SkillRegistry.get_instance()
        registry.register_skill(sample_skill)
        registry.register_skill(another_skill)

        skills = registry.find_skills_with_tool("tool1")
        assert len(skills) == 1
        assert skills[0].metadata.name == "test-skill"


class TestThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_registration(self):
        """Test concurrent skill registration."""
        registry = SkillRegistry.get_instance()

        def create_and_register(i):
            metadata = SkillMetadata(
                name=f"skill-{i}",
                description=f"Skill {i}",
                version="1.0.0"
            )
            skill = SkillDefinition(
                metadata=metadata,
                skill_path=Path(f"/path/to/skill-{i}")
            )
            registry.register_skill(skill)
            return i

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_and_register, i) for i in range(50)]
            for future in as_completed(futures):
                future.result()  # Will raise if any failed

        assert registry.skill_count() == 50

    def test_concurrent_read_write(self, sample_skill):
        """Test concurrent reads and writes."""
        registry = SkillRegistry.get_instance()
        registry.register_skill(sample_skill)

        results = {"reads": 0, "writes": 0}
        lock = threading.Lock()

        def read_skill():
            skill = registry.get_skill("test-skill")
            if skill:
                with lock:
                    results["reads"] += 1

        def list_skills():
            skills = registry.list_skills()
            with lock:
                results["writes"] += 1

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for i in range(100):
                if i % 2 == 0:
                    futures.append(executor.submit(read_skill))
                else:
                    futures.append(executor.submit(list_skills))

            for future in as_completed(futures):
                future.result()

        assert results["reads"] == 50
        assert results["writes"] == 50

