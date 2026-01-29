#!/usr/bin/env python3
"""
PPT Tool

This tool integrates with banana-slides MCP server to provide PPT generation capabilities.
It allows frontend developers to create, edit, and export PowerPoint presentations using
the banana-slides MCP server running on port 5000.

Key Features:
1. Project management (create, list, get, update, delete)
2. Content generation (outline, descriptions, images)
3. Page management (create, update, delete)
4. Export functionality (PPTX, PDF, editable PPTX)
5. Template and material management
6. File upload and reference management
"""

import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from enum import Enum

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool


class CreationType(str, Enum):
    """PPT creation types"""
    IDEA = "idea"
    OUTLINE = "outline"
    DESCRIPTIONS = "descriptions"


class ExportFormat(str, Enum):
    """Export formats"""
    PPTX = "pptx"
    PDF = "pdf"
    EDITABLE_PPTX = "editable_pptx"


class PPTToolError(Exception):
    """Base exception for PPT Tool errors"""


class MCPConnectionError(PPTToolError):
    """Raised when MCP server connection fails"""


class MCPToolError(PPTToolError):
    """Raised when MCP tool execution fails"""


@register_tool("ppt_tool")
class PPTTool(BaseTool):
    """
    PPT Tool for creating and managing PowerPoint presentations via banana-slides MCP server
    
    This tool provides:
    1. Project management (create, list, get, update, delete)
    2. Content generation (outline, descriptions, images)
    3. Page management (create, update, delete)
    4. Export functionality (PPTX, PDF, editable PPTX)
    5. Template and material management
    6. File upload and reference management
    
    The tool communicates with banana-slides MCP server via HTTP at the configured base URL.
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the PPT tool
        
        Automatically reads from environment variables with PPT_TOOL_ prefix.
        Example: PPT_TOOL_MCP_BASE_URL -> mcp_base_url
        """

        model_config = SettingsConfigDict(env_prefix="PPT_TOOL_")

        mcp_base_url: str = Field(
            default="http://localhost:5000",
            description="Base URL of banana-slides MCP server"
        )
        timeout: int = Field(
            default=300,
            description="Request timeout in seconds"
        )
        max_retries: int = Field(
            default=3,
            description="Maximum number of retries for failed requests"
        )

    def __init__(self, config: Optional[Dict] = None, **kwargs):
        """Initialize PPT Tool with settings
        
        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/ppt_tool.yaml)
        3. Environment variables (via dotenv from .env files)
        4. Tool defaults (lowest priority)
        
        Args:
            config: Optional configuration overrides
            **kwargs: Additional arguments passed to BaseTool (e.g., tool_name)
        """
        super().__init__(config, **kwargs)
        
        # Configuration is automatically loaded by BaseTool into self._config_obj
        # Access config via self._config_obj (BaseSettings instance)
        self.config = self._config_obj if self._config_obj else self.Config()
        
        self.logger = logging.getLogger(__name__)
        
        # Validate MCP server connection
        self._validate_mcp_connection()

    def _validate_mcp_connection(self):
        """Validate that MCP server is accessible"""
        try:
            health_url = f"{self.config.mcp_base_url}/health"
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                self.logger.info(f"MCP server connection validated: {self.config.mcp_base_url}")
            else:
                self.logger.warning(f"MCP server health check returned {response.status_code}")
        except Exception as e:
            self.logger.warning(f"Could not validate MCP server connection: {e}. Tool will still work but may fail at runtime.")

    def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool on the banana-slides server
        
        Args:
            tool_name: Name of the MCP tool to call
            arguments: Tool arguments
            
        Returns:
            Dict containing tool response
            
        Raises:
            MCPConnectionError: If connection to MCP server fails
            MCPToolError: If tool execution fails
        """
        url = f"{self.config.mcp_base_url}/mcp/v1/tools/call"
        
        payload = {
            "name": tool_name,
            "arguments": arguments
        }
        
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.config.timeout
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_info = error_data.get('error', {})
                error_code = error_info.get('code', 'UNKNOWN_ERROR')
                error_message = error_info.get('message', f"HTTP {response.status_code}")
                raise MCPToolError(f"MCP tool '{tool_name}' failed: {error_code} - {error_message}")
            
            result = response.json()
            
            # Extract content from MCP response format
            if 'content' in result and len(result['content']) > 0:
                content_item = result['content'][0]
                if content_item.get('type') == 'text':
                    text_content = content_item.get('text', '')
                    try:
                        return json.loads(text_content)
                    except json.JSONDecodeError:
                        return {"result": text_content}
            
            return result
            
        except requests.exceptions.RequestException as e:
            raise MCPConnectionError(f"Failed to connect to MCP server at {self.config.mcp_base_url}: {str(e)}")
        except MCPToolError:
            raise
        except Exception as e:
            raise MCPToolError(f"Unexpected error calling MCP tool '{tool_name}': {str(e)}")

    # Schema definitions
    class Create_projectSchema(BaseModel):
        """Schema for create_project operation"""
        creation_type: CreationType = Field(description="Type of project creation: idea, outline, or descriptions")
        idea_prompt: Optional[str] = Field(default=None, description="Topic or idea for PPT (required for idea type)")
        outline_text: Optional[str] = Field(default=None, description="Outline text (required for outline type)")
        description_text: Optional[str] = Field(default=None, description="Description text (required for descriptions type)")
        template_style: Optional[str] = Field(default=None, description="Template style preset")

    class List_projectsSchema(BaseModel):
        """Schema for list_projects operation"""
        limit: Optional[int] = Field(default=50, ge=1, le=100, description="Maximum number of projects to return")
        offset: Optional[int] = Field(default=0, ge=0, description="Offset for pagination")

    class Get_projectSchema(BaseModel):
        """Schema for get_project operation"""
        project_id: str = Field(description="Project ID")

    class Update_projectSchema(BaseModel):
        """Schema for update_project operation"""
        project_id: str = Field(description="Project ID")
        idea_prompt: Optional[str] = Field(default=None, description="Updated idea prompt")
        extra_requirements: Optional[str] = Field(default=None, description="Extra requirements")
        template_style: Optional[str] = Field(default=None, description="Template style")
        pages_order: Optional[List[str]] = Field(default=None, description="Order of page IDs")

    class Delete_projectSchema(BaseModel):
        """Schema for delete_project operation"""
        project_id: str = Field(description="Project ID")

    class Generate_outlineSchema(BaseModel):
        """Schema for generate_outline operation"""
        project_id: str = Field(description="Project ID")
        idea_prompt: Optional[str] = Field(default=None, description="Idea prompt for outline generation")
        language: Optional[str] = Field(default="zh", description="Language code (default: zh)")

    class Generate_descriptionsSchema(BaseModel):
        """Schema for generate_descriptions operation"""
        project_id: str = Field(description="Project ID")
        max_workers: Optional[int] = Field(default=5, description="Maximum number of parallel workers")
        language: Optional[str] = Field(default="zh", description="Language code (default: zh)")

    class Generate_imagesSchema(BaseModel):
        """Schema for generate_images operation"""
        project_id: str = Field(description="Project ID")
        max_workers: Optional[int] = Field(default=5, description="Maximum number of parallel workers")

    class Export_pptxSchema(BaseModel):
        """Schema for export_pptx operation"""
        project_id: str = Field(description="Project ID")
        filename: Optional[str] = Field(default=None, description="Custom filename")
        page_ids: Optional[List[str]] = Field(default=None, description="Specific page IDs to export")

    class Export_pdfSchema(BaseModel):
        """Schema for export_pdf operation"""
        project_id: str = Field(description="Project ID")
        filename: Optional[str] = Field(default=None, description="Custom filename")
        page_ids: Optional[List[str]] = Field(default=None, description="Specific page IDs to export")

    class Export_editable_pptxSchema(BaseModel):
        """Schema for export_editable_pptx operation"""
        project_id: str = Field(description="Project ID")
        filename: Optional[str] = Field(default=None, description="Custom filename")
        page_ids: Optional[List[str]] = Field(default=None, description="Specific page IDs to export")

    class Create_pageSchema(BaseModel):
        """Schema for create_page operation"""
        project_id: str = Field(description="Project ID")
        order_index: int = Field(description="Position where page should be inserted")
        part: Optional[str] = Field(default=None, description="Part identifier")
        outline_content: Optional[Dict[str, Any]] = Field(default=None, description="Outline content with title and points")

    class Update_pageSchema(BaseModel):
        """Schema for update_page operation"""
        project_id: str = Field(description="Project ID")
        page_id: str = Field(description="Page ID")
        outline_content: Optional[Dict[str, Any]] = Field(default=None, description="Outline content to update")
        description_content: Optional[Dict[str, Any]] = Field(default=None, description="Description content to update")

    class Delete_pageSchema(BaseModel):
        """Schema for delete_page operation"""
        project_id: str = Field(description="Project ID")
        page_id: str = Field(description="Page ID")

    class Get_task_statusSchema(BaseModel):
        """Schema for get_task_status operation"""
        task_id: str = Field(description="Task ID")

    class List_tasksSchema(BaseModel):
        """Schema for list_tasks operation"""
        limit: Optional[int] = Field(default=50, ge=1, le=100, description="Maximum number of tasks to return")
        offset: Optional[int] = Field(default=0, ge=0, description="Offset for pagination")

    # Content generation schemas (single page)
    class Generate_descriptionSchema(BaseModel):
        """Schema for generate_description operation"""
        project_id: str = Field(description="Project ID")
        page_id: str = Field(description="Page ID")
        force_regenerate: Optional[bool] = Field(default=False, description="Force regeneration even if description already exists")
        language: Optional[str] = Field(default="zh", description="Language code (default: zh)")

    class Generate_imageSchema(BaseModel):
        """Schema for generate_image operation"""
        project_id: str = Field(description="Project ID")
        page_id: str = Field(description="Page ID")
        use_template: Optional[bool] = Field(default=True, description="Whether to use template image for style reference")
        force_regenerate: Optional[bool] = Field(default=False, description="Force regeneration even if image already exists")
        language: Optional[str] = Field(default="zh", description="Language code (default: zh)")

    # Image editing schemas
    class Image_editSchema(BaseModel):
        """Schema for image_edit operation"""
        project_id: str = Field(description="Project ID")
        page_id: str = Field(description="Page ID")
        edit_instruction: str = Field(description="Natural language instruction for editing the image")
        use_template: Optional[bool] = Field(default=False, description="Whether to use template image as reference")
        desc_image_urls: Optional[List[str]] = Field(default=None, description="Optional list of image URLs from page description")
        context_images: Optional[List[Dict[str, Any]]] = Field(default=None, description="Optional list of base64-encoded images with format: [{\"file_data\": \"base64...\", \"filename\": \"image.png\"}, ...]")

    class Image_list_versionsSchema(BaseModel):
        """Schema for image_list_versions operation"""
        project_id: str = Field(description="Project ID")
        page_id: str = Field(description="Page ID")

    class Image_revert_versionSchema(BaseModel):
        """Schema for image_revert_version operation"""
        project_id: str = Field(description="Project ID")
        page_id: str = Field(description="Page ID")
        version_id: str = Field(description="ID of the version to revert to")

    # Material management schemas
    class Material_uploadSchema(BaseModel):
        """Schema for material_upload operation"""
        project_id: str = Field(description="Project ID")
        file_data: str = Field(description="Base64-encoded image data (with or without data URI prefix)")
        filename: Optional[str] = Field(default=None, description="Filename for the image (optional, defaults to material.png)")

    class Material_upload_globalSchema(BaseModel):
        """Schema for material_upload_global operation"""
        file_data: str = Field(description="Base64-encoded image data (with or without data URI prefix)")
        filename: Optional[str] = Field(default=None, description="Filename for the image (optional, defaults to material.png)")
        project_id: Optional[str] = Field(default=None, description="Optional project ID to associate with")

    class Material_generateSchema(BaseModel):
        """Schema for material_generate operation"""
        project_id: str = Field(description="Project ID (or 'none' for global material)")
        prompt: str = Field(description="Text-to-image prompt for generating the material")
        ref_image: Optional[Dict[str, Any]] = Field(default=None, description="Optional main reference image with format: {\"file_data\": \"base64...\", \"filename\": \"ref.png\"}")
        extra_images: Optional[List[Dict[str, Any]]] = Field(default=None, description="Optional additional reference images")

    class Material_listSchema(BaseModel):
        """Schema for material_list operation"""
        project_id: str = Field(description="Project ID")

    class Material_list_globalSchema(BaseModel):
        """Schema for material_list_global operation"""
        project_id: Optional[str] = Field(default="all", description="Filter by project: 'all' (all materials), 'none' (global materials only), or specific project_id")

    class Material_deleteSchema(BaseModel):
        """Schema for material_delete operation"""
        material_id: str = Field(description="Material ID")

    # Template management schemas
    class Template_uploadSchema(BaseModel):
        """Schema for template_upload operation"""
        project_id: str = Field(description="Project ID")
        file_data: str = Field(description="Base64-encoded image data (with or without data URI prefix)")
        filename: Optional[str] = Field(default=None, description="Filename for the image (optional, defaults to template.png)")

    class Template_deleteSchema(BaseModel):
        """Schema for template_delete operation"""
        project_id: str = Field(description="Project ID")

    class Template_getSchema(BaseModel):
        """Schema for template_get operation"""
        project_id: str = Field(description="Project ID")

    class Template_user_createSchema(BaseModel):
        """Schema for template_user_create operation"""
        file_data: str = Field(description="Base64-encoded image data (with or without data URI prefix)")
        filename: Optional[str] = Field(default=None, description="Filename for the image (optional, defaults to template.png)")
        name: Optional[str] = Field(default=None, description="Optional name for the template")

    class Template_user_listSchema(BaseModel):
        """Schema for template_user_list operation"""
        pass  # No parameters

    class Template_user_applySchema(BaseModel):
        """Schema for template_user_apply operation"""
        project_id: str = Field(description="Project ID")
        template_id: str = Field(description="User template ID")

    # Project management methods
    def create_project(
        self,
        creation_type: CreationType,
        idea_prompt: Optional[str] = None,
        outline_text: Optional[str] = None,
        description_text: Optional[str] = None,
        template_style: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new PPT project
        
        Args:
            creation_type: Type of creation (idea, outline, or descriptions)
            idea_prompt: Topic/idea for PPT (required for idea type)
            outline_text: Outline text (required for outline type)
            description_text: Description text (required for descriptions type)
            template_style: Template style preset
            
        Returns:
            Dict containing project_id and status
        """
        arguments = {
            "creation_type": creation_type.value,
        }
        
        if creation_type == CreationType.IDEA:
            if not idea_prompt:
                raise ValueError("idea_prompt is required for idea type")
            arguments["idea_prompt"] = idea_prompt
        elif creation_type == CreationType.OUTLINE:
            if not outline_text:
                raise ValueError("outline_text is required for outline type")
            arguments["outline_text"] = outline_text
        elif creation_type == CreationType.DESCRIPTIONS:
            if not description_text:
                raise ValueError("description_text is required for descriptions type")
            arguments["description_text"] = description_text
        
        if template_style:
            arguments["template_style"] = template_style
        
        return self._call_mcp_tool("project_create", arguments)

    def list_projects(
        self,
        limit: Optional[int] = 50,
        offset: Optional[int] = 0,
    ) -> Dict[str, Any]:
        """
        List all PPT projects
        
        Args:
            limit: Maximum number of projects to return (1-100)
            offset: Offset for pagination
            
        Returns:
            Dict containing projects list and pagination info
        """
        arguments = {}
        if limit is not None:
            arguments["limit"] = limit
        if offset is not None:
            arguments["offset"] = offset
        
        return self._call_mcp_tool("project_list", arguments)

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        Get project details by ID
        
        Args:
            project_id: Project ID
            
        Returns:
            Dict containing project details
        """
        arguments = {"project_id": project_id}
        return self._call_mcp_tool("project_get", arguments)

    def update_project(
        self,
        project_id: str,
        idea_prompt: Optional[str] = None,
        extra_requirements: Optional[str] = None,
        template_style: Optional[str] = None,
        pages_order: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Update project settings
        
        Args:
            project_id: Project ID
            idea_prompt: Updated idea prompt
            extra_requirements: Extra requirements
            template_style: Template style
            pages_order: Order of page IDs
            
        Returns:
            Dict containing updated project details
        """
        arguments = {"project_id": project_id}
        
        if idea_prompt is not None:
            arguments["idea_prompt"] = idea_prompt
        if extra_requirements is not None:
            arguments["extra_requirements"] = extra_requirements
        if template_style is not None:
            arguments["template_style"] = template_style
        if pages_order is not None:
            arguments["pages_order"] = pages_order
        
        return self._call_mcp_tool("project_update", arguments)

    def delete_project(self, project_id: str) -> Dict[str, Any]:
        """
        Delete a project
        
        Args:
            project_id: Project ID
            
        Returns:
            Dict containing success message
        """
        arguments = {"project_id": project_id}
        return self._call_mcp_tool("project_delete", arguments)

    # Content generation methods
    def generate_outline(
        self,
        project_id: str,
        idea_prompt: Optional[str] = None,
        language: Optional[str] = "zh",
    ) -> Dict[str, Any]:
        """
        Generate outline from topic
        
        Args:
            project_id: Project ID
            idea_prompt: Idea prompt for outline generation
            language: Language code (default: zh)
            
        Returns:
            Dict containing generated pages
        """
        arguments = {"project_id": project_id}
        
        if idea_prompt is not None:
            arguments["idea_prompt"] = idea_prompt
        if language is not None:
            arguments["language"] = language
        
        return self._call_mcp_tool("content_generate_outline", arguments)

    def generate_descriptions(
        self,
        project_id: str,
        max_workers: Optional[int] = 5,
        language: Optional[str] = "zh",
    ) -> Dict[str, Any]:
        """
        Batch generate descriptions for all pages
        
        Args:
            project_id: Project ID
            max_workers: Maximum number of parallel workers
            language: Language code (default: zh)
            
        Returns:
            Dict containing task_id for async operation
        """
        arguments = {"project_id": project_id}
        
        if max_workers is not None:
            arguments["max_workers"] = max_workers
        if language is not None:
            arguments["language"] = language
        
        return self._call_mcp_tool("content_generate_descriptions", arguments)

    def generate_images(
        self,
        project_id: str,
        max_workers: Optional[int] = 5,
    ) -> Dict[str, Any]:
        """
        Batch generate images for all pages
        
        Args:
            project_id: Project ID
            max_workers: Maximum number of parallel workers
            
        Returns:
            Dict containing task_id for async operation
        """
        arguments = {"project_id": project_id}
        
        if max_workers is not None:
            arguments["max_workers"] = max_workers
        
        return self._call_mcp_tool("content_generate_images", arguments)

    # Export methods
    def export_pptx(
        self,
        project_id: str,
        filename: Optional[str] = None,
        page_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Export project to PPTX format
        
        Args:
            project_id: Project ID
            filename: Custom filename (optional)
            page_ids: Specific page IDs to export (optional, exports all if not provided)
            
        Returns:
            Dict containing download_url and download_url_absolute
        """
        arguments = {"project_id": project_id}
        
        if filename is not None:
            arguments["filename"] = filename
        if page_ids is not None:
            arguments["page_ids"] = page_ids
        
        return self._call_mcp_tool("export_pptx", arguments)

    def export_pdf(
        self,
        project_id: str,
        filename: Optional[str] = None,
        page_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Export project to PDF format
        
        Args:
            project_id: Project ID
            filename: Custom filename (optional)
            page_ids: Specific page IDs to export (optional, exports all if not provided)
            
        Returns:
            Dict containing download_url and download_url_absolute
        """
        arguments = {"project_id": project_id}
        
        if filename is not None:
            arguments["filename"] = filename
        if page_ids is not None:
            arguments["page_ids"] = page_ids
        
        return self._call_mcp_tool("export_pdf", arguments)

    def export_editable_pptx(
        self,
        project_id: str,
        filename: Optional[str] = None,
        page_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Export project to editable PPTX format (Beta)
        
        Args:
            project_id: Project ID
            filename: Custom filename (optional)
            page_ids: Specific page IDs to export (optional, exports all if not provided)
            
        Returns:
            Dict containing download_url and download_url_absolute
        """
        arguments = {"project_id": project_id}
        
        if filename is not None:
            arguments["filename"] = filename
        if page_ids is not None:
            arguments["page_ids"] = page_ids
        
        return self._call_mcp_tool("export_editable_pptx", arguments)

    # Page management methods
    def create_page(
        self,
        project_id: str,
        order_index: int,
        part: Optional[str] = None,
        outline_content: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new page in the project
        
        Args:
            project_id: Project ID
            order_index: Position where page should be inserted
            part: Part identifier (optional)
            outline_content: Outline content with title and points (optional)
            
        Returns:
            Dict containing created page details
        """
        arguments = {
            "project_id": project_id,
            "order_index": order_index,
        }
        
        if part is not None:
            arguments["part"] = part
        if outline_content is not None:
            arguments["outline_content"] = outline_content
        
        return self._call_mcp_tool("page_create", arguments)

    def update_page(
        self,
        project_id: str,
        page_id: str,
        outline_content: Optional[Dict[str, Any]] = None,
        description_content: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Update page content
        
        Args:
            project_id: Project ID
            page_id: Page ID
            outline_content: Outline content to update (optional)
            description_content: Description content to update (optional)
            
        Returns:
            Dict containing updated page details
        """
        if not outline_content and not description_content:
            raise ValueError("At least one of outline_content or description_content must be provided")
        
        arguments = {
            "project_id": project_id,
            "page_id": page_id,
        }
        
        if outline_content is not None:
            arguments["outline_content"] = outline_content
        if description_content is not None:
            arguments["description_content"] = description_content
        
        return self._call_mcp_tool("page_update", arguments)

    def delete_page(
        self,
        project_id: str,
        page_id: str,
    ) -> Dict[str, Any]:
        """
        Delete a page from the project
        
        Args:
            project_id: Project ID
            page_id: Page ID
            
        Returns:
            Dict containing success message
        """
        arguments = {
            "project_id": project_id,
            "page_id": page_id,
        }
        
        return self._call_mcp_tool("page_delete", arguments)

    # Task management methods
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get task status by ID
        
        Args:
            task_id: Task ID
            
        Returns:
            Dict containing task status and progress
        """
        arguments = {"task_id": task_id}
        return self._call_mcp_tool("task_get_status", arguments)

    def list_tasks(
        self,
        limit: Optional[int] = 50,
        offset: Optional[int] = 0,
    ) -> Dict[str, Any]:
        """
        List all tasks
        
        Args:
            limit: Maximum number of tasks to return (1-100)
            offset: Offset for pagination
            
        Returns:
            Dict containing tasks list and pagination info
        """
        arguments = {}
        if limit is not None:
            arguments["limit"] = limit
        if offset is not None:
            arguments["offset"] = offset
        
        return self._call_mcp_tool("task_list", arguments)

    # Content generation methods (single page)
    def generate_description(
        self,
        project_id: str,
        page_id: str,
        force_regenerate: Optional[bool] = False,
        language: Optional[str] = "zh",
    ) -> Dict[str, Any]:
        """
        Generate description for a single page
        
        Args:
            project_id: Project ID
            page_id: Page ID
            force_regenerate: Force regeneration even if description already exists
            language: Language code (default: zh)
            
        Returns:
            Dict containing updated page details
        """
        arguments = {
            "project_id": project_id,
            "page_id": page_id,
        }
        
        if force_regenerate is not None:
            arguments["force_regenerate"] = force_regenerate
        if language is not None:
            arguments["language"] = language
        
        return self._call_mcp_tool("content_generate_description", arguments)

    def generate_image(
        self,
        project_id: str,
        page_id: str,
        use_template: Optional[bool] = True,
        force_regenerate: Optional[bool] = False,
        language: Optional[str] = "zh",
    ) -> Dict[str, Any]:
        """
        Generate image for a single page
        
        Args:
            project_id: Project ID
            page_id: Page ID
            use_template: Whether to use template image for style reference
            force_regenerate: Force regeneration even if image already exists
            language: Language code (default: zh)
            
        Returns:
            Dict containing updated page details including image URL
        """
        arguments = {
            "project_id": project_id,
            "page_id": page_id,
        }
        
        if use_template is not None:
            arguments["use_template"] = use_template
        if force_regenerate is not None:
            arguments["force_regenerate"] = force_regenerate
        if language is not None:
            arguments["language"] = language
        
        return self._call_mcp_tool("content_generate_image", arguments)

    # Image editing methods
    def image_edit(
        self,
        project_id: str,
        page_id: str,
        edit_instruction: str,
        use_template: Optional[bool] = False,
        desc_image_urls: Optional[List[str]] = None,
        context_images: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Edit a page image using natural language instructions (vibe editing)
        
        Args:
            project_id: Project ID
            page_id: Page ID
            edit_instruction: Natural language instruction for editing the image
            use_template: Whether to use template image as reference
            desc_image_urls: Optional list of image URLs from page description
            context_images: Optional list of base64-encoded images with format:
                [{"file_data": "base64...", "filename": "image.png"}, ...]
            
        Returns:
            Dict containing task_id for async operation
        """
        arguments = {
            "project_id": project_id,
            "page_id": page_id,
            "edit_instruction": edit_instruction,
        }
        
        if use_template is not None:
            arguments["use_template"] = use_template
        if desc_image_urls is not None:
            arguments["desc_image_urls"] = desc_image_urls
        if context_images is not None:
            arguments["context_images"] = context_images
        
        return self._call_mcp_tool("image_edit", arguments)

    def image_list_versions(
        self,
        project_id: str,
        page_id: str,
    ) -> Dict[str, Any]:
        """
        List all image versions for a page
        
        Args:
            project_id: Project ID
            page_id: Page ID
            
        Returns:
            Dict containing list of image versions
        """
        arguments = {
            "project_id": project_id,
            "page_id": page_id,
        }
        
        return self._call_mcp_tool("image_list_versions", arguments)

    def image_revert_version(
        self,
        project_id: str,
        page_id: str,
        version_id: str,
    ) -> Dict[str, Any]:
        """
        Revert a page image to a previous version
        
        Args:
            project_id: Project ID
            page_id: Page ID
            version_id: ID of the version to revert to
            
        Returns:
            Dict containing updated page details
        """
        arguments = {
            "project_id": project_id,
            "page_id": page_id,
            "version_id": version_id,
        }
        
        return self._call_mcp_tool("image_revert_version", arguments)

    # Material management methods
    def material_upload(
        self,
        project_id: str,
        file_data: str,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a material image to a project (base64-encoded)
        
        Args:
            project_id: Project ID
            file_data: Base64-encoded image data (with or without data URI prefix)
            filename: Filename for the image (optional, defaults to material.png)
            
        Returns:
            Dict containing material details
        """
        arguments = {
            "project_id": project_id,
            "file_data": file_data,
        }
        
        if filename is not None:
            arguments["filename"] = filename
        
        return self._call_mcp_tool("material_upload", arguments)

    def material_upload_global(
        self,
        file_data: str,
        filename: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a global material image (base64-encoded, not bound to a project)
        
        Args:
            file_data: Base64-encoded image data (with or without data URI prefix)
            filename: Filename for the image (optional, defaults to material.png)
            project_id: Optional project ID to associate with
            
        Returns:
            Dict containing material details
        """
        arguments = {
            "file_data": file_data,
        }
        
        if filename is not None:
            arguments["filename"] = filename
        if project_id is not None:
            arguments["project_id"] = project_id
        
        return self._call_mcp_tool("material_upload_global", arguments)

    def material_generate(
        self,
        project_id: str,
        prompt: str,
        ref_image: Optional[Dict[str, Any]] = None,
        extra_images: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a material image using AI with text prompt and optional reference images (async)
        
        Args:
            project_id: Project ID (or 'none' for global material)
            prompt: Text-to-image prompt for generating the material
            ref_image: Optional main reference image with format: {"file_data": "base64...", "filename": "ref.png"}
            extra_images: Optional additional reference images
            
        Returns:
            Dict containing task_id for async operation
        """
        arguments = {
            "project_id": project_id,
            "prompt": prompt,
        }
        
        if ref_image is not None:
            arguments["ref_image"] = ref_image
        if extra_images is not None:
            arguments["extra_images"] = extra_images
        
        return self._call_mcp_tool("material_generate", arguments)

    def material_list(
        self,
        project_id: str,
    ) -> Dict[str, Any]:
        """
        List all materials for a specific project
        
        Args:
            project_id: Project ID
            
        Returns:
            Dict containing list of materials
        """
        arguments = {
            "project_id": project_id,
        }
        
        return self._call_mcp_tool("material_list", arguments)

    def material_list_global(
        self,
        project_id: Optional[str] = "all",
    ) -> Dict[str, Any]:
        """
        List all materials with optional project filter
        
        Args:
            project_id: Filter by project: 'all' (all materials), 'none' (global materials only), or specific project_id
            
        Returns:
            Dict containing list of materials
        """
        arguments = {}
        if project_id is not None:
            arguments["project_id"] = project_id
        
        return self._call_mcp_tool("material_list_global", arguments)

    def material_delete(
        self,
        material_id: str,
    ) -> Dict[str, Any]:
        """
        Delete a material and its associated file
        
        Args:
            material_id: Material ID
            
        Returns:
            Dict containing success message
        """
        arguments = {
            "material_id": material_id,
        }
        
        return self._call_mcp_tool("material_delete", arguments)

    # Template management methods
    def template_upload(
        self,
        project_id: str,
        file_data: str,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a template image for a project (base64-encoded)
        
        Args:
            project_id: Project ID
            file_data: Base64-encoded image data (with or without data URI prefix)
            filename: Filename for the image (optional, defaults to template.png)
            
        Returns:
            Dict containing template_image_url
        """
        arguments = {
            "project_id": project_id,
            "file_data": file_data,
        }
        
        if filename is not None:
            arguments["filename"] = filename
        
        return self._call_mcp_tool("template_upload", arguments)

    def template_delete(
        self,
        project_id: str,
    ) -> Dict[str, Any]:
        """
        Delete template image from a project
        
        Args:
            project_id: Project ID
            
        Returns:
            Dict containing success message
        """
        arguments = {
            "project_id": project_id,
        }
        
        return self._call_mcp_tool("template_delete", arguments)

    def template_get(
        self,
        project_id: str,
    ) -> Dict[str, Any]:
        """
        Get template image URL for a project
        
        Args:
            project_id: Project ID
            
        Returns:
            Dict containing template_image_url or null if no template
        """
        arguments = {
            "project_id": project_id,
        }
        
        return self._call_mcp_tool("template_get", arguments)

    def template_user_create(
        self,
        file_data: str,
        filename: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a reusable user template from base64-encoded image
        
        Args:
            file_data: Base64-encoded image data (with or without data URI prefix)
            filename: Filename for the image (optional, defaults to template.png)
            name: Optional name for the template
            
        Returns:
            Dict containing template details
        """
        arguments = {
            "file_data": file_data,
        }
        
        if filename is not None:
            arguments["filename"] = filename
        if name is not None:
            arguments["name"] = name
        
        return self._call_mcp_tool("template_user_create", arguments)

    def template_user_list(self) -> Dict[str, Any]:
        """
        List all user-created templates
        
        Returns:
            Dict containing list of user templates
        """
        arguments = {}
        return self._call_mcp_tool("template_user_list", arguments)

    def template_user_apply(
        self,
        project_id: str,
        template_id: str,
    ) -> Dict[str, Any]:
        """
        Apply a user template to a project (copies template to project)
        
        Args:
            project_id: Project ID to apply template to
            template_id: ID of the user template to apply
            
        Returns:
            Dict containing template_image_url
        """
        arguments = {
            "project_id": project_id,
            "template_id": template_id,
        }
        
        return self._call_mcp_tool("template_user_apply", arguments)
