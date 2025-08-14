"""
Configuration Schema

Main schema that combines all configuration schemas and provides
unified validation for the entire multi-task service configuration.
"""

from pydantic import field_validator, model_validator, ConfigDict, BaseModel, Field, field_serializer
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from .prompt_schema import PromptSchema, PromptValidationSchema
from .task_schema import TaskSchema, TaskValidationSchema
from .domain_schema import DomainListSchema, DomainValidationSchema


class ConfigMetadataSchema(BaseModel):
    """Schema for configuration metadata."""

    version: str = Field(..., description="Configuration version")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    author: Optional[str] = Field(None, description="Configuration author")
    description: Optional[str] = Field(None, description="Configuration description")
    environment: str = Field(default="development", description="Target environment")

    @field_validator('version')
    @classmethod
    def validate_version(cls, v):
        """Validate version format."""
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', v):
            raise ValueError("Version must be in format X.Y.Z")
        return v

    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v):
        """Validate environment."""
        valid_environments = {'development', 'testing', 'staging', 'production'}
        if v not in valid_environments:
            raise ValueError(f"Invalid environment: {v}. Valid: {valid_environments}")
        return v

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO format."""
        if dt is None:
            return None
        return dt.isoformat()

    model_config = ConfigDict(extra="forbid")


class ConfigValidationResultSchema(BaseModel):
    """Schema for overall configuration validation results."""

    is_valid: bool = Field(..., description="Whether all configurations are valid")
    validation_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Validation timestamp")

    # Individual validation results
    prompts_validation: Optional[PromptValidationSchema] = Field(None, description="Prompts validation result")
    tasks_validation: Optional[TaskValidationSchema] = Field(None, description="Tasks validation result")
    domains_validation: Optional[DomainValidationSchema] = Field(None, description="Domains validation result")

    # Cross-validation results
    cross_validation_errors: Dict[str, List[str]] = Field(default_factory=dict, description="Cross-validation errors")
    cross_validation_warnings: List[str] = Field(default_factory=list, description="Cross-validation warnings")

    # Summary statistics
    total_errors: int = Field(default=0, description="Total number of errors")
    total_warnings: int = Field(default=0, description="Total number of warnings")
    error_categories: Dict[str, int] = Field(default_factory=dict, description="Error count by category")
    warning_categories: Dict[str, int] = Field(default_factory=dict, description="Warning count by category")

    @model_validator(mode='after')
    def validate_overall_status(self) -> 'ConfigValidationResultSchema':
        """Validate overall status based on individual validations."""
        # Check if any individual validation failed
        validations = [
            self.prompts_validation,
            self.tasks_validation,
            self.domains_validation
        ]

        for validation in validations:
            if validation and hasattr(validation, 'is_valid') and not validation.is_valid:
                if self.is_valid:  # If marked as valid but has invalid components
                    raise ValueError("Overall validation cannot be valid when individual validations fail")

        # Check cross-validation errors
        if self.cross_validation_errors and self.is_valid:
            raise ValueError("Overall validation cannot be valid when cross-validation errors exist")

        return self

    @field_serializer('validation_timestamp')
    def serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime to ISO format."""
        return dt.isoformat()

    model_config = ConfigDict(extra="allow")


class ConfigInfoSchema(BaseModel):
    """Schema for configuration information."""

    config_dir: str = Field(..., description="Configuration directory path")
    loaded_files: List[str] = Field(..., description="List of loaded configuration files")
    file_timestamps: Dict[str, str] = Field(..., description="File modification timestamps")
    watching_changes: bool = Field(..., description="Whether file watching is active")

    # Statistics
    total_domains: int = Field(..., description="Total number of domains")
    total_roles: int = Field(..., description="Total number of roles")
    total_tasks: int = Field(..., description="Total number of tasks")

    # Health status
    health_status: str = Field(default="unknown", description="Overall health status")
    last_validation: Optional[datetime] = Field(None, description="Last validation timestamp")

    @field_validator('health_status')
    @classmethod
    def validate_health_status(cls, v):
        """Validate health status."""
        valid_statuses = {'healthy', 'warning', 'error', 'unknown'}
        if v not in valid_statuses:
            raise ValueError(f"Invalid health status: {v}. Valid: {valid_statuses}")
        return v

    @field_serializer('last_validation')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO format."""
        if dt is None:
            return None
        return dt.isoformat()

    model_config = ConfigDict(extra="allow")


class ConfigUpdateSchema(BaseModel):
    """Schema for configuration updates."""

    config_type: str = Field(..., description="Type of configuration to update")
    update_data: Dict[str, Any] = Field(..., description="Update data")
    update_reason: Optional[str] = Field(None, description="Reason for the update")
    updated_by: Optional[str] = Field(None, description="User who made the update")
    backup_created: bool = Field(default=False, description="Whether a backup was created")

    @field_validator('config_type')
    @classmethod
    def validate_config_type(cls, v):
        """Validate configuration type."""
        valid_types = {'prompts', 'tasks', 'domains', 'metadata'}
        if v not in valid_types:
            raise ValueError(f"Invalid config type: {v}. Valid: {valid_types}")
        return v
    model_config = ConfigDict(extra="forbid")


class ConfigBackupSchema(BaseModel):
    """Schema for configuration backups."""

    backup_id: str = Field(..., description="Unique backup identifier")
    backup_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Backup creation time")
    config_files: List[str] = Field(..., description="List of backed up configuration files")
    backup_reason: str = Field(..., description="Reason for creating the backup")
    backup_size: Optional[int] = Field(None, description="Backup size in bytes")

    @field_serializer('backup_timestamp')
    def serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime to ISO format."""
        return dt.isoformat()

    model_config = ConfigDict(extra="forbid")


class ConfigSchema(BaseModel):
    """
    Main configuration schema that combines all configuration types.

    This schema represents the complete configuration for the multi-task service,
    including prompts, tasks, domains, and metadata.
    """

    metadata: ConfigMetadataSchema = Field(..., description="Configuration metadata")
    prompts: Optional[PromptSchema] = Field(None, description="Prompts configuration")
    tasks: Optional[TaskSchema] = Field(None, description="Tasks configuration")
    domains: Optional[DomainListSchema] = Field(None, description="Domains configuration")

    # Validation and status
    validation_result: Optional[ConfigValidationResultSchema] = Field(None, description="Last validation result")
    config_info: Optional[ConfigInfoSchema] = Field(None, description="Configuration information")
    last_validated_at: Optional[datetime] = Field(None, description="Last validation timestamp")

    @field_validator('prompts')
    @classmethod
    def validate_prompts_config(cls, v):
        """Validate prompts configuration."""
        if v is None:
            return v

        # Additional validation logic can be added here
        return v

    @field_validator('tasks')
    @classmethod
    def validate_tasks_config(cls, v):
        """Validate tasks configuration."""
        if v is None:
            return v

        # Additional validation logic can be added here
        return v

    @field_validator('domains')
    @classmethod
    def validate_domains_config(cls, v):
        """Validate domains configuration."""
        if v is None:
            return v

        # Additional validation logic can be added here
        return v

    def is_complete(self) -> bool:
        """Check if all required configurations are present."""
        return all([
            self.prompts is not None,
            self.tasks is not None,
            self.domains is not None
        ])

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the configuration."""
        summary = {
            'version': self.metadata.version,
            'environment': self.metadata.environment,
            'complete': self.is_complete(),
            'components': {
                'prompts': self.prompts is not None,
                'tasks': self.tasks is not None,
                'domains': self.domains is not None
            }
        }

        if self.validation_result:
            summary['validation'] = {
                'is_valid': self.validation_result.is_valid,
                'total_errors': self.validation_result.total_errors,
                'total_warnings': self.validation_result.total_warnings,
                'last_validated': self.validation_result.validation_timestamp.isoformat()
            }

        if self.config_info:
            summary['info'] = {
                'total_domains': self.config_info.total_domains,
                'total_roles': self.config_info.total_roles,
                'total_tasks': self.config_info.total_tasks,
                'health_status': self.config_info.health_status
            }

        return summary

    model_config = ConfigDict(extra="allow", validate_assignment=True,)

    @field_serializer('last_validated_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO format."""
        if dt is None:
            return None
        return dt.isoformat()


class ConfigManagerStateSchema(BaseModel):
    """Schema for configuration manager state."""

    initialized: bool = Field(default=False, description="Whether the manager is initialized")
    config_dir: str = Field(..., description="Configuration directory")
    watching_files: bool = Field(default=False, description="Whether file watching is active")
    loaded_configs: List[str] = Field(default_factory=list, description="List of loaded configurations")
    last_reload: Optional[datetime] = Field(None, description="Last configuration reload time")
    error_count: int = Field(default=0, description="Number of configuration errors")
    warning_count: int = Field(default=0, description="Number of configuration warnings")
    last_validated_at: datetime = Field(default_factory=datetime.utcnow, description="Last validation timestamp")

    model_config = ConfigDict(extra="allow")

    @field_serializer('last_reload', 'last_validated_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime objects to ISO format strings."""
        if dt is None:
            return None
        return dt.isoformat()
