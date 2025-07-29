"""
Data Repository Interface

Defines the contract for data repository implementations in the multi-task architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from ..models.execution_models import ExecutionContext, ExecutionResult, ExecutionModel


class IDataRepository(ABC):
    """
    Abstract interface for data repository implementations.

    This interface defines the core contract that all data repositories must implement,
    providing a standardized way to handle data persistence operations.
    """

    @abstractmethod
    async def save(self, entity: Any, context: Optional[ExecutionContext] = None) -> str:
        """
        Save an entity to the repository.

        Args:
            entity: The entity to save
            context: Optional execution context

        Returns:
            The unique identifier of the saved entity

        Raises:
            DataRepositoryError: If save operation fails
        """
        pass

    @abstractmethod
    async def get_by_id(self, entity_id: str, entity_type: str) -> Optional[Any]:
        """
        Retrieve an entity by its unique identifier.

        Args:
            entity_id: Unique identifier of the entity
            entity_type: Type of the entity

        Returns:
            The entity if found, None otherwise

        Raises:
            DataRepositoryError: If retrieval fails
        """
        pass

    @abstractmethod
    async def update(self, entity_id: str, updates: Dict[str, Any], context: Optional[ExecutionContext] = None) -> bool:
        """
        Update an existing entity.

        Args:
            entity_id: Unique identifier of the entity
            updates: Dictionary of fields to update
            context: Optional execution context

        Returns:
            True if update was successful, False otherwise

        Raises:
            DataRepositoryError: If update operation fails
        """
        pass

    @abstractmethod
    async def delete(self, entity_id: str, entity_type: str) -> bool:
        """
        Delete an entity from the repository.

        Args:
            entity_id: Unique identifier of the entity
            entity_type: Type of the entity

        Returns:
            True if deletion was successful, False otherwise

        Raises:
            DataRepositoryError: If deletion fails
        """
        pass

    @abstractmethod
    async def find(self, criteria: Dict[str, Any], entity_type: str, limit: Optional[int] = None) -> List[Any]:
        """
        Find entities matching the given criteria.

        Args:
            criteria: Search criteria
            entity_type: Type of entities to search
            limit: Maximum number of results

        Returns:
            List of matching entities

        Raises:
            DataRepositoryError: If search operation fails
        """
        pass

    @abstractmethod
    async def count(self, criteria: Dict[str, Any], entity_type: str) -> int:
        """
        Count entities matching the given criteria.

        Args:
            criteria: Search criteria
            entity_type: Type of entities to count

        Returns:
            Number of matching entities

        Raises:
            DataRepositoryError: If count operation fails
        """
        pass


class ITaskRepository(IDataRepository):
    """
    Interface for task-specific repository operations.
    """

    @abstractmethod
    async def save_task_execution(self, execution: ExecutionModel) -> str:
        """
        Save a task execution record.

        Args:
            execution: The execution model to save

        Returns:
            The execution ID

        Raises:
            DataRepositoryError: If save operation fails
        """
        pass

    @abstractmethod
    async def get_task_history(self, task_id: str, user_id: Optional[str] = None) -> List[ExecutionResult]:
        """
        Get the execution history for a task.

        Args:
            task_id: The task identifier
            user_id: Optional user identifier for filtering

        Returns:
            List of execution results

        Raises:
            DataRepositoryError: If retrieval fails
        """
        pass

    @abstractmethod
    async def get_active_executions(self, user_id: Optional[str] = None) -> List[ExecutionModel]:
        """
        Get currently active executions.

        Args:
            user_id: Optional user identifier for filtering

        Returns:
            List of active execution models

        Raises:
            DataRepositoryError: If retrieval fails
        """
        pass

    @abstractmethod
    async def update_execution_status(self, execution_id: str, status: str, result: Optional[ExecutionResult] = None) -> bool:
        """
        Update the status of an execution.

        Args:
            execution_id: The execution identifier
            status: New status
            result: Optional execution result

        Returns:
            True if update was successful

        Raises:
            DataRepositoryError: If update fails
        """
        pass


class IResultRepository(IDataRepository):
    """
    Interface for result-specific repository operations.
    """

    @abstractmethod
    async def save_execution_result(self, result: ExecutionResult, context: ExecutionContext) -> str:
        """
        Save an execution result.

        Args:
            result: The execution result to save
            context: The execution context

        Returns:
            The result ID

        Raises:
            DataRepositoryError: If save operation fails
        """
        pass

    @abstractmethod
    async def get_results_by_execution(self, execution_id: str) -> List[ExecutionResult]:
        """
        Get all results for a specific execution.

        Args:
            execution_id: The execution identifier

        Returns:
            List of execution results

        Raises:
            DataRepositoryError: If retrieval fails
        """
        pass

    @abstractmethod
    async def get_results_by_quality_score(self, min_score: float, max_score: float = 1.0) -> List[ExecutionResult]:
        """
        Get results within a quality score range.

        Args:
            min_score: Minimum quality score
            max_score: Maximum quality score

        Returns:
            List of execution results

        Raises:
            DataRepositoryError: If retrieval fails
        """
        pass

    @abstractmethod
    async def aggregate_results(self, criteria: Dict[str, Any], aggregation_type: str) -> Dict[str, Any]:
        """
        Aggregate results based on criteria.

        Args:
            criteria: Aggregation criteria
            aggregation_type: Type of aggregation (sum, avg, count, etc.)

        Returns:
            Aggregation results

        Raises:
            DataRepositoryError: If aggregation fails
        """
        pass


class IStorageProvider(ABC):
    """
    Abstract interface for storage provider implementations.
    """

    @abstractmethod
    async def store(self, key: str, data: Union[str, bytes, Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store data with the given key.

        Args:
            key: Storage key
            data: Data to store
            metadata: Optional metadata

        Returns:
            True if storage was successful

        Raises:
            StorageError: If storage operation fails
        """
        pass

    @abstractmethod
    async def retrieve(self, key: str) -> Optional[Union[str, bytes, Dict[str, Any]]]:
        """
        Retrieve data by key.

        Args:
            key: Storage key

        Returns:
            The stored data if found, None otherwise

        Raises:
            StorageError: If retrieval fails
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete data by key.

        Args:
            key: Storage key

        Returns:
            True if deletion was successful

        Raises:
            StorageError: If deletion fails
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if data exists for the given key.

        Args:
            key: Storage key

        Returns:
            True if data exists

        Raises:
            StorageError: If check operation fails
        """
        pass

    @abstractmethod
    async def list_keys(self, prefix: Optional[str] = None, limit: Optional[int] = None) -> List[str]:
        """
        List storage keys with optional prefix filtering.

        Args:
            prefix: Optional key prefix filter
            limit: Maximum number of keys to return

        Returns:
            List of storage keys

        Raises:
            StorageError: If listing fails
        """
        pass
