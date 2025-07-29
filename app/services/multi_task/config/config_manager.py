"""
Configuration Manager

Central configuration management for the multi-task service, providing
unified access to configuration data with validation and dynamic updates.
"""

import os
import yaml
import json
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime
import logging
# Removed watchdog dependency - configuration files are static during service runtime

from ..core.exceptions.task_exceptions import TaskValidationError
from .validators import ConfigValidator
from .schemas import ConfigSchema

logger = logging.getLogger(__name__)


# Removed ConfigFileHandler - configuration files are static during service runtime


class ConfigManager:
    """
    Central configuration manager for the multi-task service.

    Provides unified access to configuration data with validation,
    caching, and dynamic updates.
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the configuration manager.

        Args:
            config_dir: Directory containing configuration files.
                       If None, uses the default multi_task directory.
        """
        if config_dir is None:
            # Default to the /opt/startu/python-middleware/config/multi_task directory
            self.config_dir = Path("/opt/startu/python-middleware/config/multi_task")
        else:
            self.config_dir = Path(config_dir)

        self.config_cache: Dict[str, Any] = {}
        self.config_timestamps: Dict[str, datetime] = {}
        self.validator = ConfigValidator()
        # Create ConfigSchema with default metadata
        from .schemas.config_schema import ConfigMetadataSchema
        default_metadata = ConfigMetadataSchema(
            version="1.0.0",
            environment="development",
            description="Default configuration for multi-task service"
        )
        self.schema = ConfigSchema(metadata=default_metadata)

        # Configuration files are static during service runtime - no file watching needed

        # Load initial configurations
        self._load_all_configs()

    def _load_all_configs(self) -> None:
        """Load all configuration files from the config directory."""
        try:
            # Load core configuration files
            self._load_config_file('prompts.yaml')
            self._load_config_file('tasks.yaml')

            # Load new configuration files
            self._load_config_file('llm_binding.yaml')
            self._load_config_file('agent_list.yaml')

            # Load domain configuration
            self._load_domain_config()

            logger.info("All configuration files loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load configurations: {e}")
            raise TaskValidationError(
                message=f"Configuration loading failed: {e}",
                validation_errors={"config_loading": str(e)}
            )

    def _load_config_file(self, filename: str) -> Dict[str, Any]:
        """
        Load a specific configuration file.

        Args:
            filename: Name of the configuration file to load

        Returns:
            Loaded configuration data

        Raises:
            TaskValidationError: If file loading or validation fails
        """
        file_path = self.config_dir / filename

        if not file_path.exists():
            raise TaskValidationError(
                message=f"Configuration file not found: {filename}",
                validation_errors={"file_not_found": str(file_path)}
            )

        try:
            # Load file content
            with open(file_path, 'r', encoding='utf-8') as file:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    config_data = yaml.safe_load(file)
                elif file_path.suffix.lower() == '.json':
                    config_data = json.load(file)
                else:
                    raise ValueError(f"Unsupported file format: {file_path.suffix}")

            # Validate configuration
            validation_result = self.validator.validate_config(filename, config_data)
            if not validation_result.is_valid:
                raise TaskValidationError(
                    message=f"Configuration validation failed for {filename}",
                    validation_errors=validation_result.errors
                )

            # Cache the configuration
            self.config_cache[filename] = config_data
            self.config_timestamps[filename] = datetime.fromtimestamp(file_path.stat().st_mtime)

            logger.info(f"Configuration file loaded: {filename}")
            return config_data

        except Exception as e:
            if isinstance(e, TaskValidationError):
                raise
            raise TaskValidationError(
                message=f"Failed to load configuration file {filename}: {e}",
                validation_errors={"file_loading": str(e)}
            )

    def _load_domain_config(self) -> None:
        """Load domain configuration from domain_list.yaml."""
        try:
            # Load DOMAINS from domain_list.yaml
            domain_file_path = self.config_dir / "domain_list.yaml"

            if not domain_file_path.exists():
                raise TaskValidationError(
                    message="Domain configuration file not found: domain_list.yaml",
                    validation_errors={"file_not_found": str(domain_file_path)}
                )

            with open(domain_file_path, 'r', encoding='utf-8') as file:
                domain_data = yaml.safe_load(file)

            # Extract DOMAINS list from the loaded data
            DOMAINS = domain_data.get('DOMAINS', [])

            if not DOMAINS:
                raise TaskValidationError(
                    message="No domains found in domain_list.yaml",
                    validation_errors={"empty_domains": "DOMAINS list is empty or missing"}
                )

            # Validate domains
            validation_result = self.validator.validate_domains(DOMAINS)
            if not validation_result.is_valid:
                raise TaskValidationError(
                    message="Domain list validation failed",
                    validation_errors=validation_result.errors
                )

            # Cache domain configuration
            domain_config = {
                'domains': DOMAINS,
                'domain_count': len(DOMAINS),
                'last_updated': datetime.utcnow().isoformat()
            }

            self.config_cache['domains.json'] = domain_config
            self.config_timestamps['domains.json'] = datetime.utcnow()

            logger.info(f"Domain configuration loaded: {len(DOMAINS)} domains")

        except Exception as e:
            if isinstance(e, TaskValidationError):
                raise
            raise TaskValidationError(
                message=f"Failed to load domain configuration: {e}",
                validation_errors={"domain_loading": str(e)}
            )

# Removed _reload_config_file - configuration files are static during service runtime

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.

        Args:
            key: Configuration key in format 'file.section.key' or 'file.key'
            default: Default value if key is not found

        Returns:
            Configuration value or default
        """
        try:
            parts = key.split('.')

            if len(parts) < 2:
                raise ValueError(f"Invalid configuration key format: {key}")

            filename = f"{parts[0]}.yaml"
            if filename not in self.config_cache:
                # Try with .json extension
                filename = f"{parts[0]}.json"
                if filename not in self.config_cache:
                    logger.warning(f"Configuration file not found for key: {key}")
                    return default

            config_data = self.config_cache[filename]

            # Navigate through the nested structure
            current = config_data
            for part in parts[1:]:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    logger.warning(f"Configuration key not found: {key}")
                    return default

            return current

        except Exception as e:
            logger.error(f"Error getting configuration for key {key}: {e}")
            return default

    def set_config(self, key: str, value: Any) -> bool:
        """
        Set a configuration value.

        Args:
            key: Configuration key in format 'file.section.key'
            value: Value to set

        Returns:
            True if successful, False otherwise
        """
        try:
            parts = key.split('.')

            if len(parts) < 2:
                raise ValueError(f"Invalid configuration key format: {key}")

            filename = f"{parts[0]}.yaml"
            if filename not in self.config_cache:
                filename = f"{parts[0]}.json"
                if filename not in self.config_cache:
                    logger.error(f"Configuration file not found for key: {key}")
                    return False

            config_data = self.config_cache[filename]

            # Navigate to the parent of the target key
            current = config_data
            for part in parts[1:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Set the value
            current[parts[-1]] = value

            # Update timestamp
            self.config_timestamps[filename] = datetime.utcnow()

            logger.info(f"Configuration updated: {key}")
            return True

        except Exception as e:
            logger.error(f"Error setting configuration for key {key}: {e}")
            return False

    def get_prompts_config(self) -> Dict[str, Any]:
        """Get the complete prompts configuration."""
        return self.config_cache.get('prompts.yaml', {})

    def get_tasks_config(self) -> Dict[str, Any]:
        """Get the complete tasks configuration."""
        return self.config_cache.get('tasks.yaml', {})

    def get_domains_config(self) -> Dict[str, Any]:
        """Get the complete domains configuration."""
        return self.config_cache.get('domains.json', {})

    def get_llm_binding_config(self) -> Dict[str, Any]:
        """Get the complete LLM binding configuration."""
        return self.config_cache.get('llm_binding.yaml', {})

    def get_agent_list_config(self) -> Dict[str, Any]:
        """Get the complete agent list configuration."""
        return self.config_cache.get('agent_list.yaml', {})

    def get_domain_list(self) -> List[str]:
        """Get the list of available domains."""
        domains_config = self.get_domains_config()
        return domains_config.get('domains', [])

    def validate_domain(self, domain: str) -> bool:
        """
        Validate if a domain is in the allowed list.

        Args:
            domain: Domain name to validate

        Returns:
            True if domain is valid, False otherwise
        """
        domain_list = self.get_domain_list()
        return domain in domain_list

    def get_role_config(self, role_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific role.

        Args:
            role_name: Name of the role

        Returns:
            Role configuration or None if not found
        """
        prompts_config = self.get_prompts_config()
        roles = prompts_config.get('roles', {})
        return roles.get(role_name)

    def get_llm_binding(self, role_name: str) -> Optional[Dict[str, Any]]:
        """
        Get LLM binding configuration for a specific role/agent.

        Args:
            role_name: Name of the role/agent

        Returns:
            LLM binding configuration with provider and model, or None if not found
        """
        llm_binding_config = self.get_llm_binding_config()
        llm_bindings = llm_binding_config.get('llm_bindings', {})
        return llm_bindings.get(role_name)

    def get_agent_category(self, agent_name: str) -> Optional[str]:
        """
        Get the category for a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Category name or None if not found
        """
        agent_list_config = self.get_agent_list_config()
        agent_categories = agent_list_config.get('agent_categories', {})

        for category_name, category_config in agent_categories.items():
            agents = category_config.get('agents', [])
            if agent_name in agents:
                return category_name
        return None

    def list_agents_by_category(self, category: str = None) -> Union[List[str], Dict[str, List[str]]]:
        """
        List agents by category.

        Args:
            category: Specific category to list agents from. If None, returns all categories.

        Returns:
            List of agents if category specified, or dict mapping categories to agent lists
        """
        agent_list_config = self.get_agent_list_config()
        agent_categories = agent_list_config.get('agent_categories', {})

        if category:
            category_config = agent_categories.get(category, {})
            return category_config.get('agents', [])
        else:
            result = {}
            for category_name, category_config in agent_categories.items():
                result[category_name] = category_config.get('agents', [])
            return result

    def get_task_config(self, task_name: str, task_section: str = None) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific task.

        Args:
            task_name: Name of the task
            task_section: Section to search in ('system_tasks' or 'sub_tasks')
                         If None, searches both sections

        Returns:
            Task configuration or None if not found
        """
        tasks_config = self.get_tasks_config()

        if task_section:
            section = tasks_config.get(task_section, {})
            return section.get(task_name)
        else:
            # Search in both sections
            for section_name in ['system_tasks', 'sub_tasks']:
                section = tasks_config.get(section_name, {})
                if task_name in section:
                    return section[task_name]
            return None

    def list_available_tasks(self, task_section: str = None) -> List[str]:
        """
        List all available tasks.

        Args:
            task_section: Section to list from ('system_tasks' or 'sub_tasks')
                         If None, lists from both sections

        Returns:
            List of task names
        """
        tasks_config = self.get_tasks_config()

        if task_section:
            section = tasks_config.get(task_section, {})
            return list(section.keys())
        else:
            # Combine both sections
            all_tasks = []
            for section_name in ['system_tasks', 'sub_tasks']:
                section = tasks_config.get(section_name, {})
                all_tasks.extend(section.keys())
            return all_tasks

    def list_available_roles(self) -> List[str]:
        """
        List all available roles.

        Returns:
            List of role names
        """
        prompts_config = self.get_prompts_config()
        roles = prompts_config.get('roles', {})
        return list(roles.keys())

    def reload_config(self) -> None:
        """Reload all configuration files."""
        try:
            logger.info("Reloading all configuration files")
            self.config_cache.clear()
            self.config_timestamps.clear()
            self._load_all_configs()
            logger.info("Configuration reload completed")

        except Exception as e:
            logger.error(f"Failed to reload configurations: {e}")
            raise TaskValidationError(
                message=f"Configuration reload failed: {e}",
                validation_errors={"reload_error": str(e)}
            )

    def watch_config_changes(self) -> None:
        """Start watching for configuration file changes."""
        try:
            if self.observer is not None:
                self.stop_watching()

            self.file_handler = ConfigFileHandler(self)
            self.observer = Observer()
            self.observer.schedule(
                self.file_handler,
                str(self.config_dir),
                recursive=False
            )
            self.observer.start()

            logger.info("Started watching for configuration file changes")

        except Exception as e:
            logger.error(f"Failed to start configuration file watcher: {e}")

    def stop_watching(self) -> None:
        """Stop watching for configuration file changes."""
        try:
            if self.observer is not None:
                self.observer.stop()
                self.observer.join()
                self.observer = None
                self.file_handler = None

            logger.info("Stopped watching for configuration file changes")

        except Exception as e:
            logger.error(f"Failed to stop configuration file watcher: {e}")

    def get_config_info(self) -> Dict[str, Any]:
        """
        Get information about loaded configurations.

        Returns:
            Dictionary containing configuration metadata
        """
        return {
            'config_dir': str(self.config_dir),
            'loaded_files': list(self.config_cache.keys()),
            'file_timestamps': {
                filename: timestamp.isoformat()
                for filename, timestamp in self.config_timestamps.items()
            },
            'watching_changes': False,  # File watching disabled - configs are static
            'total_domains': len(self.get_domain_list()),
            'total_roles': len(self.list_available_roles()),
            'total_tasks': len(self.list_available_tasks())
        }

    def validate_all_configs(self) -> Dict[str, Any]:
        """
        Validate all loaded configurations.

        Returns:
            Validation results for all configurations
        """
        results = {}

        try:
            # Validate prompts configuration
            prompts_config = self.get_prompts_config()
            if prompts_config:
                results['prompts.yaml'] = self.validator.validate_config(
                    'prompts.yaml', prompts_config
                )

            # Validate tasks configuration
            tasks_config = self.get_tasks_config()
            if tasks_config:
                results['tasks.yaml'] = self.validator.validate_config(
                    'tasks.yaml', tasks_config
                )

            # Validate domains configuration
            domain_list = self.get_domain_list()
            if domain_list:
                results['domains'] = self.validator.validate_domains(domain_list)

            return results

        except Exception as e:
            logger.error(f"Error during configuration validation: {e}")
            return {
                'error': str(e),
                'validation_failed': True
            }

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_watching()
