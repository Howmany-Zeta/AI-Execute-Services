"""
Knowledge Database

Manages the analytical frameworks database for the Meta-Architect system.
Handles synchronization with framework.yaml, database operations, and
provides query interfaces for framework selection.
"""

import os
import yaml
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy import create_engine, MetaData, and_, or_, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from pathlib import Path

from ...core.models.architect_models import (
    Base, AnalyticalFramework, MetaFramework, StrategicPlanExecution,
    ComplexityLevel, FrameworkStrategy, ProblemType
)
from ...config.schemas.framework_schema import FrameworkConfigModel
from ...config.validators.framework_validator import FrameworkValidator, FrameworkValidationError

logger = logging.getLogger(__name__)


class KnowledgeDatabaseError(Exception):
    """Custom exception for knowledge database operations."""
    pass


class KnowledgeDatabase:
    """
    Knowledge database manager for analytical frameworks.

    Responsibilities:
    1. Create and manage database schema
    2. Synchronize framework.yaml with database
    3. Provide query interfaces for framework selection
    4. Track framework usage and performance
    5. Maintain data consistency and integrity
    """

    def __init__(self, database_url: str = None, framework_config_path: str = None):
        """
        Initialize the knowledge database.

        Args:
            database_url: Database connection URL (defaults to SQLite in-memory)
            framework_config_path: Path to framework.yaml file
        """
        # Database configuration
        self.database_url = database_url or "sqlite:///knowledge_database.db"
        self.engine = None
        self.SessionLocal = None

        # Framework configuration
        self.framework_config_path = framework_config_path or self._get_default_config_path()
        self.validator = FrameworkValidator()

        # Cache for frequently accessed data
        self._framework_cache: Dict[str, AnalyticalFramework] = {}
        self._meta_framework_cache: Dict[str, MetaFramework] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minutes

        logger.info(f"KnowledgeDatabase initialized with URL: {self.database_url}")

    def initialize(self) -> None:
        """
        Initialize the database and perform initial synchronization.

        Raises:
            KnowledgeDatabaseError: If initialization fails
        """
        try:
            logger.info("Initializing knowledge database...")

            # Create database engine and session factory
            self._create_engine()
            self._create_tables()

            # Perform initial synchronization
            self.sync_with_config()

            logger.info("Knowledge database initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize knowledge database: {e}")
            raise KnowledgeDatabaseError(f"Database initialization failed: {e}")

    def sync_with_config(self) -> Dict[str, Any]:
        """
        Synchronize database with framework.yaml configuration.

        Returns:
            Dictionary with synchronization results

        Raises:
            KnowledgeDatabaseError: If synchronization fails
        """
        try:
            logger.info(f"Synchronizing database with config file: {self.framework_config_path}")

            # Validate configuration file
            is_valid, config_model, errors, warnings = self._validate_config()
            validation_summary = {"errors": errors, "warnings": warnings}
            if not is_valid:
                raise KnowledgeDatabaseError(f"Configuration validation failed: {validation_summary}")

            # Perform synchronization
            sync_results = self._perform_sync(config_model)

            # Clear cache after sync
            self._clear_cache()

            logger.info(f"Synchronization completed: {sync_results}")
            return sync_results

        except Exception as e:
            logger.error(f"Configuration synchronization failed: {e}")
            raise KnowledgeDatabaseError(f"Sync failed: {e}")

    def get_frameworks_by_problem_type(self, problem_type: str) -> List[AnalyticalFramework]:
        """
        Get frameworks that can solve a specific problem type.

        Args:
            problem_type: Type of problem to solve

        Returns:
            List of matching frameworks
        """
        try:
            with self._get_session() as session:
                frameworks = session.query(AnalyticalFramework).filter(
                    and_(
                        AnalyticalFramework.solves_problem_type == problem_type,
                        AnalyticalFramework.is_active == True
                    )
                ).all()

                logger.debug(f"Found {len(frameworks)} frameworks for problem type: {problem_type}")
                return frameworks

        except Exception as e:
            logger.error(f"Failed to query frameworks by problem type: {e}")
            raise KnowledgeDatabaseError(f"Query failed: {e}")

    def get_frameworks_by_tags(self, tags: List[str]) -> List[AnalyticalFramework]:
        """
        Get frameworks that match any of the specified tags.

        Args:
            tags: List of tags to search for

        Returns:
            List of matching frameworks
        """
        try:
            with self._get_session() as session:
                # Build OR conditions for tag matching
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append(AnalyticalFramework.tags.contains(tag))

                frameworks = session.query(AnalyticalFramework).filter(
                    and_(
                        or_(*tag_conditions),
                        AnalyticalFramework.is_active == True
                    )
                ).all()

                logger.debug(f"Found {len(frameworks)} frameworks for tags: {tags}")
                return frameworks

        except Exception as e:
            logger.error(f"Failed to query frameworks by tags: {e}")
            raise KnowledgeDatabaseError(f"Query failed: {e}")

    def get_frameworks_by_complexity(self, complexity: ComplexityLevel) -> List[AnalyticalFramework]:
        """
        Get frameworks by complexity level.

        Args:
            complexity: Complexity level to filter by

        Returns:
            List of matching frameworks
        """
        try:
            with self._get_session() as session:
                frameworks = session.query(AnalyticalFramework).filter(
                    and_(
                        AnalyticalFramework.complexity_level == complexity.value,
                        AnalyticalFramework.is_active == True
                    )
                ).all()

                logger.debug(f"Found {len(frameworks)} frameworks for complexity: {complexity}")
                return frameworks

        except Exception as e:
            logger.error(f"Failed to query frameworks by complexity: {e}")
            raise KnowledgeDatabaseError(f"Query failed: {e}")

    def get_framework_by_name(self, name: str) -> Optional[AnalyticalFramework]:
        """
        Get a specific framework by name.

        Args:
            name: Name of the framework

        Returns:
            Framework if found, None otherwise
        """
        try:
            # Check cache first
            if self._is_cache_valid() and name in self._framework_cache:
                return self._framework_cache[name]

            with self._get_session() as session:
                framework = session.query(AnalyticalFramework).filter(
                    and_(
                        AnalyticalFramework.name == name,
                        AnalyticalFramework.is_active == True
                    )
                ).first()

                # Update cache
                if framework:
                    self._framework_cache[name] = framework

                return framework

        except Exception as e:
            logger.error(f"Failed to get framework by name: {e}")
            raise KnowledgeDatabaseError(f"Query failed: {e}")

    def get_meta_framework_by_name(self, name: str) -> Optional[MetaFramework]:
        """
        Get a specific meta-framework by name.

        Args:
            name: Name of the meta-framework

        Returns:
            Meta-framework if found, None otherwise
        """
        try:
            # Check cache first
            if self._is_cache_valid() and name in self._meta_framework_cache:
                return self._meta_framework_cache[name]

            with self._get_session() as session:
                meta_framework = session.query(MetaFramework).filter(
                    and_(
                        MetaFramework.name == name,
                        MetaFramework.is_active == True
                    )
                ).first()

                # Update cache
                if meta_framework:
                    self._meta_framework_cache[name] = meta_framework

                return meta_framework

        except Exception as e:
            logger.error(f"Failed to get meta-framework by name: {e}")
            raise KnowledgeDatabaseError(f"Query failed: {e}")

    def get_meta_frameworks_by_problem_type(self, problem_type: str) -> List[MetaFramework]:
        """
        Get meta-frameworks that can solve a specific problem type.

        Args:
            problem_type: Type of problem to solve

        Returns:
            List of matching meta-frameworks
        """
        try:
            with self._get_session() as session:
                meta_frameworks = session.query(MetaFramework).filter(
                    and_(
                        MetaFramework.solves_problem_type == problem_type,
                        MetaFramework.is_active == True
                    )
                ).all()

                logger.debug(f"Found {len(meta_frameworks)} meta-frameworks for problem type: {problem_type}")
                return meta_frameworks

        except Exception as e:
            logger.error(f"Failed to query meta-frameworks by problem type: {e}")
            raise KnowledgeDatabaseError(f"Query failed: {e}")

    def search_frameworks(self, query: str, limit: int = 10) -> List[AnalyticalFramework]:
        """
        Search frameworks by name, description, or tags.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of matching frameworks
        """
        try:
            with self._get_session() as session:
                search_pattern = f"%{query}%"

                frameworks = session.query(AnalyticalFramework).filter(
                    and_(
                        or_(
                            AnalyticalFramework.name.ilike(search_pattern),
                            AnalyticalFramework.description.ilike(search_pattern),
                            AnalyticalFramework.tags.ilike(search_pattern)
                        ),
                        AnalyticalFramework.is_active == True
                    )
                ).limit(limit).all()

                logger.debug(f"Found {len(frameworks)} frameworks for search query: {query}")
                return frameworks

        except Exception as e:
            logger.error(f"Failed to search frameworks: {e}")
            raise KnowledgeDatabaseError(f"Search failed: {e}")

    def record_strategic_plan_execution(self, execution_data: Dict[str, Any]) -> str:
        """
        Record a strategic plan execution for analytics and learning.

        Args:
            execution_data: Execution data dictionary

        Returns:
            Execution ID
        """
        try:
            with self._get_session() as session:
                execution = StrategicPlanExecution(
                    execution_id=execution_data.get('execution_id'),
                    problem_type=execution_data.get('problem_type'),
                    selected_frameworks=execution_data.get('selected_frameworks', []),
                    strategic_plan=execution_data.get('strategic_plan', {}),
                    confidence_score=execution_data.get('confidence_score', 0.0),
                    reasoning=execution_data.get('reasoning', ''),
                    total_estimated_duration=execution_data.get('total_estimated_duration', ''),
                    overall_complexity=execution_data.get('overall_complexity', ''),
                    processing_time_ms=execution_data.get('processing_time_ms', 0.0),
                    architect_version=execution_data.get('architect_version', '1.0.0'),
                    user_id=execution_data.get('user_id'),
                    task_id=execution_data.get('task_id'),
                    session_id=execution_data.get('session_id')
                )

                session.add(execution)
                session.commit()

                logger.info(f"Recorded strategic plan execution: {execution.execution_id}")
                return execution.execution_id

        except Exception as e:
            logger.error(f"Failed to record strategic plan execution: {e}")
            raise KnowledgeDatabaseError(f"Recording failed: {e}")

    def get_framework_usage_stats(self) -> Dict[str, Any]:
        """
        Get framework usage statistics.

        Returns:
            Dictionary with usage statistics
        """
        try:
            with self._get_session() as session:
                # Get total executions
                total_executions = session.query(StrategicPlanExecution).count()

                # Get framework usage counts
                framework_usage = {}
                executions = session.query(StrategicPlanExecution).all()

                for execution in executions:
                    for framework_name in execution.selected_frameworks:
                        framework_usage[framework_name] = framework_usage.get(framework_name, 0) + 1

                # Get problem type distribution
                problem_type_stats = session.query(
                    StrategicPlanExecution.problem_type,
                    func.count(StrategicPlanExecution.id)
                ).group_by(StrategicPlanExecution.problem_type).all()

                problem_type_distribution = {pt: count for pt, count in problem_type_stats}

                # Get average confidence score
                avg_confidence = session.query(
                    func.avg(StrategicPlanExecution.confidence_score)
                ).scalar() or 0.0

                return {
                    'total_executions': total_executions,
                    'framework_usage': framework_usage,
                    'problem_type_distribution': problem_type_distribution,
                    'average_confidence_score': float(avg_confidence),
                    'last_updated': datetime.utcnow().isoformat()
                }

        except Exception as e:
            logger.error(f"Failed to get framework usage stats: {e}")
            raise KnowledgeDatabaseError(f"Stats query failed: {e}")

    # Private helper methods

    def _create_engine(self) -> None:
        """Create database engine and session factory."""
        try:
            self.engine = create_engine(
                self.database_url,
                echo=False,  # Set to True for SQL debugging
                pool_pre_ping=True
            )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        except Exception as e:
            raise KnowledgeDatabaseError(f"Failed to create database engine: {e}")

    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")

        except Exception as e:
            raise KnowledgeDatabaseError(f"Failed to create database tables: {e}")

    def _get_session(self) -> Session:
        """Get a database session."""
        if not self.SessionLocal:
            raise KnowledgeDatabaseError("Database not initialized")
        return self.SessionLocal()

    def _get_default_config_path(self) -> str:
        """Get the default path to framework.yaml."""
        # Navigate from current file to the config directory
        # Current file: app/services/multi_task/data/storage/knowledge_database.py
        # Target path: config/multi_task/framework.yaml
        current_dir = Path(__file__).parent.parent.parent.parent.parent.parent  # Go to project root
        return str(current_dir / "config" / "multi_task" / "framework.yaml")

    def _validate_config(self) -> Tuple[bool, Optional[FrameworkConfigModel], List[str], List[str]]:
        """Validate the framework configuration file."""
        try:
            return self.validator.validate_file(self.framework_config_path)
        except FrameworkValidationError as e:
            logger.error(f"Framework configuration validation failed: {e}")
            return False, None, [str(e)], []

    def _perform_sync(self, config_model: FrameworkConfigModel) -> Dict[str, Any]:
        """Perform the actual synchronization with the database."""
        sync_results = {
            'frameworks_added': 0,
            'frameworks_updated': 0,
            'frameworks_removed': 0,
            'meta_frameworks_added': 0,
            'meta_frameworks_updated': 0,
            'meta_frameworks_removed': 0,
            'errors': []
        }

        try:
            with self._get_session() as session:
                # Sync frameworks
                self._sync_frameworks(session, config_model.frameworks, sync_results)

                # Sync meta-frameworks
                self._sync_meta_frameworks(session, config_model.meta_frameworks, sync_results)

                session.commit()

        except Exception as e:
            logger.error(f"Sync operation failed: {e}")
            sync_results['errors'].append(str(e))

        return sync_results

    def _sync_frameworks(self, session: Session, frameworks: List, sync_results: Dict[str, Any]) -> None:
        """Sync frameworks with the database."""
        # Get existing frameworks
        existing_frameworks = {f.name: f for f in session.query(AnalyticalFramework).all()}
        config_framework_names = {f.name for f in frameworks}

        # Add or update frameworks from config
        for framework_config in frameworks:
            clean_name = framework_config.name.lower().replace(' ', '_').replace("'", '')
            framework_id = f"fw_{clean_name}"

            if framework_config.name in existing_frameworks:
                # Update existing framework
                framework = existing_frameworks[framework_config.name]
                self._update_framework_from_config(framework, framework_config)
                sync_results['frameworks_updated'] += 1
            else:
                # Add new framework
                framework = AnalyticalFramework(
                    framework_id=framework_id,
                    name=framework_config.name,
                    description=framework_config.description,
                    tags=framework_config.tags,
                    components=framework_config.components,
                    solves_problem_type=framework_config.solves_problem_type,
                    complexity_level=framework_config.complexity_level.value,
                    estimated_duration=framework_config.estimated_duration,
                    required_data_types=framework_config.required_data_types,
                    output_format=framework_config.output_format.value
                )
                session.add(framework)
                sync_results['frameworks_added'] += 1

        # Mark removed frameworks as inactive
        for name, framework in existing_frameworks.items():
            if name not in config_framework_names and framework.is_active:
                framework.is_active = False
                framework.updated_at = datetime.utcnow()
                sync_results['frameworks_removed'] += 1

    def _sync_meta_frameworks(self, session: Session, meta_frameworks: List, sync_results: Dict[str, Any]) -> None:
        """Sync meta-frameworks with the database."""
        # Get existing meta-frameworks
        existing_meta_frameworks = {mf.name: mf for mf in session.query(MetaFramework).all()}
        config_meta_framework_names = {mf.name for mf in meta_frameworks}

        # Add or update meta-frameworks from config
        for meta_framework_config in meta_frameworks:
            meta_framework_id = f"mf_{meta_framework_config.name.lower().replace(' ', '_')}"

            if meta_framework_config.name in existing_meta_frameworks:
                # Update existing meta-framework
                meta_framework = existing_meta_frameworks[meta_framework_config.name]
                self._update_meta_framework_from_config(meta_framework, meta_framework_config)
                sync_results['meta_frameworks_updated'] += 1
            else:
                # Add new meta-framework
                meta_framework = MetaFramework(
                    meta_framework_id=meta_framework_id,
                    name=meta_framework_config.name,
                    description=meta_framework_config.description,
                    component_frameworks=meta_framework_config.component_frameworks,
                    solves_problem_type=meta_framework_config.solves_problem_type,
                    complexity_level=meta_framework_config.complexity_level.value,
                    estimated_duration=meta_framework_config.estimated_duration,
                    strategy=meta_framework_config.strategy.value
                )
                session.add(meta_framework)
                sync_results['meta_frameworks_added'] += 1

        # Mark removed meta-frameworks as inactive
        for name, meta_framework in existing_meta_frameworks.items():
            if name not in config_meta_framework_names and meta_framework.is_active:
                meta_framework.is_active = False
                meta_framework.updated_at = datetime.utcnow()
                sync_results['meta_frameworks_removed'] += 1

    def _update_framework_from_config(self, framework: AnalyticalFramework, config) -> None:
        """Update framework from configuration."""
        framework.description = config.description
        framework.tags = config.tags
        framework.components = config.components
        framework.solves_problem_type = config.solves_problem_type
        framework.complexity_level = config.complexity_level.value
        framework.estimated_duration = config.estimated_duration
        framework.required_data_types = config.required_data_types
        framework.output_format = config.output_format.value
        framework.updated_at = datetime.utcnow()
        framework.is_active = True

    def _update_meta_framework_from_config(self, meta_framework: MetaFramework, config) -> None:
        """Update meta-framework from configuration."""
        meta_framework.description = config.description
        meta_framework.component_frameworks = config.component_frameworks
        meta_framework.solves_problem_type = config.solves_problem_type
        meta_framework.complexity_level = config.complexity_level.value
        meta_framework.estimated_duration = config.estimated_duration
        meta_framework.strategy = config.strategy.value
        meta_framework.updated_at = datetime.utcnow()
        meta_framework.is_active = True

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache_timestamp:
            return False

        elapsed = (datetime.utcnow() - self._cache_timestamp).total_seconds()
        return elapsed < self._cache_ttl_seconds

    def _clear_cache(self) -> None:
        """Clear the framework cache."""
        self._framework_cache.clear()
        self._meta_framework_cache.clear()
        self._cache_timestamp = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.engine:
            self.engine.dispose()
