#!/usr/bin/env python3
"""
Content Insertion Tool

This tool is responsible for inserting complex content elements
into documents, including charts, tables, images, and media.

Key Features:
1. Chart insertion (leveraging chart_tool)
2. Table insertion (leveraging pandas_tool)
3. Image insertion and optimization (leveraging image_tool)
4. Media content insertion (videos, audio, etc.)
5. Interactive elements (forms, buttons, etc.)
6. Cross-reference and citation management
"""

import os
import uuid
import tempfile
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple
from enum import Enum

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool


class ContentType(str, Enum):
    """Types of content that can be inserted"""

    CHART = "chart"
    TABLE = "table"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DIAGRAM = "diagram"
    FORM = "form"
    BUTTON = "button"
    LINK = "link"
    CITATION = "citation"
    FOOTNOTE = "footnote"
    CALLOUT = "callout"
    CODE_BLOCK = "code_block"
    EQUATION = "equation"
    GALLERY = "gallery"


class ChartType(str, Enum):
    """Chart types supported"""

    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    BOX = "box"
    HEATMAP = "heatmap"
    AREA = "area"
    BUBBLE = "bubble"
    GANTT = "gantt"


class TableStyle(str, Enum):
    """Table styling options"""

    DEFAULT = "default"
    SIMPLE = "simple"
    GRID = "grid"
    STRIPED = "striped"
    BORDERED = "bordered"
    CORPORATE = "corporate"
    ACADEMIC = "academic"
    MINIMAL = "minimal"
    COLORFUL = "colorful"


class ImageAlignment(str, Enum):
    """Image alignment options"""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    INLINE = "inline"
    FLOAT_LEFT = "float_left"
    FLOAT_RIGHT = "float_right"


class InsertionPosition(str, Enum):
    """Content insertion positions"""

    BEFORE = "before"
    AFTER = "after"
    REPLACE = "replace"
    APPEND = "append"
    PREPEND = "prepend"
    INLINE = "inline"


class ContentInsertionError(Exception):
    """Base exception for Content Insertion errors"""


class ChartInsertionError(ContentInsertionError):
    """Raised when chart insertion fails"""


class TableInsertionError(ContentInsertionError):
    """Raised when table insertion fails"""


class ImageInsertionError(ContentInsertionError):
    """Raised when image insertion fails"""


@register_tool("content_insertion")
class ContentInsertionTool(BaseTool):
    """
    Content Insertion Tool for adding complex content to documents

    This tool provides:
    1. Chart generation and insertion
    2. Table formatting and insertion
    3. Image processing and insertion
    4. Media content embedding
    5. Interactive element creation
    6. Cross-reference management

    Integrates with:
    - ChartTool for chart generation
    - PandasTool for table processing
    - ImageTool for image processing
    - DocumentWriterTool for content placement
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the content insertion tool
        
        Automatically reads from environment variables with CONTENT_INSERT_ prefix.
        Example: CONTENT_INSERT_TEMP_DIR -> temp_dir
        """

        model_config = SettingsConfigDict(env_prefix="CONTENT_INSERT_")

        temp_dir: str = Field(
            default=os.path.join(tempfile.gettempdir(), "content_insertion"),
            description="Temporary directory for content processing",
        )
        assets_dir: str = Field(
            default=os.path.join(tempfile.gettempdir(), "document_assets"),
            description="Directory for document assets",
        )
        max_image_size: int = Field(default=10 * 1024 * 1024, description="Maximum image size in bytes")
        max_chart_size: Tuple[int, int] = Field(
            default=(1200, 800),
            description="Maximum chart size in pixels (width, height)",
        )
        default_image_format: str = Field(
            default="png",
            description="Default image format for generated content",
        )
        optimize_images: bool = Field(
            default=True,
            description="Whether to optimize images automatically",
        )
        auto_resize: bool = Field(
            default=True,
            description="Whether to automatically resize content to fit",
        )

    def __init__(self, config: Optional[Dict] = None, **kwargs):
        """Initialize Content Insertion Tool with settings

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/content_insertion.yaml)
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

        # Initialize directories
        self._init_directories()

        # Initialize external tools
        self._init_external_tools()

        # Track insertions
        self._insertions: List[Any] = []

        # Content registry for cross-references
        self._content_registry: Dict[str, Any] = {}

    def _init_directories(self):
        """Initialize required directories"""
        os.makedirs(self.config.temp_dir, exist_ok=True)
        os.makedirs(self.config.assets_dir, exist_ok=True)

    def _init_external_tools(self):
        """Initialize external tools for content generation"""
        self.external_tools = {}

        # Try to initialize chart tool
        try:
            from aiecs.tools.task_tools.chart_tool import ChartTool

            self.external_tools["chart"] = ChartTool()
            self.logger.info("ChartTool initialized successfully")
        except ImportError:
            self.logger.warning("ChartTool not available")

        # Try to initialize pandas tool
        try:
            from aiecs.tools.task_tools.pandas_tool import PandasTool

            self.external_tools["pandas"] = PandasTool()
            self.logger.info("PandasTool initialized successfully")
        except ImportError:
            self.logger.warning("PandasTool not available")

        # Try to initialize image tool
        try:
            from aiecs.tools.task_tools.image_tool import ImageTool

            self.external_tools["image"] = ImageTool()
            self.logger.info("ImageTool initialized successfully")
        except ImportError:
            self.logger.warning("ImageTool not available")

    # Schema definitions
    class InsertChartSchema(BaseModel):
        """Schema for insert_chart operation"""

        document_path: str = Field(description="Path to target document")
        chart_data: Dict[str, Any] = Field(description="Data for chart generation")
        chart_type: ChartType = Field(description="Type of chart to create")
        position: Dict[str, Any] = Field(description="Position to insert chart")
        chart_config: Optional[Dict[str, Any]] = Field(default=None, description="Chart configuration")
        caption: Optional[str] = Field(default=None, description="Chart caption")
        reference_id: Optional[str] = Field(default=None, description="Reference ID for cross-referencing")

    class InsertTableSchema(BaseModel):
        """Schema for insert_table operation"""

        document_path: str = Field(description="Path to target document")
        table_data: Union[List[List[Any]], Dict[str, Any]] = Field(description="Table data")
        position: Dict[str, Any] = Field(description="Position to insert table")
        table_style: TableStyle = Field(default=TableStyle.DEFAULT, description="Table styling")
        headers: Optional[List[str]] = Field(default=None, description="Table headers")
        caption: Optional[str] = Field(default=None, description="Table caption")
        reference_id: Optional[str] = Field(default=None, description="Reference ID for cross-referencing")

    class InsertImageSchema(BaseModel):
        """Schema for insert_image operation"""

        document_path: str = Field(description="Path to target document")
        image_source: str = Field(description="Image source (path, URL, or base64)")
        position: Dict[str, Any] = Field(description="Position to insert image")
        image_config: Optional[Dict[str, Any]] = Field(default=None, description="Image configuration")
        alignment: ImageAlignment = Field(default=ImageAlignment.CENTER, description="Image alignment")
        caption: Optional[str] = Field(default=None, description="Image caption")
        alt_text: Optional[str] = Field(default=None, description="Alternative text")
        reference_id: Optional[str] = Field(default=None, description="Reference ID for cross-referencing")

    class InsertMediaSchema(BaseModel):
        """Schema for insert_media operation"""

        document_path: str = Field(description="Path to target document")
        media_source: str = Field(description="Media source (path or URL)")
        media_type: ContentType = Field(description="Type of media content")
        position: Dict[str, Any] = Field(description="Position to insert media")
        media_config: Optional[Dict[str, Any]] = Field(default=None, description="Media configuration")
        caption: Optional[str] = Field(default=None, description="Media caption")

    class InsertInteractiveSchema(BaseModel):
        """Schema for insert_interactive_element operation"""

        document_path: str = Field(description="Path to target document")
        element_type: ContentType = Field(description="Type of interactive element")
        element_config: Dict[str, Any] = Field(description="Element configuration")
        position: Dict[str, Any] = Field(description="Position to insert element")

    def insert_chart(
        self,
        document_path: str,
        chart_data: Dict[str, Any],
        chart_type: ChartType,
        position: Dict[str, Any],
        chart_config: Optional[Dict[str, Any]] = None,
        caption: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Insert chart into document

        Args:
            document_path: Path to target document
            chart_data: Data for chart generation
            chart_type: Type of chart to create
            position: Position to insert chart
            chart_config: Chart configuration options
            caption: Chart caption
            reference_id: Reference ID for cross-referencing

        Returns:
            Dict containing chart insertion results
        """
        try:
            start_time = datetime.now()
            insertion_id = str(uuid.uuid4())

            self.logger.info(f"Inserting {chart_type} chart {insertion_id} into: {document_path}")

            # Check if chart tool is available
            if "chart" not in self.external_tools:
                raise ChartInsertionError("ChartTool not available")

            # Generate chart
            chart_result = self._generate_chart(chart_data, chart_type, chart_config)

            # Process chart for document insertion
            processed_chart = self._process_chart_for_document(chart_result, document_path, chart_config)

            # Generate chart markup
            chart_markup = self._generate_chart_markup(processed_chart, caption, reference_id, chart_config)

            # Insert chart into document
            self._insert_content_at_position(document_path, chart_markup, position)

            # Register for cross-references
            if reference_id:
                self._register_content_reference(
                    reference_id,
                    "chart",
                    {
                        "type": chart_type,
                        "caption": caption,
                        "file_path": processed_chart.get("file_path"),
                    },
                )

            # Track insertion
            insertion_info = {
                "insertion_id": insertion_id,
                "content_type": "chart",
                "chart_type": chart_type,
                "document_path": document_path,
                "position": position,
                "chart_data": chart_data,
                "chart_config": chart_config,
                "caption": caption,
                "reference_id": reference_id,
                "chart_result": chart_result,
                "processed_chart": processed_chart,
                "insertion_metadata": {
                    "inserted_at": start_time.isoformat(),
                    "duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            self._insertions.append(insertion_info)

            self.logger.info(f"Chart {insertion_id} inserted successfully")
            return insertion_info

        except Exception as e:
            raise ChartInsertionError(f"Failed to insert chart: {str(e)}")

    def insert_table(
        self,
        document_path: str,
        table_data: Union[List[List[Any]], Dict[str, Any]],
        position: Dict[str, Any],
        table_style: TableStyle = TableStyle.DEFAULT,
        headers: Optional[List[str]] = None,
        caption: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Insert table into document

        Args:
            document_path: Path to target document
            table_data: Table data (list of lists or dict)
            position: Position to insert table
            table_style: Table styling options
            headers: Table headers
            caption: Table caption
            reference_id: Reference ID for cross-referencing

        Returns:
            Dict containing table insertion results
        """
        try:
            start_time = datetime.now()
            insertion_id = str(uuid.uuid4())

            self.logger.info(f"Inserting table {insertion_id} into: {document_path}")

            # Process table data
            processed_table = self._process_table_data(table_data, headers)

            # Generate table markup
            table_markup = self._generate_table_markup(processed_table, table_style, caption, reference_id)

            # Insert table into document
            self._insert_content_at_position(document_path, table_markup, position)

            # Register for cross-references
            if reference_id:
                self._register_content_reference(
                    reference_id,
                    "table",
                    {
                        "rows": len(processed_table.get("data", [])),
                        "columns": len(processed_table.get("headers", [])),
                        "caption": caption,
                        "style": table_style,
                    },
                )

            # Track insertion
            insertion_info = {
                "insertion_id": insertion_id,
                "content_type": "table",
                "document_path": document_path,
                "position": position,
                "table_data": table_data,
                "table_style": table_style,
                "headers": headers,
                "caption": caption,
                "reference_id": reference_id,
                "processed_table": processed_table,
                "insertion_metadata": {
                    "inserted_at": start_time.isoformat(),
                    "duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            self._insertions.append(insertion_info)

            self.logger.info(f"Table {insertion_id} inserted successfully")
            return insertion_info

        except Exception as e:
            raise TableInsertionError(f"Failed to insert table: {str(e)}")

    def insert_image(
        self,
        document_path: str,
        image_source: str,
        position: Dict[str, Any],
        image_config: Optional[Dict[str, Any]] = None,
        alignment: ImageAlignment = ImageAlignment.CENTER,
        caption: Optional[str] = None,
        alt_text: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Insert image into document

        Args:
            document_path: Path to target document
            image_source: Image source (path, URL, or base64)
            position: Position to insert image
            image_config: Image configuration (size, format, etc.)
            alignment: Image alignment
            caption: Image caption
            alt_text: Alternative text for accessibility
            reference_id: Reference ID for cross-referencing

        Returns:
            Dict containing image insertion results
        """
        try:
            start_time = datetime.now()
            insertion_id = str(uuid.uuid4())

            self.logger.info(f"Inserting image {insertion_id} into: {document_path}")

            # Process image
            processed_image = self._process_image_for_document(image_source, image_config, document_path)

            # Generate image markup
            image_markup = self._generate_image_markup(processed_image, alignment, caption, alt_text, reference_id)

            # Insert image into document
            self._insert_content_at_position(document_path, image_markup, position)

            # Register for cross-references
            if reference_id:
                self._register_content_reference(
                    reference_id,
                    "image",
                    {
                        "caption": caption,
                        "alt_text": alt_text,
                        "file_path": processed_image.get("file_path"),
                        "dimensions": processed_image.get("dimensions"),
                    },
                )

            # Track insertion
            insertion_info = {
                "insertion_id": insertion_id,
                "content_type": "image",
                "document_path": document_path,
                "position": position,
                "image_source": image_source,
                "image_config": image_config,
                "alignment": alignment,
                "caption": caption,
                "alt_text": alt_text,
                "reference_id": reference_id,
                "processed_image": processed_image,
                "insertion_metadata": {
                    "inserted_at": start_time.isoformat(),
                    "duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            self._insertions.append(insertion_info)

            self.logger.info(f"Image {insertion_id} inserted successfully")
            return insertion_info

        except Exception as e:
            raise ImageInsertionError(f"Failed to insert image: {str(e)}")

    def insert_media(
        self,
        document_path: str,
        media_source: str,
        media_type: ContentType,
        position: Dict[str, Any],
        media_config: Optional[Dict[str, Any]] = None,
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Insert media content (video, audio, etc.) into document

        Args:
            document_path: Path to target document
            media_source: Media source (path or URL)
            media_type: Type of media content
            position: Position to insert media
            media_config: Media configuration
            caption: Media caption

        Returns:
            Dict containing media insertion results
        """
        try:
            start_time = datetime.now()
            insertion_id = str(uuid.uuid4())

            self.logger.info(f"Inserting {media_type} media {insertion_id} into: {document_path}")

            # Process media
            processed_media = self._process_media_for_document(media_source, media_type, media_config)

            # Generate media markup
            media_markup = self._generate_media_markup(processed_media, media_type, caption, media_config)

            # Insert media into document
            self._insert_content_at_position(document_path, media_markup, position)

            # Track insertion
            insertion_info = {
                "insertion_id": insertion_id,
                "content_type": "media",
                "media_type": media_type,
                "document_path": document_path,
                "position": position,
                "media_source": media_source,
                "media_config": media_config,
                "caption": caption,
                "processed_media": processed_media,
                "insertion_metadata": {
                    "inserted_at": start_time.isoformat(),
                    "duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            self._insertions.append(insertion_info)

            self.logger.info(f"Media {insertion_id} inserted successfully")
            return insertion_info

        except Exception as e:
            raise ContentInsertionError(f"Failed to insert media: {str(e)}")

    def insert_interactive_element(
        self,
        document_path: str,
        element_type: ContentType,
        element_config: Dict[str, Any],
        position: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Insert interactive element (form, button, etc.) into document

        Args:
            document_path: Path to target document
            element_type: Type of interactive element
            element_config: Element configuration
            position: Position to insert element

        Returns:
            Dict containing interactive element insertion results
        """
        try:
            start_time = datetime.now()
            insertion_id = str(uuid.uuid4())

            self.logger.info(f"Inserting {element_type} element {insertion_id} into: {document_path}")

            # Generate interactive element markup
            element_markup = self._generate_interactive_element_markup(element_type, element_config)

            # Insert element into document
            self._insert_content_at_position(document_path, element_markup, position)

            # Track insertion
            insertion_info = {
                "insertion_id": insertion_id,
                "content_type": "interactive",
                "element_type": element_type,
                "document_path": document_path,
                "position": position,
                "element_config": element_config,
                "insertion_metadata": {
                    "inserted_at": start_time.isoformat(),
                    "duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            self._insertions.append(insertion_info)

            self.logger.info(f"Interactive element {insertion_id} inserted successfully")
            return insertion_info

        except Exception as e:
            raise ContentInsertionError(f"Failed to insert interactive element: {str(e)}")

    def insert_citation(
        self,
        document_path: str,
        citation_data: Dict[str, Any],
        position: Dict[str, Any],
        citation_style: str = "apa",
    ) -> Dict[str, Any]:
        """
        Insert citation into document

        Args:
            document_path: Path to target document
            citation_data: Citation information
            position: Position to insert citation
            citation_style: Citation style (apa, mla, chicago, etc.)

        Returns:
            Dict containing citation insertion results
        """
        try:
            start_time = datetime.now()
            insertion_id = str(uuid.uuid4())

            self.logger.info(f"Inserting citation {insertion_id} into: {document_path}")

            # Generate citation markup
            citation_markup = self._generate_citation_markup(citation_data, citation_style)

            # Insert citation into document
            self._insert_content_at_position(document_path, citation_markup, position)

            # Track insertion
            insertion_info = {
                "insertion_id": insertion_id,
                "content_type": "citation",
                "document_path": document_path,
                "position": position,
                "citation_data": citation_data,
                "citation_style": citation_style,
                "insertion_metadata": {
                    "inserted_at": start_time.isoformat(),
                    "duration": (datetime.now() - start_time).total_seconds(),
                },
            }

            self._insertions.append(insertion_info)

            self.logger.info(f"Citation {insertion_id} inserted successfully")
            return insertion_info

        except Exception as e:
            raise ContentInsertionError(f"Failed to insert citation: {str(e)}")

    def batch_insert_content(self, document_path: str, content_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Insert multiple content items in batch

        Args:
            document_path: Path to target document
            content_items: List of content items to insert

        Returns:
            Dict containing batch insertion results
        """
        try:
            start_time = datetime.now()
            batch_id = str(uuid.uuid4())

            self.logger.info(f"Starting batch insertion {batch_id} for: {document_path}")

            results: Dict[str, Any] = {
                "batch_id": batch_id,
                "document_path": document_path,
                "total_items": len(content_items),
                "successful_insertions": 0,
                "failed_insertions": 0,
                "insertion_results": [],
                "errors": [],
            }

            for i, item in enumerate(content_items):
                try:
                    content_type = item.get("content_type")

                    if content_type == "chart":
                        result = self.insert_chart(**item)
                    elif content_type == "table":
                        result = self.insert_table(**item)
                    elif content_type == "image":
                        result = self.insert_image(**item)
                    elif content_type == "media":
                        result = self.insert_media(**item)
                    elif content_type == "citation":
                        result = self.insert_citation(**item)
                    else:
                        raise ContentInsertionError(f"Unsupported content type: {content_type}")

                    results["insertion_results"].append(result)
                    successful = results.get("successful_insertions", 0)
                    if isinstance(successful, (int, float)):
                        results["successful_insertions"] = successful + 1

                except Exception as e:
                    error_info = {
                        "item_index": i,
                        "item": item,
                        "error": str(e),
                    }
                    results["errors"].append(error_info)
                    failed = results.get("failed_insertions", 0)
                    if isinstance(failed, (int, float)):
                        results["failed_insertions"] = failed + 1
                    self.logger.warning(f"Failed to insert item {i}: {e}")

            results["batch_metadata"] = {
                "started_at": start_time.isoformat(),
                "completed_at": datetime.now().isoformat(),
                "duration": (datetime.now() - start_time).total_seconds(),
            }

            self.logger.info(f"Batch insertion {batch_id} completed: {results['successful_insertions']}/{results['total_items']} successful")
            return results

        except Exception as e:
            raise ContentInsertionError(f"Batch insertion failed: {str(e)}")

    def get_content_references(self) -> Dict[str, Any]:
        """
        Get all registered content references

        Returns:
            Dict containing content references
        """
        return self._content_registry.copy()

    def get_insertion_history(self) -> List[Dict[str, Any]]:
        """
        Get insertion history

        Returns:
            List of insertion operations
        """
        return self._insertions.copy()

    # Helper methods for content generation
    def _generate_chart(
        self,
        chart_data: Dict[str, Any],
        chart_type: ChartType,
        config: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate chart using ChartTool"""
        try:
            chart_tool = self.external_tools["chart"]

            # Create temporary data file for ChartTool
            import tempfile
            import json

            temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            json.dump(chart_data, temp_file)
            temp_file.close()

            # Map chart types to visualization types
            type_mapping = {
                ChartType.BAR: "bar",
                ChartType.LINE: "line",
                ChartType.PIE: "pie",
                ChartType.SCATTER: "scatter",
                ChartType.HISTOGRAM: "histogram",
                ChartType.BOX: "box",
                ChartType.HEATMAP: "heatmap",
                ChartType.AREA: "area",
            }

            # Generate chart using visualize method
            result = chart_tool.visualize(
                file_path=temp_file.name,
                plot_type=type_mapping.get(chart_type, "bar"),
                title=config.get("title", "Chart") if config else "Chart",
                figsize=config.get("figsize", (10, 6)) if config else (10, 6),
            )

            # Clean up temp file
            os.unlink(temp_file.name)
            return result

        except Exception as e:
            raise ChartInsertionError(f"Failed to generate chart: {str(e)}")

    def _process_chart_for_document(
        self,
        chart_result: Dict[str, Any],
        document_path: str,
        config: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Process chart for document insertion"""
        try:
            # Get chart file path - ChartTool returns 'output_path'
            chart_file = chart_result.get("output_path") or chart_result.get("file_path")
            if not chart_file or not os.path.exists(chart_file):
                raise ChartInsertionError("Chart file not found")

            # Copy chart to assets directory
            chart_filename = f"chart_{uuid.uuid4().hex[:8]}.{self.config.default_image_format}"
            asset_path = os.path.join(self.config.assets_dir, chart_filename)

            import shutil

            shutil.copy2(chart_file, asset_path)

            # Optimize if needed
            if self.config.optimize_images and "image" in self.external_tools:
                self._optimize_image(asset_path)

            return {
                "file_path": asset_path,
                "filename": chart_filename,
                "relative_path": os.path.relpath(asset_path, os.path.dirname(document_path)),
                "chart_data": chart_result,
                "dimensions": self._get_image_dimensions(asset_path),
            }

        except Exception as e:
            raise ChartInsertionError(f"Failed to process chart: {str(e)}")

    def _process_table_data(
        self,
        table_data: Union[List[List[Any]], Dict[str, Any]],
        headers: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Process table data for insertion"""
        try:
            if isinstance(table_data, dict):
                # Convert dict to list format
                if headers is None:
                    headers = list(table_data.keys())
                data_rows = []
                max_len = max(len(v) if isinstance(v, list) else 1 for v in table_data.values())
                for i in range(max_len):
                    row = []
                    for key in headers:
                        value = table_data[key]
                        if isinstance(value, list):
                            row.append(value[i] if i < len(value) else "")
                        else:
                            row.append(value if i == 0 else "")
                    data_rows.append(row)
                data = data_rows
            else:
                data = table_data
                if headers is None and data:
                    headers = [f"Column {i+1}" for i in range(len(data[0]))]

            return {
                "headers": headers or [],
                "data": data,
                "rows": len(data),
                "columns": len(headers or []),
            }

        except Exception as e:
            raise TableInsertionError(f"Failed to process table data: {str(e)}")

    def _process_image_for_document(
        self,
        image_source: str,
        config: Optional[Dict[str, Any]],
        document_path: str,
    ) -> Dict[str, Any]:
        """Process image for document insertion"""
        try:
            # Determine image source type
            if image_source.startswith(("http://", "https://")):
                # Download from URL
                image_file = self._download_image(image_source)
            elif image_source.startswith("data:"):
                # Decode base64 image
                image_file = self._decode_base64_image(image_source)
            else:
                # Local file
                if not os.path.exists(image_source):
                    raise ImageInsertionError(f"Image file not found: {image_source}")
                image_file = image_source

            # Copy to assets directory
            image_filename = f"image_{uuid.uuid4().hex[:8]}.{self.config.default_image_format}"
            asset_path = os.path.join(self.config.assets_dir, image_filename)

            import shutil

            shutil.copy2(image_file, asset_path)

            # Process image (resize, optimize, etc.)
            if config:
                self._apply_image_processing(asset_path, config)

            return {
                "file_path": asset_path,
                "filename": image_filename,
                "relative_path": os.path.relpath(asset_path, os.path.dirname(document_path)),
                "original_source": image_source,
                "dimensions": self._get_image_dimensions(asset_path),
                "file_size": os.path.getsize(asset_path),
            }

        except Exception as e:
            raise ImageInsertionError(f"Failed to process image: {str(e)}")

    def _process_media_for_document(
        self,
        media_source: str,
        media_type: ContentType,
        config: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Process media for document insertion"""
        return {
            "source": media_source,
            "type": media_type,
            "config": config or {},
            "is_external": media_source.startswith(("http://", "https://")),
        }

    # Markup generation methods
    def _generate_chart_markup(
        self,
        chart_info: Dict[str, Any],
        caption: Optional[str],
        reference_id: Optional[str],
        config: Optional[Dict[str, Any]],
    ) -> str:
        """Generate markup for chart insertion"""
        file_format = self._detect_document_format_from_config(config)

        if file_format == "markdown":
            markup = f"![{caption or 'Chart'}]({chart_info['relative_path']})"
            if caption:
                markup += f"\n\n*{caption}*"
            if reference_id:
                markup = f"<div id='{reference_id}'>\n{markup}\n</div>"
        elif file_format == "html":
            markup = f"<img src='{chart_info['relative_path']}' alt='{caption or 'Chart'}'>"
            if caption:
                markup = f"<figure>\n{markup}\n<figcaption>{caption}</figcaption>\n</figure>"
            if reference_id:
                markup = f"<div id='{reference_id}'>\n{markup}\n</div>"
        else:
            markup = f"[Chart: {chart_info['filename']}]"
            if caption:
                markup += f"\nCaption: {caption}"

        return markup

    def _generate_table_markup(
        self,
        table_info: Dict[str, Any],
        style: TableStyle,
        caption: Optional[str],
        reference_id: Optional[str],
    ) -> str:
        """Generate markup for table insertion"""
        headers = table_info.get("headers", [])
        data = table_info.get("data", [])

        # Generate Markdown table (most compatible)
        markup_lines = []

        # Add caption
        if caption:
            markup_lines.append(f"**{caption}**\n")

        # Add headers
        if headers:
            markup_lines.append("| " + " | ".join(str(h) for h in headers) + " |")
            markup_lines.append("| " + " | ".join("---" for _ in headers) + " |")

        # Add data rows
        for row in data:
            markup_lines.append("| " + " | ".join(str(cell) for cell in row) + " |")

        markup = "\n".join(markup_lines)

        if reference_id:
            markup = f"<div id='{reference_id}'>\n\n{markup}\n\n</div>"

        return markup

    def _generate_image_markup(
        self,
        image_info: Dict[str, Any],
        alignment: ImageAlignment,
        caption: Optional[str],
        alt_text: Optional[str],
        reference_id: Optional[str],
    ) -> str:
        """Generate markup for image insertion"""
        alt = alt_text or caption or "Image"

        # Basic markdown image
        markup = f"![{alt}]({image_info['relative_path']})"

        # Add alignment if needed
        if alignment != ImageAlignment.INLINE:
            if alignment == ImageAlignment.CENTER:
                markup = f"<div align='center'>\n{markup}\n</div>"
            elif alignment == ImageAlignment.RIGHT:
                markup = f"<div align='right'>\n{markup}\n</div>"
            elif alignment == ImageAlignment.FLOAT_RIGHT:
                markup = f"<div style='float: right;'>\n{markup}\n</div>"
            elif alignment == ImageAlignment.FLOAT_LEFT:
                markup = f"<div style='float: left;'>\n{markup}\n</div>"

        # Add caption
        if caption:
            markup += f"\n\n*{caption}*"

        # Add reference ID
        if reference_id:
            markup = f"<div id='{reference_id}'>\n{markup}\n</div>"

        return markup

    def _generate_media_markup(
        self,
        media_info: Dict[str, Any],
        media_type: ContentType,
        caption: Optional[str],
        config: Optional[Dict[str, Any]],
    ) -> str:
        """Generate markup for media insertion"""
        source = media_info["source"]

        if media_type == ContentType.VIDEO:
            markup = f'<video controls>\n<source src="{source}">\nYour browser does not support the video tag.\n</video>'
        elif media_type == ContentType.AUDIO:
            markup = f'<audio controls>\n<source src="{source}">\nYour browser does not support the audio tag.\n</audio>'
        else:
            markup = f'<object data="{source}">Media content</object>'

        if caption:
            markup = f"<figure>\n{markup}\n<figcaption>{caption}</figcaption>\n</figure>"

        return markup

    def _generate_interactive_element_markup(self, element_type: ContentType, config: Dict[str, Any]) -> str:
        """Generate markup for interactive elements"""
        if element_type == ContentType.BUTTON:
            text = config.get("text", "Button")
            action = config.get("action", "#")
            return f'<button onclick="{action}">{text}</button>'
        elif element_type == ContentType.FORM:
            return self._generate_form_markup(config)
        elif element_type == ContentType.LINK:
            text = config.get("text", "Link")
            url = config.get("url", "#")
            return f'<a href="{url}">{text}</a>'
        else:
            return f"<!-- Interactive element: {element_type} -->"

    def _generate_form_markup(self, config: Dict[str, Any]) -> str:
        """Generate form markup"""
        fields = config.get("fields", [])
        action = config.get("action", "#")
        method = config.get("method", "POST")

        form_lines = [f'<form action="{action}" method="{method}">']

        for field in fields:
            field_type = field.get("type", "text")
            name = field.get("name", "")
            label = field.get("label", "")

            if label:
                form_lines.append(f'  <label for="{name}">{label}:</label>')
            form_lines.append(f'  <input type="{field_type}" name="{name}" id="{name}">')

        form_lines.append('  <input type="submit" value="Submit">')
        form_lines.append("</form>")

        return "\n".join(form_lines)

    def _generate_citation_markup(self, citation_data: Dict[str, Any], style: str) -> str:
        """Generate citation markup"""
        if style.lower() == "apa":
            return self._generate_apa_citation(citation_data)
        elif style.lower() == "mla":
            return self._generate_mla_citation(citation_data)
        else:
            return self._generate_basic_citation(citation_data)

    def _generate_apa_citation(self, data: Dict[str, Any]) -> str:
        """Generate APA style citation"""
        author = data.get("author", "Unknown Author")
        year = data.get("year", "n.d.")
        data.get("title", "Untitled")
        return f"({author}, {year})"

    def _generate_mla_citation(self, data: Dict[str, Any]) -> str:
        """Generate MLA style citation"""
        author = data.get("author", "Unknown Author")
        page = data.get("page", "")
        if page:
            return f"({author} {page})"
        return f"({author})"

    def _generate_basic_citation(self, data: Dict[str, Any]) -> str:
        """Generate basic citation"""
        author = data.get("author", "Unknown Author")
        year = data.get("year", "")
        if year:
            return f"[{author}, {year}]"
        return f"[{author}]"

    # Content insertion methods
    def _insert_content_at_position(self, document_path: str, content: str, position: Dict[str, Any]):
        """Insert content at specified position in document"""
        try:
            with open(document_path, "r", encoding="utf-8") as f:
                doc_content = f.read()

            if "line" in position:
                lines = doc_content.split("\n")
                line_num = position["line"]
                insertion_type = position.get("type", InsertionPosition.AFTER)

                if insertion_type == InsertionPosition.BEFORE:
                    lines.insert(line_num, content)
                elif insertion_type == InsertionPosition.AFTER:
                    lines.insert(line_num + 1, content)
                elif insertion_type == InsertionPosition.REPLACE:
                    lines[line_num] = content

                doc_content = "\n".join(lines)

            elif "offset" in position:
                offset = position["offset"]
                doc_content = doc_content[:offset] + content + doc_content[offset:]

            elif "marker" in position:
                marker = position["marker"]
                if marker in doc_content:
                    doc_content = doc_content.replace(marker, content, 1)
                else:
                    doc_content += "\n\n" + content

            else:
                # Append at end
                doc_content += "\n\n" + content

            with open(document_path, "w", encoding="utf-8") as f:
                f.write(doc_content)

        except Exception as e:
            raise ContentInsertionError(f"Failed to insert content: {str(e)}")

    def _register_content_reference(self, reference_id: str, content_type: str, metadata: Dict[str, Any]):
        """Register content for cross-referencing"""
        self._content_registry[reference_id] = {
            "type": content_type,
            "metadata": metadata,
            "registered_at": datetime.now().isoformat(),
        }

    # Utility methods
    def _detect_document_format_from_config(self, config: Optional[Dict[str, Any]]) -> str:
        """Detect document format from configuration"""
        if config and "document_format" in config:
            return config["document_format"]
        return "markdown"  # Default

    def _download_image(self, url: str) -> str:
        """Download image from URL"""
        import urllib.request

        filename = f"downloaded_{uuid.uuid4().hex[:8]}.{self.config.default_image_format}"
        filepath = os.path.join(self.config.temp_dir, filename)

        urllib.request.urlretrieve(url, filepath)
        return filepath

    def _decode_base64_image(self, data_url: str) -> str:
        """Decode base64 image data"""
        import base64

        # Extract format and data
        header, data = data_url.split(",", 1)
        format_info = header.split(";")[0].split("/")[-1]

        # Decode data
        image_data = base64.b64decode(data)

        filename = f"base64_{uuid.uuid4().hex[:8]}.{format_info}"
        filepath = os.path.join(self.config.temp_dir, filename)

        with open(filepath, "wb") as f:
            f.write(image_data)

        return filepath

    def _get_image_dimensions(self, image_path: str) -> Optional[Tuple[int, int]]:
        """Get image dimensions"""
        try:
            from PIL import Image

            with Image.open(image_path) as img:
                return img.size
        except ImportError:
            return None
        except Exception:
            return None

    def _optimize_image(self, image_path: str):
        """Optimize image for document inclusion"""
        if "image" in self.external_tools:
            try:
                image_tool = self.external_tools["image"]
                # Load image to get current info
                image_info = image_tool.load(image_path)
                # For now, just log the optimization - actual optimization
                # would require more complex logic
                self.logger.info(f"Image optimization requested for: {image_path}, size: {image_info.get('size')}")
            except Exception as e:
                self.logger.warning(f"Failed to optimize image: {e}")

    def _apply_image_processing(self, image_path: str, config: Dict[str, Any]):
        """Apply image processing based on configuration"""
        if "image" in self.external_tools:
            try:
                self.external_tools["image"]

                # Apply resize if specified
                if "resize" in config:
                    resize_params = config["resize"]
                    if isinstance(resize_params, dict) and "width" in resize_params and "height" in resize_params:
                        # Note: ImageTool.resize method would need to be called here
                        # For now, just log the resize request
                        self.logger.info(f"Resize requested: {resize_params}")

                # Apply filter if specified
                if "filter" in config:
                    filter_type = config["filter"]
                    # Note: ImageTool.filter method would need to be called
                    # here
                    self.logger.info(f"Filter requested: {filter_type}")

            except Exception as e:
                self.logger.warning(f"Failed to process image: {e}")
