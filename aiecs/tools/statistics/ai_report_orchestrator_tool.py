"""
AI Report Orchestrator Tool - AI-powered comprehensive report generation

This tool provides advanced report generation with:
- Automated analysis report creation
- Multiple report types and formats
- Integration with analysis results
- Visualization embedding
- Export to multiple formats
"""

import os
import logging
import tempfile
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool


class ReportType(str, Enum):
    """Types of reports"""

    EXECUTIVE_SUMMARY = "executive_summary"
    TECHNICAL_REPORT = "technical_report"
    BUSINESS_REPORT = "business_report"
    RESEARCH_PAPER = "research_paper"
    DATA_QUALITY_REPORT = "data_quality_report"


class ReportFormat(str, Enum):
    """Report output formats"""

    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    WORD = "word"
    JSON = "json"


class ReportOrchestratorError(Exception):
    """Base exception for Report Orchestrator errors"""


class ReportGenerationError(ReportOrchestratorError):
    """Raised when report generation fails"""


@register_tool("ai_report_orchestrator")
class AIReportOrchestratorTool(BaseTool):
    """
    AI-powered analysis report generator that can:
    1. Generate comprehensive analysis reports
    2. Customize report structure and style
    3. Include visualizations and tables
    4. Export to multiple formats
    5. Integrate analysis results and insights

    Integrates with report_tool for document generation.
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the AI report orchestrator tool
        
        Automatically reads from environment variables with AI_REPORT_ORCHESTRATOR_ prefix.
        Example: AI_REPORT_ORCHESTRATOR_DEFAULT_REPORT_TYPE -> default_report_type
        """

        model_config = SettingsConfigDict(env_prefix="AI_REPORT_ORCHESTRATOR_")

        default_report_type: str = Field(
            default="business_report",
            description="Default report type to generate",
        )
        default_format: str = Field(default="markdown", description="Default report output format")
        output_directory: str = Field(
            default=tempfile.gettempdir(),
            description="Directory for report output files",
        )
        include_code: bool = Field(
            default=False,
            description="Whether to include code snippets in reports",
        )
        include_visualizations: bool = Field(
            default=True,
            description="Whether to include visualizations in reports",
        )
        max_insights_per_report: int = Field(
            default=20,
            description="Maximum number of insights to include per report",
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """Initialize AI Report Orchestrator Tool

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/ai_report_orchestrator.yaml)
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

        self._init_external_tools()

        # Ensure output directory exists
        os.makedirs(self.config.output_directory, exist_ok=True)

    def _init_external_tools(self):
        """Initialize external task tools"""
        self.external_tools = {}

        # Initialize ReportTool for document generation
        try:
            from aiecs.tools.task_tools.report_tool import ReportTool

            self.external_tools["report"] = ReportTool()
            self.logger.info("ReportTool initialized successfully")
        except ImportError:
            self.logger.warning("ReportTool not available")
            self.external_tools["report"] = None

    # Schema definitions
    class GenerateReportSchema(BaseModel):
        """Schema for generate_report operation"""

        analysis_results: Dict[str, Any] = Field(description="Analysis results to include")
        insights: Optional[Dict[str, Any]] = Field(default=None, description="Generated insights")
        report_type: ReportType = Field(default=ReportType.BUSINESS_REPORT, description="Type of report")
        output_format: ReportFormat = Field(default=ReportFormat.MARKDOWN, description="Output format")
        title: Optional[str] = Field(default=None, description="Report title")
        include_code: bool = Field(default=False, description="Include code snippets")

    class FormatReportSchema(BaseModel):
        """Schema for format_report operation"""

        report_content: str = Field(description="Report content to format")
        output_format: ReportFormat = Field(description="Desired output format")
        output_path: Optional[str] = Field(default=None, description="Output file path")

    class ExportReportSchema(BaseModel):
        """Schema for export_report operation"""

        report_content: str = Field(description="Report content")
        output_format: ReportFormat = Field(description="Export format")
        output_path: str = Field(description="Output file path")

    def generate_report(
        self,
        analysis_results: Dict[str, Any],
        insights: Optional[Dict[str, Any]] = None,
        report_type: ReportType = ReportType.BUSINESS_REPORT,
        output_format: ReportFormat = ReportFormat.MARKDOWN,
        title: Optional[str] = None,
        include_code: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive analysis report.

        Args:
            analysis_results: Results from data analysis
            insights: Generated insights to include
            report_type: Type of report to generate
            output_format: Output format
            title: Report title
            include_code: Whether to include code snippets

        Returns:
            Dict containing:
                - report_content: Generated report content
                - sections: Report sections
                - export_path: Path to exported report
                - metadata: Report metadata
        """
        try:
            self.logger.info(f"Generating {report_type.value} report in {output_format.value} format")

            # Generate report title
            if title is None:
                title = self._generate_title(report_type, analysis_results)

            # Build report sections
            sections = self._build_report_sections(analysis_results, insights, report_type, include_code)

            # Compile report content
            report_content = self._compile_report(title, sections, report_type)

            # Format report for output format
            formatted_content = self._format_content(report_content, output_format)

            # Export report
            export_path = self._export_report(formatted_content, output_format, title)

            # Generate metadata
            metadata = {
                "generated_at": datetime.now().isoformat(),
                "report_type": report_type.value,
                "output_format": output_format.value,
                "sections_count": len(sections),
                "word_count": len(report_content.split()),
            }

            return {
                "report_content": report_content,
                "sections": {s["title"]: s["content"] for s in sections},
                "export_path": export_path,
                "metadata": metadata,
                "title": title,
            }

        except Exception as e:
            self.logger.error(f"Error generating report: {e}")
            raise ReportGenerationError(f"Report generation failed: {e}")

    def format_report(
        self,
        report_content: str,
        output_format: ReportFormat,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Format report content to specified format.

        Args:
            report_content: Report content to format
            output_format: Desired output format
            output_path: Optional output file path

        Returns:
            Dict containing formatted report info
        """
        try:
            formatted_content = self._format_content(report_content, output_format)

            if output_path:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(formatted_content)
                export_path = output_path
            else:
                export_path = self._export_report(formatted_content, output_format, "report")

            return {
                "formatted_content": formatted_content,
                "output_format": output_format.value,
                "export_path": export_path,
            }

        except Exception as e:
            self.logger.error(f"Error formatting report: {e}")
            raise ReportGenerationError(f"Report formatting failed: {e}")

    def export_report(
        self,
        report_content: str,
        output_format: ReportFormat,
        output_path: str,
    ) -> Dict[str, Any]:
        """
        Export report to file.

        Args:
            report_content: Report content
            output_format: Export format
            output_path: Output file path

        Returns:
            Dict containing export information
        """
        try:
            formatted_content = self._format_content(report_content, output_format)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(formatted_content)

            file_size = os.path.getsize(output_path)

            return {
                "export_path": output_path,
                "format": output_format.value,
                "file_size_bytes": file_size,
                "success": True,
            }

        except Exception as e:
            self.logger.error(f"Error exporting report: {e}")
            raise ReportGenerationError(f"Report export failed: {e}")

    # Internal report generation methods

    def _generate_title(self, report_type: ReportType, analysis_results: Dict[str, Any]) -> str:
        """Generate appropriate report title"""
        if report_type == ReportType.EXECUTIVE_SUMMARY:
            return "Executive Summary: Data Analysis Report"
        elif report_type == ReportType.TECHNICAL_REPORT:
            return "Technical Data Analysis Report"
        elif report_type == ReportType.BUSINESS_REPORT:
            return "Business Intelligence Report"
        elif report_type == ReportType.RESEARCH_PAPER:
            return "Data Analysis Research Paper"
        elif report_type == ReportType.DATA_QUALITY_REPORT:
            return "Data Quality Assessment Report"
        else:
            return "Data Analysis Report"

    def _build_report_sections(
        self,
        analysis_results: Dict[str, Any],
        insights: Optional[Dict[str, Any]],
        report_type: ReportType,
        include_code: bool,
    ) -> List[Dict[str, str]]:
        """Build report sections based on type"""
        sections = []

        # Executive Summary (for all report types)
        sections.append(
            {
                "title": "Executive Summary",
                "content": self._generate_executive_summary(analysis_results, insights),
            }
        )

        # Methodology section (for technical and research reports)
        if report_type in [
            ReportType.TECHNICAL_REPORT,
            ReportType.RESEARCH_PAPER,
        ]:
            sections.append(
                {
                    "title": "Methodology",
                    "content": self._generate_methodology_section(analysis_results),
                }
            )

        # Data Overview
        sections.append(
            {
                "title": "Data Overview",
                "content": self._generate_data_overview(analysis_results),
            }
        )

        # Findings section
        sections.append(
            {
                "title": "Key Findings",
                "content": self._generate_findings_section(analysis_results, insights),
            }
        )

        # Statistical Analysis (for technical reports)
        if report_type == ReportType.TECHNICAL_REPORT and "statistical_analysis" in analysis_results:
            sections.append(
                {
                    "title": "Statistical Analysis",
                    "content": self._generate_statistics_section(analysis_results.get("statistical_analysis", {})),
                }
            )

        # Insights section
        if insights:
            sections.append(
                {
                    "title": "Insights and Patterns",
                    "content": self._generate_insights_section(insights),
                }
            )

        # Recommendations
        sections.append(
            {
                "title": "Recommendations",
                "content": self._generate_recommendations_section(analysis_results, insights),
            }
        )

        # Conclusion
        sections.append(
            {
                "title": "Conclusion",
                "content": self._generate_conclusion(analysis_results, insights),
            }
        )

        # Appendix (if code included)
        if include_code:
            sections.append(
                {
                    "title": "Appendix: Technical Details",
                    "content": self._generate_appendix(analysis_results),
                }
            )

        return sections

    def _generate_executive_summary(
        self,
        analysis_results: Dict[str, Any],
        insights: Optional[Dict[str, Any]],
    ) -> str:
        """Generate executive summary"""
        lines = []

        # Get data profile if available
        data_profile = analysis_results.get("data_profile", {})
        summary = data_profile.get("summary", {})

        if summary:
            lines.append(f"This report presents a comprehensive analysis of a dataset containing {summary.get('rows', 'N/A')} rows and {summary.get('columns', 'N/A')} columns.")

            missing_pct = summary.get("missing_percentage", 0)
            if missing_pct > 0:
                lines.append(f"The dataset has {missing_pct:.2f}% missing values.")

        # Add insight summary
        if insights and "summary" in insights:
            lines.append(f"\n{insights['summary']}")

        # Add key metrics
        if insights and "priority_insights" in insights:
            top_insights = insights["priority_insights"][:3]
            if top_insights:
                lines.append("\nKey highlights:")
                for i, insight in enumerate(top_insights, 1):
                    lines.append(f"{i}. {insight.get('title', 'Insight')}")

        return "\n".join(lines) if lines else "Analysis completed successfully."

    def _generate_methodology_section(self, analysis_results: Dict[str, Any]) -> str:
        """Generate methodology section"""
        lines = [
            "The analysis was conducted using a systematic approach:",
            "",
            "1. **Data Loading**: Data was loaded and validated for quality",
            "2. **Data Profiling**: Comprehensive statistical profiling was performed",
            "3. **Data Transformation**: Necessary transformations and cleaning were applied",
            "4. **Statistical Analysis**: Various statistical tests and analyses were conducted",
            "5. **Insight Generation**: Patterns, trends, and anomalies were identified",
            "6. **Visualization**: Key findings were visualized for clarity",
        ]

        return "\n".join(lines)

    def _generate_data_overview(self, analysis_results: Dict[str, Any]) -> str:
        """Generate data overview section"""
        lines = []

        data_profile = analysis_results.get("data_profile", {})
        summary = data_profile.get("summary", {})

        if summary:
            lines.append("**Dataset Characteristics:**")
            lines.append(f"- Total Records: {summary.get('rows', 'N/A')}")
            lines.append(f"- Total Columns: {summary.get('columns', 'N/A')}")
            lines.append(f"- Numeric Columns: {summary.get('numeric_columns', 'N/A')}")
            lines.append(f"- Categorical Columns: {summary.get('categorical_columns', 'N/A')}")
            lines.append(f"- Missing Values: {summary.get('missing_percentage', 0):.2f}%")
            lines.append(f"- Duplicate Rows: {summary.get('duplicate_rows', 0)}")
        else:
            lines.append("Data overview not available.")

        return "\n".join(lines)

    def _generate_findings_section(
        self,
        analysis_results: Dict[str, Any],
        insights: Optional[Dict[str, Any]],
    ) -> str:
        """Generate findings section"""
        lines = []

        # Extract findings from analysis results
        if "findings" in analysis_results:
            findings = analysis_results["findings"]
            for i, finding in enumerate(findings[:10], 1):
                lines.append(f"{i}. **{finding.get('title', 'Finding')}**: {finding.get('description', 'No description')}")

        # Add insights if available
        if insights and "insights" in insights:
            insight_list = insights["insights"][: self.config.max_insights_per_report]
            if insight_list and not lines:
                lines.append("**Key Insights:**")
            for insight in insight_list:
                lines.append(f"- {insight.get('title', 'Insight')}: {insight.get('description', '')}")

        return "\n".join(lines) if lines else "No significant findings to report."

    def _generate_statistics_section(self, stats_results: Dict[str, Any]) -> str:
        """Generate statistics section"""
        lines = ["**Statistical Analysis Results:**", ""]

        if "correlation_matrix" in stats_results:
            lines.append("Correlation analysis was performed to identify relationships between variables.")

        if "hypothesis_tests" in stats_results:
            lines.append("Hypothesis testing was conducted to validate statistical significance.")

        return "\n".join(lines)

    def _generate_insights_section(self, insights: Dict[str, Any]) -> str:
        """Generate insights section"""
        lines = []

        insights.get("insights", [])
        priority_insights = insights.get("priority_insights", [])

        if priority_insights:
            lines.append("**Priority Insights:**")
            for i, insight in enumerate(priority_insights, 1):
                title = insight.get("title", "Insight")
                description = insight.get("description", "")
                confidence = insight.get("confidence", 0)
                impact = insight.get("impact", "medium")

                lines.append(f"\n{i}. **{title}** (Confidence: {confidence:.0%}, Impact: {impact})")
                lines.append(f"   {description}")

                if "recommendation" in insight:
                    lines.append(f"   *Recommendation: {insight['recommendation']}*")

        return "\n".join(lines) if lines else "No insights generated."

    def _generate_recommendations_section(
        self,
        analysis_results: Dict[str, Any],
        insights: Optional[Dict[str, Any]],
    ) -> str:
        """Generate recommendations section"""
        lines = []

        # Get recommendations from analysis results
        if "recommendations" in analysis_results:
            recs = analysis_results["recommendations"]
            for i, rec in enumerate(recs[:10], 1):
                action = rec.get("action", "Action")
                reason = rec.get("reason", "")
                priority = rec.get("priority", "medium")
                lines.append(f"{i}. **{action}** (Priority: {priority})")
                if reason:
                    lines.append(f"   {reason}")

        # Get recommendations from data profiler
        data_profile = analysis_results.get("data_profile", {})
        if "recommendations" in data_profile:
            if not lines:
                lines.append("**Data Quality Recommendations:**")
            for rec in data_profile["recommendations"][:5]:
                lines.append(f"- {rec.get('action', 'Action')}: {rec.get('reason', '')}")

        return "\n".join(lines) if lines else "No specific recommendations at this time."

    def _generate_conclusion(
        self,
        analysis_results: Dict[str, Any],
        insights: Optional[Dict[str, Any]],
    ) -> str:
        """Generate conclusion"""
        lines = []

        lines.append("This comprehensive analysis has provided valuable insights into the dataset.")

        if insights:
            total_insights = insights.get("total_insights", 0)
            lines.append(f"A total of {total_insights} insights were generated through systematic analysis.")

        lines.append("\nThe findings and recommendations presented in this report should be carefully considered in the context of your specific business objectives and constraints.")

        return "\n".join(lines)

    def _generate_appendix(self, analysis_results: Dict[str, Any]) -> str:
        """Generate appendix with technical details"""
        lines = [
            "**Technical Details:**",
            "",
            "This section contains technical information about the analysis process.",
            "",
            "Analysis was performed using the AIECS Data Analysis Orchestrator framework.",
        ]

        return "\n".join(lines)

    def _compile_report(
        self,
        title: str,
        sections: List[Dict[str, str]],
        report_type: ReportType,
    ) -> str:
        """Compile report sections into final document"""
        lines = [
            f"# {title}",
            "",
            f"*Report Type: {report_type.value.replace('_', ' ').title()}*",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "---",
            "",
        ]

        for section in sections:
            lines.append(f"## {section['title']}")
            lines.append("")
            lines.append(section["content"])
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _format_content(self, content: str, output_format: ReportFormat) -> str:
        """Format content for specified output format"""
        if output_format == ReportFormat.MARKDOWN:
            return content
        elif output_format == ReportFormat.HTML:
            return self._markdown_to_html(content)
        elif output_format == ReportFormat.JSON:
            return self._content_to_json(content)
        else:
            # For PDF and Word, return markdown (would need additional
            # libraries for conversion)
            self.logger.warning(f"Format {output_format.value} not fully implemented, returning markdown")
            return content

    def _markdown_to_html(self, markdown_content: str) -> str:
        """Convert markdown to HTML (basic implementation)"""
        html = markdown_content
        # Basic conversions
        html = html.replace("# ", "<h1>").replace("\n", "</h1>\n", 1)
        html = html.replace("## ", "<h2>").replace("\n", "</h2>\n")
        html = html.replace("**", "<strong>").replace("**", "</strong>")
        html = html.replace("*", "<em>").replace("*", "</em>")
        html = f"<html><body>{html}</body></html>"
        return html

    def _content_to_json(self, content: str) -> str:
        """Convert content to JSON format"""
        import json

        return json.dumps({"content": content, "format": "markdown"}, indent=2)

    def _export_report(self, content: str, output_format: ReportFormat, title: str) -> str:
        """Export report to file"""
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = title.replace(" ", "_").replace(":", "").lower()

        extension_map = {
            ReportFormat.MARKDOWN: ".md",
            ReportFormat.HTML: ".html",
            ReportFormat.PDF: ".pdf",
            ReportFormat.WORD: ".docx",
            ReportFormat.JSON: ".json",
        }

        extension = extension_map.get(output_format, ".txt")
        filename = f"{safe_title}_{timestamp}{extension}"
        filepath = os.path.join(self.config.output_directory, filename)

        # Write file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        self.logger.info(f"Report exported to: {filepath}")
        return filepath
