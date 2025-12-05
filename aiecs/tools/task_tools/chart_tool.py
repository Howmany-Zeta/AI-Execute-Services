import os
import json
import csv
import tempfile
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from enum import Enum

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import matplotlib.pyplot as plt
import seaborn as sns  # type: ignore[import-untyped]

from aiecs.tools import register_tool
from aiecs.tools.base_tool import BaseTool
from aiecs.tools.tool_executor import measure_execution_time

# Enums for configuration options


class ExportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    HTML = "html"
    EXCEL = "excel"
    MARKDOWN = "markdown"


class VisualizationType(str, Enum):
    HISTOGRAM = "histogram"
    BOXPLOT = "boxplot"
    SCATTER = "scatter"
    BAR = "bar"
    LINE = "line"
    HEATMAP = "heatmap"
    PAIR = "pair"


@register_tool("chart")
class ChartTool(BaseTool):
    """Chart and visualization tool: creates charts and exports data in various formats."""

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the chart tool
        
        Automatically reads from environment variables with CHART_TOOL_ prefix.
        Example: CHART_TOOL_EXPORT_DIR -> export_dir
        """

        model_config = SettingsConfigDict(env_prefix="CHART_TOOL_")

        export_dir: str = Field(
            default=os.path.join(tempfile.gettempdir(), "chart_exports"),
            description="Directory to export files to",
        )
        plot_dpi: int = Field(default=100, description="DPI for plot exports")
        plot_figsize: Tuple[int, int] = Field(
            default=(10, 6),
            description="Default figure size (width, height) in inches",
        )
        allowed_extensions: List[str] = Field(
            default=[
                ".csv",
                ".xlsx",
                ".xls",
                ".json",
                ".parquet",
                ".feather",
                ".sav",
                ".sas7bdat",
                ".por",
            ],
            description="Allowed file extensions",
        )

    # Input schemas for operations
    class ReadDataSchema(BaseModel):
        """Schema for reading data files"""

        file_path: str = Field(description="Path to the data file")
        nrows: Optional[int] = Field(default=None, description="Number of rows to read")
        sheet_name: Optional[Union[str, int]] = Field(default=0, description="Sheet name or index for Excel files")
        export_format: Optional[ExportFormat] = Field(default=None, description="Format to export results in")
        export_path: Optional[str] = Field(default=None, description="Path to export results to")

        @field_validator("file_path")
        @classmethod
        def validate_file_path(cls, v):
            if not os.path.isfile(v):
                raise ValueError(f"File not found: {v}")
            return v

        @field_validator("export_path")
        @classmethod
        def validate_export_path(cls, v, info):
            if v and "export_format" not in info.data:
                raise ValueError("export_format must be specified when export_path is provided")
            return v

    class VisualizationSchema(BaseModel):
        """Schema for data visualization"""

        file_path: str = Field(description="Path to the data file")
        plot_type: VisualizationType = Field(description="Type of visualization to create")
        x: Optional[str] = Field(default=None, description="Column to use for x-axis")
        y: Optional[str] = Field(default=None, description="Column to use for y-axis")
        hue: Optional[str] = Field(default=None, description="Column to use for color encoding")
        variables: Optional[List[str]] = Field(
            default=None,
            description="List of variables to include in the visualization",
        )
        title: Optional[str] = Field(default=None, description="Title for the visualization")
        figsize: Optional[Tuple[int, int]] = Field(default=None, description="Figure size (width, height) in inches")
        output_path: Optional[str] = Field(default=None, description="Path to save the visualization")
        dpi: Optional[int] = Field(default=None, description="DPI for the visualization")
        export_format: Optional[ExportFormat] = Field(default=None, description="Format to export results in")
        export_path: Optional[str] = Field(default=None, description="Path to export results to")

        @field_validator("file_path")
        @classmethod
        def validate_file_path(cls, v):
            if not os.path.isfile(v):
                raise ValueError(f"File not found: {v}")
            return v

        @field_validator("export_path")
        @classmethod
        def validate_export_path(cls, v, info):
            if v and "export_format" not in info.data:
                raise ValueError("export_format must be specified when export_path is provided")
            return v

    class ExportDataSchema(BaseModel):
        """Schema for exporting data"""

        file_path: str = Field(description="Path to the data file")
        variables: Optional[List[str]] = Field(
            default=None,
            description="List of variables to include in the export",
        )
        format: ExportFormat = Field(description="Format to export data in")
        export_path: Optional[str] = Field(default=None, description="Path to save the exported data")
        export_format: Optional[ExportFormat] = Field(default=None, description="Format to export results in")

        @field_validator("file_path")
        @classmethod
        def validate_file_path(cls, v):
            if not os.path.isfile(v):
                raise ValueError(f"File not found: {v}")
            return v

        @field_validator("export_path")
        @classmethod
        def validate_export_path(cls, v, info):
            if v and "export_format" not in info.data:
                raise ValueError("export_format must be specified when export_path is provided")
            return v

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize the chart tool

        Args:
            config: Optional configuration for the tool
            **kwargs: Additional arguments passed to BaseTool (e.g., tool_name)

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/chart.yaml)
        3. Environment variables (via dotenv from .env files)
        4. Tool defaults (lowest priority)
        """
        super().__init__(config, **kwargs)

        # Configuration is automatically loaded by BaseTool into self._config_obj
        # Access config via self._config_obj (BaseSettings instance)
        self.config = self._config_obj if self._config_obj else self.Config()

        # Create export directory if it doesn't exist
        os.makedirs(self.config.export_dir, exist_ok=True)

        # Set up logger
        self.logger = logging.getLogger(__name__)

        # Set default matplotlib style
        plt.style.use("seaborn-v0_8-whitegrid")

    def _load_data(
        self,
        file_path: str,
        nrows: Optional[int] = None,
        sheet_name: Optional[Union[str, int]] = 0,
    ) -> pd.DataFrame:
        """
        Load data from various file formats into a pandas DataFrame

        Args:
            file_path: Path to the data file
            nrows: Number of rows to read
            sheet_name: Sheet name or index for Excel files

        Returns:
            Loaded DataFrame
        """
        # Determine file type and read accordingly
        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == ".sav":
                import pyreadstat  # type: ignore[import-untyped]

                df, meta = pyreadstat.read_sav(file_path)
                return df
            elif ext == ".sas7bdat":
                import pyreadstat  # type: ignore[import-untyped]

                df, meta = pyreadstat.read_sas7bdat(file_path)
                return df
            elif ext == ".por":
                import pyreadstat  # type: ignore[import-untyped]

                df, meta = pyreadstat.read_por(file_path)
                return df
            elif ext == ".csv":
                return pd.read_csv(file_path, nrows=nrows)
            elif ext in [".xlsx", ".xls"]:
                return pd.read_excel(file_path, sheet_name=sheet_name, nrows=nrows)
            elif ext == ".json":
                return pd.read_json(file_path)
            elif ext == ".parquet":
                return pd.read_parquet(file_path)
            elif ext == ".feather":
                return pd.read_feather(file_path)
            else:
                raise ValueError(f"Unsupported file format: {ext}")
        except Exception as e:
            raise ValueError(f"Error reading file {file_path}: {str(e)}")

    def _export_result(self, result: Dict[str, Any], path: str, format: ExportFormat) -> str:
        """
        Export results to the specified format

        Args:
            result: Result to export
            path: Path to save the exported result
            format: Format to export in
        """
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

        try:
            if format == ExportFormat.JSON:
                # Convert numpy types to Python native types
                def json_serialize(obj):
                    if isinstance(obj, (np.integer, np.int64)):
                        return int(obj)
                    elif isinstance(obj, (np.floating, np.float64)):
                        return float(obj)
                    elif isinstance(obj, np.ndarray):
                        return obj.tolist()
                    elif isinstance(obj, pd.DataFrame):
                        return obj.to_dict(orient="records")
                    return str(obj)

                with open(path, "w") as f:
                    json.dump(result, f, default=json_serialize, indent=2)

            elif format == ExportFormat.CSV:
                # Find the first dict or DataFrame in the result
                data_to_export = None
                for key, value in result.items():
                    if isinstance(value, dict) and value:
                        data_to_export = pd.DataFrame(value)
                        break
                    elif isinstance(value, pd.DataFrame):
                        data_to_export = value
                        break

                if data_to_export is not None:
                    data_to_export.to_csv(path, index=False)
                else:
                    # Fallback: convert the entire result to a flat structure
                    flat_data: Dict[str, Any] = {}
                    for k, v in result.items():
                        if not isinstance(v, (dict, list, pd.DataFrame)):
                            flat_data[k] = v

                    with open(path, "w", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow(flat_data.keys())
                        writer.writerow(flat_data.values())

            elif format == ExportFormat.HTML:
                # Convert to HTML table
                html_content = "<html><body><h1>Chart Results</h1>"
                for key, value in result.items():
                    html_content += f"<h2>{key}</h2>"
                    if isinstance(value, pd.DataFrame):
                        html_content += value.to_html()
                    elif isinstance(value, dict):
                        html_content += "<table border='1'><tr><th>Parameter</th><th>Value</th></tr>"
                        for k, v in value.items():
                            html_content += f"<tr><td>{k}</td><td>{v}</td></tr>"
                        html_content += "</table>"
                    else:
                        html_content += f"<p>{value}</p>"
                html_content += "</body></html>"

                with open(path, "w") as f:
                    f.write(html_content)

            elif format == ExportFormat.EXCEL:
                with pd.ExcelWriter(path) as writer:
                    for key, value in result.items():
                        if isinstance(value, pd.DataFrame):
                            # Excel sheet names limited to 31 chars
                            value.to_excel(writer, sheet_name=key[:31])
                        elif isinstance(value, dict):
                            pd.DataFrame(value, index=[0]).to_excel(writer, sheet_name=key[:31])
                        else:
                            pd.DataFrame({key: [value]}).to_excel(writer, sheet_name="Summary")

            elif format == ExportFormat.MARKDOWN:
                with open(path, "w") as f:
                    f.write("# Chart Results\n\n")
                    for key, value in result.items():
                        f.write(f"## {key}\n\n")
                        if isinstance(value, pd.DataFrame):
                            f.write(value.to_markdown())
                        elif isinstance(value, dict):
                            f.write("| Parameter | Value |\n|-----------|-------|\n")
                            for k, v in value.items():
                                f.write(f"| {k} | {v} |\n")
                        else:
                            f.write(f"{value}\n\n")

            return path
        except Exception as e:
            raise ValueError(f"Error exporting to {format}: {str(e)}")

    def _create_visualization(
        self,
        df: pd.DataFrame,
        plot_type: VisualizationType,
        x: Optional[str] = None,
        y: Optional[str] = None,
        hue: Optional[str] = None,
        variables: Optional[List[str]] = None,
        title: Optional[str] = None,
        figsize: Optional[Tuple[int, int]] = None,
        output_path: Optional[str] = None,
        dpi: Optional[int] = None,
    ) -> str:
        """
        Create a visualization based on the parameters and return the path to the saved image

        Args:
            df: DataFrame to visualize
            plot_type: Type of visualization to create
            x: Column to use for x-axis
            y: Column to use for y-axis
            hue: Column to use for color encoding
            variables: List of variables to include in the visualization
            title: Title for the visualization
            figsize: Figure size (width, height) in inches
            output_path: Path to save the visualization
            dpi: DPI for the visualization

        Returns:
            Path to the saved visualization
        """
        if not output_path:
            output_path = os.path.join(self.config.export_dir, f"plot_{os.urandom(4).hex()}.png")
        elif not os.path.isabs(output_path):
            output_path = os.path.join(self.config.export_dir, output_path)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        try:
            figsize = figsize or self.config.plot_figsize
            dpi = dpi or self.config.plot_dpi

            plt.figure(figsize=figsize)

            if plot_type == VisualizationType.HISTOGRAM:
                if variables:
                    for var in variables:
                        sns.histplot(data=df, x=var, kde=True, label=var)
                    plt.legend()
                else:
                    sns.histplot(data=df, x=x, hue=hue)

            elif plot_type == VisualizationType.BOXPLOT:
                sns.boxplot(data=df, x=x, y=y, hue=hue)

            elif plot_type == VisualizationType.SCATTER:
                sns.scatterplot(data=df, x=x, y=y, hue=hue)

            elif plot_type == VisualizationType.BAR:
                sns.barplot(data=df, x=x, y=y, hue=hue)

            elif plot_type == VisualizationType.LINE:
                sns.lineplot(data=df, x=x, y=y, hue=hue)

            elif plot_type == VisualizationType.HEATMAP:
                if variables:
                    corr = df[variables].corr()
                else:
                    corr = df.corr()
                sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f")

            elif plot_type == VisualizationType.PAIR:
                if variables:
                    plot_vars = variables + [hue] if hue else variables
                    sns.pairplot(df[plot_vars], hue=hue)
                else:
                    sns.pairplot(df, hue=hue)

            if title:
                plt.title(title)

            plt.tight_layout()
            plt.savefig(output_path, dpi=dpi)
            plt.close()

            return output_path
        except Exception as e:
            raise ValueError(f"Error creating visualization: {str(e)}")

    def _validate_variables(self, df: pd.DataFrame, variables: List[str]) -> None:
        """
        Validate that variables exist in the DataFrame

        Args:
            df: DataFrame to check
            variables: List of variables to validate

        Raises:
            ValueError: If any variables are not found in the DataFrame
        """
        if not variables:
            return

        available_columns = set(df.columns)
        missing = [col for col in variables if col not in available_columns]
        if missing:
            raise ValueError(f"Variables not found in dataset: {', '.join(missing)}. Available columns: {list(available_columns)}")

    def _to_json_serializable(self, result: Union[pd.DataFrame, pd.Series, Dict]) -> Union[List[Dict], Dict]:
        """
        Convert result to JSON serializable format

        Args:
            result: Result to convert

        Returns:
            JSON serializable result
        """
        if isinstance(result, pd.DataFrame):
            # Handle datetime columns
            for col in result.select_dtypes(include=["datetime64"]).columns:
                result[col] = result[col].dt.strftime("%Y-%m-%d %H:%M:%S")
            return result.to_dict(orient="records")
        elif isinstance(result, pd.Series):
            if pd.api.types.is_datetime64_any_dtype(result):
                result = result.dt.strftime("%Y-%m-%d %H:%M:%S")
            return result.to_dict()
        elif isinstance(result, dict):
            # Handle numpy types and datetime objects
            def convert_value(v):
                if isinstance(v, (np.floating, np.integer)):
                    return float(v)
                elif isinstance(v, np.bool_):
                    return bool(v)
                elif isinstance(v, (pd.Timestamp, np.datetime64)):
                    return str(v)
                elif isinstance(v, np.ndarray):
                    return v.tolist()
                elif pd.isna(v):
                    return None
                return v

            return {k: convert_value(v) for k, v in result.items()}
        return result

    @measure_execution_time
    def read_data(
        self,
        file_path: str,
        nrows: Optional[int] = None,
        sheet_name: Optional[Union[str, int]] = 0,
        export_format: Optional[ExportFormat] = None,
        export_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Read data from various file formats

        Args:
            file_path: Path to the data file
            nrows: Number of rows to read
            sheet_name: Sheet name or index for Excel files
            export_format: Format to export results in
            export_path: Path to export results to

        Returns:
            Dictionary with data summary
        """
        # Validate file path
        if not os.path.isfile(file_path):
            raise ValueError(f"File not found: {file_path}")

        # Check file extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.config.allowed_extensions:
            raise ValueError(f"Extension '{ext}' not allowed. Supported formats: {', '.join(self.config.allowed_extensions)}")

        # Load data
        df = self._load_data(file_path, nrows, sheet_name)

        # Create result
        result = {
            "variables": df.columns.tolist(),
            "observations": len(df),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            # MB
            "memory_usage": df.memory_usage(deep=True).sum() / (1024 * 1024),
            "preview": df.head(5).to_dict(orient="records"),
        }

        # Handle export if requested
        if export_format and export_path:
            if not os.path.isabs(export_path):
                export_path = os.path.join(self.config.export_dir, export_path)

            self._export_result(result, export_path, export_format)
            result["exported_to"] = export_path

        return result

    @measure_execution_time
    def visualize(
        self,
        file_path: str,
        plot_type: VisualizationType,
        x: Optional[str] = None,
        y: Optional[str] = None,
        hue: Optional[str] = None,
        variables: Optional[List[str]] = None,
        title: Optional[str] = None,
        figsize: Optional[Tuple[int, int]] = None,
        output_path: Optional[str] = None,
        dpi: Optional[int] = None,
        export_format: Optional[ExportFormat] = None,
        export_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create data visualizations

        Args:
            file_path: Path to the data file
            plot_type: Type of visualization to create
            x: Column to use for x-axis
            y: Column to use for y-axis
            hue: Column to use for color encoding
            variables: List of variables to include in the visualization
            title: Title for the visualization
            figsize: Figure size (width, height) in inches
            output_path: Path to save the visualization
            dpi: DPI for the visualization
            export_format: Format to export results in
            export_path: Path to export results to

        Returns:
            Dictionary with visualization details
        """
        # Validate file path
        if not os.path.isfile(file_path):
            raise ValueError(f"File not found: {file_path}")

        # Check file extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.config.allowed_extensions:
            raise ValueError(f"Extension '{ext}' not allowed. Supported formats: {', '.join(self.config.allowed_extensions)}")

        # Load data
        df = self._load_data(file_path)

        # Validate variables
        vars_to_check = []
        if variables:
            vars_to_check.extend(variables)
        if x:
            vars_to_check.append(x)
        if y:
            vars_to_check.append(y)
        if hue:
            vars_to_check.append(hue)

        self._validate_variables(df, vars_to_check)

        # Create visualization
        output_path = self._create_visualization(
            df,
            plot_type,
            x,
            y,
            hue,
            variables,
            title,
            figsize,
            output_path,
            dpi,
        )

        # Create result - filter out None values from variables
        var_list = variables or [v for v in [x, y, hue] if v is not None]
        result = {
            "plot_type": plot_type,
            "output_path": output_path,
            "variables": var_list,
            "title": title or f"{plot_type.capitalize()} Plot",
        }

        # Handle export if requested
        if export_format and export_path:
            if not os.path.isabs(export_path):
                export_path = os.path.join(self.config.export_dir, export_path)

            self._export_result(result, export_path, export_format)
            result["exported_to"] = export_path

        return result

    @measure_execution_time
    def export_data(
        self,
        file_path: str,
        format: ExportFormat,
        variables: Optional[List[str]] = None,
        export_path: Optional[str] = None,
        export_format: Optional[ExportFormat] = None,
    ) -> Dict[str, Any]:
        """
        Export data to various formats

        Args:
            file_path: Path to the data file
            format: Format to export data in
            variables: List of variables to include in the export
            export_path: Path to save the exported data
            export_format: Format to export results in

        Returns:
            Dictionary with export details
        """
        # Validate file path
        if not os.path.isfile(file_path):
            raise ValueError(f"File not found: {file_path}")

        # Check file extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.config.allowed_extensions:
            raise ValueError(f"Extension '{ext}' not allowed. Supported formats: {', '.join(self.config.allowed_extensions)}")

        # Load data
        df = self._load_data(file_path)

        # Validate variables
        if variables:
            self._validate_variables(df, variables)
            df = df[variables]

        # Determine export path
        if not export_path:
            ext = "." + format.value
            if format == ExportFormat.EXCEL:
                ext = ".xlsx"
            export_path = os.path.join(self.config.export_dir, f"export_{os.urandom(4).hex()}{ext}")
        elif not os.path.isabs(export_path):
            export_path = os.path.join(self.config.export_dir, export_path)

        # Create export directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(export_path)), exist_ok=True)

        # Export data
        try:
            if format == ExportFormat.JSON:
                df.to_json(export_path, orient="records", indent=2)
            elif format == ExportFormat.CSV:
                df.to_csv(export_path, index=False)
            elif format == ExportFormat.HTML:
                df.to_html(export_path)
            elif format == ExportFormat.EXCEL:
                df.to_excel(export_path, index=False)
            elif format == ExportFormat.MARKDOWN:
                with open(export_path, "w") as f:
                    f.write(df.to_markdown())
        except Exception as e:
            raise ValueError(f"Error exporting to {format}: {str(e)}")

        # Create result
        result = {
            "format": format,
            "path": export_path,
            "rows": len(df),
            "columns": len(df.columns),
            "variables": df.columns.tolist(),
        }

        # Handle export if requested
        if export_format and export_path:
            if not os.path.isabs(export_path):
                export_path = os.path.join(self.config.export_dir, export_path)

            self._export_result(result, export_path, export_format)
            result["exported_to"] = export_path

        return result
