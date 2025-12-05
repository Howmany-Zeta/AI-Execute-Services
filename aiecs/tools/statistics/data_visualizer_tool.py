"""
Data Visualizer Tool - Smart data visualization and chart generation

This tool provides intelligent visualization capabilities with:
- Auto chart type recommendation
- Multiple chart types support
- Interactive and static visualizations
- Export in multiple formats
"""

import os
import logging
import tempfile
from typing import Dict, Any, List, Optional, Union
from enum import Enum

import pandas as pd  # type: ignore[import-untyped]
import numpy as np
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool


class ChartType(str, Enum):
    """Supported chart types"""

    # Basic charts
    LINE = "line"
    BAR = "bar"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    BOX = "box"
    VIOLIN = "violin"

    # Advanced charts
    HEATMAP = "heatmap"
    CORRELATION_MATRIX = "correlation_matrix"
    PAIR_PLOT = "pair_plot"
    PARALLEL_COORDINATES = "parallel_coordinates"

    # Statistical charts
    DISTRIBUTION = "distribution"
    QQ_PLOT = "qq_plot"
    RESIDUAL_PLOT = "residual_plot"

    # Time series
    TIME_SERIES = "time_series"

    # Auto-detect
    AUTO = "auto"


class VisualizationStyle(str, Enum):
    """Visualization styles"""

    STATIC = "static"
    INTERACTIVE = "interactive"
    ANIMATED = "animated"


class DataVisualizerError(Exception):
    """Base exception for DataVisualizer errors"""


class VisualizationError(DataVisualizerError):
    """Raised when visualization fails"""


@register_tool("data_visualizer")
class DataVisualizerTool(BaseTool):
    """
    Intelligent data visualization tool that can:
    1. Auto-recommend appropriate chart types
    2. Generate interactive visualizations
    3. Create multi-dimensional plots
    4. Export in multiple formats

    Integrates with chart_tool for core visualization operations.
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the data visualizer tool
        
        Automatically reads from environment variables with DATA_VISUALIZER_ prefix.
        Example: DATA_VISUALIZER_DEFAULT_STYLE -> default_style
        """

        model_config = SettingsConfigDict(env_prefix="DATA_VISUALIZER_")

        default_style: str = Field(default="static", description="Default visualization style")
        default_output_dir: str = Field(
            default=tempfile.gettempdir(),
            description="Default directory for output files",
        )
        default_dpi: int = Field(default=100, description="Default DPI for image exports")
        default_figsize: List[int] = Field(
            default=[10, 6],
            description="Default figure size in inches (width, height)",
        )
        enable_auto_recommendation: bool = Field(
            default=True,
            description="Whether to enable automatic chart type recommendation",
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize DataVisualizerTool with settings.

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/data_visualizer.yaml)
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
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # Initialize external tools
        self._init_external_tools()

    def _init_external_tools(self):
        """Initialize external task tools"""
        self.external_tools = {}

        # Initialize ChartTool for visualization operations
        try:
            from aiecs.tools.task_tools.chart_tool import ChartTool

            self.external_tools["chart"] = ChartTool()
            self.logger.info("ChartTool initialized successfully")
        except ImportError:
            self.logger.warning("ChartTool not available")
            self.external_tools["chart"] = None

    # Schema definitions
    class VisualizeSchema(BaseModel):
        """Schema for visualize operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Data to visualize")
        chart_type: ChartType = Field(default=ChartType.AUTO, description="Type of chart")
        x: Optional[str] = Field(default=None, description="X-axis column")
        y: Optional[str] = Field(default=None, description="Y-axis column")
        hue: Optional[str] = Field(default=None, description="Hue/color column")
        style: VisualizationStyle = Field(
            default=VisualizationStyle.STATIC,
            description="Visualization style",
        )
        title: Optional[str] = Field(default=None, description="Chart title")
        output_path: Optional[str] = Field(default=None, description="Output file path")

    class AutoVisualizeDatasetSchema(BaseModel):
        """Schema for auto_visualize_dataset operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Dataset to visualize")
        max_charts: int = Field(default=10, description="Maximum number of charts to generate")
        focus_areas: Optional[List[str]] = Field(default=None, description="Areas to focus on")

    class RecommendChartTypeSchema(BaseModel):
        """Schema for recommend_chart_type operation"""

        data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(description="Data for recommendation")
        x: Optional[str] = Field(default=None, description="X column")
        y: Optional[str] = Field(default=None, description="Y column")

    def visualize(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        chart_type: ChartType = ChartType.AUTO,
        x: Optional[str] = None,
        y: Optional[str] = None,
        hue: Optional[str] = None,
        style: VisualizationStyle = VisualizationStyle.STATIC,
        title: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create visualization with auto chart type recommendation.

        Args:
            data: Data to visualize
            chart_type: Type of chart (auto-recommended if AUTO)
            x: X-axis column name
            y: Y-axis column name
            hue: Column for color encoding
            style: Visualization style
            title: Chart title
            output_path: Path to save the chart

        Returns:
            Dict containing:
                - chart_info: Information about generated chart
                - chart_type: Type of chart created
                - recommendation_reason: Reason for chart type choice
                - output_path: Path to saved chart (if saved)

        Raises:
            VisualizationError: If visualization fails
        """
        try:
            df = self._to_dataframe(data)

            # Auto-recommend chart type if needed
            if chart_type == ChartType.AUTO:
                chart_type, reason = self._recommend_chart_type(df, x, y)
                self.logger.info(f"Auto-recommended chart type: {chart_type.value} - {reason}")
            else:
                reason = "User specified"

            # Generate output path if not provided
            if output_path is None:
                output_path = os.path.join(
                    self.config.default_output_dir,
                    f"chart_{chart_type.value}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.png",
                )

            # Create visualization using chart_tool if available
            if self.external_tools.get("chart"):
                chart_result = self._create_chart_with_tool(df, chart_type, x, y, hue, title, output_path)
            else:
                chart_result = self._create_chart_matplotlib(df, chart_type, x, y, hue, title, output_path)

            return {
                "chart_info": chart_result,
                "chart_type": chart_type.value,
                "recommendation_reason": reason,
                "output_path": output_path,
                "style": style.value,
            }

        except Exception as e:
            self.logger.error(f"Error creating visualization: {e}")
            raise VisualizationError(f"Visualization failed: {e}")

    def auto_visualize_dataset(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        max_charts: int = 10,
        focus_areas: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Automatically generate a comprehensive visualization suite.

        Args:
            data: Dataset to visualize
            max_charts: Maximum number of charts to generate
            focus_areas: Specific areas to focus on (distributions, correlations, outliers)

        Returns:
            Dict containing information about all generated charts
        """
        try:
            df = self._to_dataframe(data)

            generated_charts = []
            chart_count = 0

            # Default focus areas
            if focus_areas is None:
                focus_areas = ["distributions", "correlations", "outliers"]

            # Generate distribution charts
            if "distributions" in focus_areas and chart_count < max_charts:
                numeric_cols = df.select_dtypes(include=[np.number]).columns[:5]
                for col in numeric_cols:
                    if chart_count >= max_charts:
                        break
                    chart_info = self.visualize(
                        df,
                        ChartType.HISTOGRAM,
                        x=col,
                        title=f"Distribution of {col}",
                    )
                    generated_charts.append(chart_info)
                    chart_count += 1

            # Generate correlation matrix
            if "correlations" in focus_areas and chart_count < max_charts:
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) >= 2:
                    chart_info = self.visualize(
                        df,
                        ChartType.CORRELATION_MATRIX,
                        title="Correlation Matrix",
                    )
                    generated_charts.append(chart_info)
                    chart_count += 1

            # Generate box plots for outlier detection
            if "outliers" in focus_areas and chart_count < max_charts:
                numeric_cols = df.select_dtypes(include=[np.number]).columns[:3]
                for col in numeric_cols:
                    if chart_count >= max_charts:
                        break
                    chart_info = self.visualize(df, ChartType.BOX, y=col, title=f"Box Plot of {col}")
                    generated_charts.append(chart_info)
                    chart_count += 1

            return {
                "generated_charts": generated_charts,
                "total_charts": len(generated_charts),
                "focus_areas": focus_areas,
            }

        except Exception as e:
            self.logger.error(f"Error in auto visualization: {e}")
            raise VisualizationError(f"Auto visualization failed: {e}")

    def recommend_chart_type(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        x: Optional[str] = None,
        y: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Recommend appropriate chart type based on data characteristics.

        Args:
            data: Data for analysis
            x: X column name
            y: Y column name

        Returns:
            Dict containing recommended chart type and reasoning
        """
        try:
            df = self._to_dataframe(data)
            chart_type, reason = self._recommend_chart_type(df, x, y)

            return {
                "recommended_chart": chart_type.value,
                "reason": reason,
                "confidence": "high",
            }

        except Exception as e:
            self.logger.error(f"Error recommending chart type: {e}")
            raise VisualizationError(f"Chart recommendation failed: {e}")

    # Internal helper methods

    def _to_dataframe(self, data: Union[Dict, List, pd.DataFrame]) -> pd.DataFrame:
        """Convert data to DataFrame"""
        if isinstance(data, pd.DataFrame):
            return data
        elif isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            return pd.DataFrame([data])
        else:
            raise VisualizationError(f"Unsupported data type: {type(data)}")

    def _recommend_chart_type(self, df: pd.DataFrame, x: Optional[str], y: Optional[str]) -> tuple:
        """Recommend chart type based on data characteristics"""
        # If no columns specified, recommend based on data structure
        if x is None and y is None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) >= 2:
                return (
                    ChartType.CORRELATION_MATRIX,
                    "Multiple numeric columns detected",
                )
            elif len(numeric_cols) == 1:
                return ChartType.HISTOGRAM, "Single numeric column detected"
            else:
                return ChartType.BAR, "Categorical data detected"

        # Determine column types
        x_is_numeric = x and df[x].dtype in ["int64", "float64"] if x in df.columns else False
        y_is_numeric = y and df[y].dtype in ["int64", "float64"] if y in df.columns else False

        # Both numeric: scatter or line
        if x_is_numeric and y_is_numeric:
            # Check if x looks like time series
            if x and (("date" in x.lower()) or ("time" in x.lower())):
                return ChartType.TIME_SERIES, "Time series data detected"
            return ChartType.SCATTER, "Two numeric variables"

        # One numeric, one categorical: bar or box
        if (x_is_numeric and not y_is_numeric) or (not x_is_numeric and y_is_numeric):
            return ChartType.BAR, "Mix of numeric and categorical"

        # Both categorical: bar
        if x and y and not x_is_numeric and not y_is_numeric:
            return ChartType.BAR, "Two categorical variables"

        # Single numeric: histogram
        if (x_is_numeric and y is None) or (y_is_numeric and x is None):
            return ChartType.HISTOGRAM, "Single numeric variable distribution"

        # Default
        return ChartType.BAR, "Default chart type"

    def _create_chart_with_tool(
        self,
        df: pd.DataFrame,
        chart_type: ChartType,
        x: Optional[str],
        y: Optional[str],
        hue: Optional[str],
        title: Optional[str],
        output_path: str,
    ) -> Dict[str, Any]:
        """Create chart using chart_tool"""
        chart_tool = self.external_tools["chart"]

        # Convert chart type to chart_tool format
        chart_config = {
            "data": df.to_dict("records"),
            "chart_type": chart_type.value,
            "x": x,
            "y": y,
            "title": title or f"{chart_type.value.title()} Chart",
            "output_path": output_path,
        }

        try:
            result = chart_tool.run("create_chart", **chart_config)
            return result
        except Exception as e:
            self.logger.warning(f"chart_tool failed, falling back to matplotlib: {e}")
            return self._create_chart_matplotlib(df, chart_type, x, y, hue, title, output_path)

    def _create_chart_matplotlib(
        self,
        df: pd.DataFrame,
        chart_type: ChartType,
        x: Optional[str],
        y: Optional[str],
        hue: Optional[str],
        title: Optional[str],
        output_path: str,
    ) -> Dict[str, Any]:
        """Create chart using matplotlib as fallback"""
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=self.config.default_figsize)

        if chart_type == ChartType.HISTOGRAM and x:
            ax.hist(df[x].dropna(), bins=30, edgecolor="black")
            ax.set_xlabel(x)
            ax.set_ylabel("Frequency")
        elif chart_type == ChartType.SCATTER and x and y:
            ax.scatter(df[x], df[y], alpha=0.6)
            ax.set_xlabel(x)
            ax.set_ylabel(y)
        elif chart_type == ChartType.BAR and x and y:
            df_grouped = df.groupby(x)[y].mean()
            df_grouped.plot(kind="bar", ax=ax)
            ax.set_xlabel(x)
            ax.set_ylabel(y)
        elif chart_type == ChartType.CORRELATION_MATRIX:
            numeric_df = df.select_dtypes(include=[np.number])
            if len(numeric_df.columns) >= 2:
                corr = numeric_df.corr()
                im = ax.imshow(corr, cmap="coolwarm", aspect="auto")
                ax.set_xticks(range(len(corr.columns)))
                ax.set_yticks(range(len(corr.columns)))
                ax.set_xticklabels(corr.columns, rotation=45, ha="right")
                ax.set_yticklabels(corr.columns)
                plt.colorbar(im, ax=ax)
        elif chart_type == ChartType.BOX and y:
            df.boxplot(column=y, ax=ax)
        else:
            # Default: simple line plot
            if x and y:
                ax.plot(df[x], df[y])
            elif x:
                ax.plot(df[x])

        if title:
            ax.set_title(title)

        plt.tight_layout()
        plt.savefig(output_path, dpi=self.config.default_dpi, bbox_inches="tight")
        plt.close()

        return {
            "status": "success",
            "output_path": output_path,
            "chart_type": chart_type.value,
        }
