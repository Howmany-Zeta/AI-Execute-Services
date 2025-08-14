"""
Prompt Configuration Schema

Pydantic schema definitions for prompt configuration validation.
"""

from pydantic import field_validator, ConfigDict, BaseModel, Field, model_validator
from typing import Dict, List, Optional, Any, Union
import re


class RoleSchema(BaseModel):
    """Schema for role configuration in prompts.yaml."""

    goal: str = Field(..., min_length=10, description="The role's primary goal or objective")
    backstory: str = Field(..., min_length=20, description="Background story and context for the role")
    tools: Optional[List[str]] = Field(None, description="List of tools available to this role")
    tools_instruction: Optional[str] = Field(None, description="Instructions for using tools")
    domain_specialization: Optional[str] = Field(None, description="Domain-specific specialization instructions")
    reasoning_guidance: Optional[str] = Field(None, description="ReAct framework reasoning guidance for the role")

    @field_validator('goal')
    @classmethod
    def validate_goal(cls, v):
        """Validate the goal field."""
        if not v.strip():
            raise ValueError("Goal cannot be empty or whitespace only")

        # Check for action words
        action_words = ['analyze', 'create', 'generate', 'process', 'manage', 'execute', 'validate', 'review']
        if not any(word in v.lower() for word in action_words):
            raise ValueError("Goal should contain action words describing what the role does")

        return v.strip()

    @field_validator('backstory')
    @classmethod
    def validate_backstory(cls, v):
        """Validate the backstory field."""
        if not v.strip():
            raise ValueError("Backstory cannot be empty or whitespace only")
        return v.strip()

    @field_validator('tools')
    @classmethod
    def validate_tools(cls, v):
        """Validate the tools list."""
        if v is None:
            return v

        valid_tools = {
            'chart', 'classifier', 'image', 'office', 'pandas',
            'report', 'research', 'scraper', 'stats', 'search_api'
        }

        for tool in v:
            if not isinstance(tool, str):
                raise ValueError(f"Tool name must be a string: {tool}")
            if tool not in valid_tools:
                raise ValueError(f"Unknown tool: {tool}. Valid tools: {valid_tools}")

        return v


    @model_validator(mode='after')
    def validate_tools_instruction(self) -> 'YourModelName': # Replace 'YourModelName' with your model's class name
        """Validates the consistency between the 'tools' list and the 'tools_instruction' text."""
        # Use self to access the model's fields
        tools_instruction = self.tools_instruction
        tools = self.tools

        if tools_instruction is None:
            return self

        # Check for unclosed thinking tags
        if '<thinking>' in tools_instruction and '</thinking>' not in tools_instruction:
            raise ValueError("Unclosed <thinking> tag in tools_instruction")

        # Check if tools are mentioned in instructions when tools list is provided
        if tools:
            for tool in tools:
                if tool not in tools_instruction:
                    raise ValueError(f"Tool '{tool}' is listed but not mentioned in tools_instruction")

        # Check for proper sub-operation format (tool.operation)
        sub_op_pattern = r'(\w+)\.(\w+)'
        sub_operations = re.findall(sub_op_pattern, tools_instruction)

        if tools and sub_operations:
            mentioned_tools = {op[0] for op in sub_operations}
            for tool in tools:
                if tool not in mentioned_tools:
                    raise ValueError(f"Tool '{tool}' is listed, but no sub-operations like 'tool_name.operation_name' are specified in the instructions.")

        # It's good practice to assign back the stripped value if validation passes
        self.tools_instruction = tools_instruction.strip()

        # Always return the self instance at the end
        return self

    @field_validator('domain_specialization')
    @classmethod
    def validate_domain_specialization(cls, v):
        """Validate the domain specialization field."""
        if v is None:
            return v

        # Check if it references the domain list (more flexible check)
        domain_indicators = ['DOMAINS', 'base.py', 'domain', 'specialize', 'adapt']
        if not any(indicator in v for indicator in domain_indicators):
            raise ValueError("Domain specialization should reference domains or specialization patterns")

        # Check for dynamic specialization pattern
        if 'Dynamically specialize' not in v:
            raise ValueError("Domain specialization should use 'Dynamically specialize' pattern")

        return v.strip()


class PromptSchema(BaseModel):
    """Schema for the complete prompts.yaml configuration."""

    system_prompt: str = Field(..., min_length=50, description="The main system prompt")
    roles: Dict[str, RoleSchema] = Field(..., description="Dictionary of role configurations")

    @field_validator('system_prompt')
    @classmethod
    def validate_system_prompt(cls, v):
        """Validate the system prompt."""
        if not v.strip():
            raise ValueError("System prompt cannot be empty")

        # Check for required sections
        required_sections = ['CAPABILITIES', 'TOOL USE GUIDELINES', 'RULES', 'OBJECTIVE']
        missing_sections = [section for section in required_sections if section not in v]

        if missing_sections:
            raise ValueError(f"System prompt missing required sections: {missing_sections}")

        return v.strip()

    @field_validator('roles')
    @classmethod
    def validate_roles(cls, v):
        """Validate the roles dictionary."""
        if not v:
            raise ValueError("At least one role must be defined")

        # Check for required system roles
        required_system_roles = [
            'intent_parser', 'task_decomposer', 'planner', 'supervisor', 'director'
        ]

        missing_system_roles = [role for role in required_system_roles if role not in v]
        if missing_system_roles:
            raise ValueError(f"Missing required system roles: {missing_system_roles}")

        # Check for role categories based on the YAML structure
        expected_categories = {
            'system': ['intent_parser', 'task_decomposer', 'supervisor', 'planner', 'director'],
            'answer': ['researcher_discussionfacilitator', 'researcher_knowledgeprovider',
                      'researcher_ideagenerator', 'writer_conclusionspecialist'],
            'collect': ['fieldwork_webscraper', 'fieldwork_apisearcher', 'fieldwork_internaldatacollector',
                       'fieldwork_externaldatacollector'],
            'process': ['fieldwork_dataoperator', 'fieldwork_dataengineer', 'fieldwork_statistician',
                       'fieldwork_datascientist', 'fieldwork_documentconverter', 'fieldwork_documentcleaner',
                       'fieldwork_documentsegmenter', 'fieldwork_textprocessor', 'fieldwork_dataextractor',
                       'fieldwork_imageextractor', 'fieldwork_imageprocessor'],
            'analyze': ['analyst_dataoutcomespecialist', 'analyst_contextspecialist', 'analyst_imageanalyst',
                       'analyst_classificationspecialist', 'analyst_codespecialist', 'analyst_predictivespecialist',
                       'analyst_refiningspecialist'],
            'generate': ['writer_formatspecialist', 'writer_tablespecialist', 'writer_contentspecialist',
                        'writer_summarizationspecialist', 'writer_visualizationspecialist', 'writer_imagespecialist',
                        'writer_reportspecialist', 'writer_codespecialist']
        }

        return v

    @classmethod
    def validate_role_completeness(cls, roles: Dict[str, 'RoleSchema']) -> List[str]:
        """Validate that all required role categories are covered."""
        warnings = []
        categories = cls.categorize_roles(roles)

        # Check minimum role counts per category
        min_requirements = {
            'system': 5,  # intent_parser, task_decomposer, supervisor, planner, director
            'answer': 2,  # At least 2 answer roles
            'collect': 2,  # At least 2 collect roles
            'process': 3,  # At least 3 process roles
            'analyze': 3,  # At least 3 analyze roles
            'generate': 3   # At least 3 generate roles
        }

        for category, min_count in min_requirements.items():
            actual_count = len(categories.get(category, []))
            if actual_count < min_count:
                warnings.append(f"Category '{category}' has {actual_count} roles, recommended minimum: {min_count}")

        return warnings

    @classmethod
    def categorize_roles(cls, roles: Dict[str, 'RoleSchema']) -> Dict[str, List[str]]:
        """Categorize roles based on their names and purposes."""
        categories = {
            'system': [],
            'answer': [],
            'collect': [],
            'process': [],
            'analyze': [],
            'generate': []
        }

        system_roles = ['intent_parser', 'task_decomposer', 'supervisor', 'planner', 'director']

        for role_name in roles.keys():
            if role_name in system_roles:
                categories['system'].append(role_name)
            elif role_name.startswith('researcher_') or role_name.startswith('writer_conclusion'):
                categories['answer'].append(role_name)
            elif role_name.startswith('fieldwork_') and any(x in role_name for x in ['scraper', 'searcher', 'collector']):
                categories['collect'].append(role_name)
            elif role_name.startswith('fieldwork_') and not any(x in role_name for x in ['scraper', 'searcher', 'collector']):
                categories['process'].append(role_name)
            elif role_name.startswith('analyst_'):
                categories['analyze'].append(role_name)
            elif role_name.startswith('writer_') and not role_name.startswith('writer_conclusion'):
                categories['generate'].append(role_name)

        return categories

    @classmethod
    def extract_tool_sub_operations(cls, roles: Dict[str, 'RoleSchema']) -> Dict[str, 'ToolSubOperationSchema']:
        """Extract tool sub-operations from role instructions."""
        tool_operations = {}

        for role_name, role in roles.items():
            if role.tools_instruction:
                # Find tool.operation patterns
                sub_op_pattern = r'(\w+)\.(\w+)'
                matches = re.findall(sub_op_pattern, role.tools_instruction)

                for tool_name, operation in matches:
                    if tool_name not in tool_operations:
                        tool_operations[tool_name] = ToolSubOperationSchema(
                            tool_name=tool_name,
                            sub_operations=[],
                            roles_using=[]
                        )

                    if operation not in tool_operations[tool_name].sub_operations:
                        tool_operations[tool_name].sub_operations.append(operation)

                    if role_name not in tool_operations[tool_name].roles_using:
                        tool_operations[tool_name].roles_using.append(role_name)

        return tool_operations

    @classmethod
    def validate_domain_specialization_patterns(cls, roles: Dict[str, 'RoleSchema']) -> Dict[str, 'DomainSpecializationSchema']:
        """Validate domain specialization patterns in roles."""
        domain_analysis = {}

        for role_name, role in roles.items():
            if role.domain_specialization:
                # Check for domain references
                has_domain_ref = 'DOMAINS' in role.domain_specialization or 'base.py' in role.domain_specialization
                has_dynamic = 'Dynamically specialize' in role.domain_specialization

                # Extract mentioned domains (basic pattern matching)
                domain_pattern = r'- ([A-Z][a-zA-Z\s]+):'
                mentioned_domains = re.findall(domain_pattern, role.domain_specialization)

                # Extract tool-domain mappings
                tool_domain_mapping = {}
                if role.tools_instruction:
                    tool_pattern = r'(\w+)\.(\w+)'
                    tools_ops = re.findall(tool_pattern, role.tools_instruction)
                    for domain in mentioned_domains:
                        tool_domain_mapping[domain] = [f"{t}.{o}" for t, o in tools_ops]

                domain_analysis[role_name] = DomainSpecializationSchema(
                    has_domain_reference=has_domain_ref,
                    mentioned_domains=mentioned_domains,
                    has_dynamic_specialization=has_dynamic,
                    tool_domain_mapping=tool_domain_mapping
                )

        return domain_analysis
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class PromptValidationSchema(BaseModel):
    """Schema for prompt validation results."""

    is_valid: bool = Field(..., description="Whether the configuration is valid")
    errors: Dict[str, List[str]] = Field(default_factory=dict, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    role_count: int = Field(..., description="Number of roles defined")
    system_roles_count: int = Field(..., description="Number of system roles defined")
    answer_roles_count: int = Field(default=0, description="Number of answer category roles defined")
    collect_roles_count: int = Field(default=0, description="Number of collect category roles defined")
    process_roles_count: int = Field(default=0, description="Number of process category roles defined")
    analyze_roles_count: int = Field(default=0, description="Number of analyze category roles defined")
    generate_roles_count: int = Field(default=0, description="Number of generate category roles defined")
    domain_roles_count: int = Field(..., description="Number of domain-specific roles defined")
    model_config = ConfigDict(extra="allow")


class RoleConsistencySchema(BaseModel):
    """Schema for role consistency validation."""

    duplicate_goals: Dict[str, List[str]] = Field(default_factory=dict, description="Roles with duplicate goals")
    tool_usage: Dict[str, List[str]] = Field(default_factory=dict, description="Tool usage by roles")
    unused_tools: List[str] = Field(default_factory=list, description="Tools not used by any role")
    category_coverage: Dict[str, List[str]] = Field(default_factory=dict, description="Role coverage by category")
    missing_categories: List[str] = Field(default_factory=list, description="Categories without dedicated roles")
    domain_specialization_coverage: Dict[str, List[str]] = Field(default_factory=dict, description="Roles with domain specialization by category")
    roles_without_domain_specialization: List[str] = Field(default_factory=list, description="Roles missing domain specialization")
    model_config = ConfigDict(extra="allow")


class ToolSubOperationSchema(BaseModel):
    """Schema for validating tool sub-operations mentioned in role instructions."""

    tool_name: str = Field(..., description="Name of the tool")
    sub_operations: List[str] = Field(default_factory=list, description="List of sub-operations for this tool")
    roles_using: List[str] = Field(default_factory=list, description="Roles that use this tool")
    model_config = ConfigDict(extra="allow")


class DomainSpecializationSchema(BaseModel):
    """Schema for validating domain specialization patterns."""

    has_domain_reference: bool = Field(..., description="Whether it references DOMAINS list")
    mentioned_domains: List[str] = Field(default_factory=list, description="Domains explicitly mentioned")
    has_dynamic_specialization: bool = Field(..., description="Whether it uses dynamic specialization pattern")
    tool_domain_mapping: Dict[str, List[str]] = Field(default_factory=dict, description="Tools mapped to specific domains")
    model_config = ConfigDict(extra="allow")
