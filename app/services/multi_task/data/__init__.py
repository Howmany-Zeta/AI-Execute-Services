"""
Multi-Task Data Layer

Provides unified data access and storage capabilities for the multi-task service.
"""

from .repositories.task_repository import TaskRepository
from .repositories.result_repository import ResultRepository
from .serializers.data_serializer import DataSerializer, create_serializer
from .storage.storage_manager import StorageManager, create_storage_manager
from .data_layer_service import DataLayerService, create_data_layer_service

__all__ = [
    'TaskRepository',
    'ResultRepository',
    'DataSerializer',
    'create_serializer',
    'StorageManager',
    'create_storage_manager',
    'DataLayerService',
    'create_data_layer_service'
]
