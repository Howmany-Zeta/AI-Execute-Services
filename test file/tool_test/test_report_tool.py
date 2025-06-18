import os
import pytest
import tempfile
import pandas as pd
from datetime import datetime
from pathlib import Path

from app.tools.report_tool import (
    ReportTool, ReportToolError, InputValidationError, 
    SecurityError, FileOperationError, HtmlReportSchema
)

# Test fixtures
@pytest.fixture
def report_tool():
    """Create a ReportTool instance with test configuration."""
    test_dir = tempfile.mkdtemp(prefix="report_tool_test_")
    config = {
        "templates_dir": test_dir,
        "default_output_dir": test_dir,
        "cache_ttl_seconds": 10,
        "cache_max_items": 5
    }
    tool = ReportTool(config=config)
    yield tool
    # Clean up test directory after tests
    for root, dirs, files in os.walk(test_dir, topdown=False):
        for file in files:
            os.remove(os.path.join(root, file))
        for dir in dirs:
            os.rmdir(os.path.join(root, dir))
    os.rmdir(test_dir)

@pytest.fixture
def html_template():
    """Create a simple HTML template for testing."""
    return "<html><body><h1>{{title}}</h1><p>{{content}}</p></body></html>"

@pytest.fixture
def markdown_template():
    """Create a simple Markdown template for testing."""
    return "# {{title}}\n\n{{content}}"

@pytest.fixture
def test_data():
    """Create test data for reports."""
    return {
        "title": "Test Report",
        "content": "This is a test report generated at " + datetime.now().isoformat(),
        "data": pd.DataFrame({
            "Category": ["A", "B", "C", "D"],
            "Value": [10, 20, 15, 25]
        })
    }

# Unit tests
@pytest.mark.asyncio
async def test_generate_html(report_tool, html_template, test_data):
    """Test HTML report generation."""
    # Create output path
    output_path = os.path.join(report_tool.settings.default_output_dir, "test_report.html")
    
    # Generate HTML report
    result = await report_tool.run(
        op='generate_html',
        template_str=html_template,
        context={"title": test_data["title"], "content": test_data["content"]},
        output_path=output_path
    )
    
    # Verify result
    assert isinstance(result, str)
    assert os.path.isfile(result)
    assert result == output_path
    
    # Verify content
    with open(result, 'r', encoding='utf-8') as f:
        content = f.read()
        assert test_data["title"] in content
        assert test_data["content"] in content
        assert "<h1>" in content
        assert "</html>" in content

@pytest.mark.asyncio
async def test_generate_pdf(report_tool, html_template, test_data):
    """Test PDF report generation."""
    # Create output path
    output_path = os.path.join(report_tool.settings.default_output_dir, "test_report.pdf")
    
    # Generate PDF report
    result = await report_tool.run(
        op='generate_pdf',
        html=f"<h1>{test_data['title']}</h1><p>{test_data['content']}</p>",
        output_path=output_path
    )
    
    # Verify result
    assert isinstance(result, str)
    assert os.path.isfile(result)
    assert result == output_path
    
    # Verify file size (PDF should have some content)
    assert os.path.getsize(result) > 0

@pytest.mark.asyncio
async def test_generate_excel(report_tool, test_data):
    """Test Excel report generation."""
    # Create output path
    output_path = os.path.join(report_tool.settings.default_output_dir, "test_report.xlsx")
    
    # Generate Excel report
    result = await report_tool.run(
        op='generate_excel',
        sheets={"Data": test_data["data"]},
        output_path=output_path
    )
    
    # Verify result
    assert isinstance(result, str)
    assert os.path.isfile(result)
    assert result == output_path
    
    # Verify file size
    assert os.path.getsize(result) > 0

@pytest.mark.asyncio
async def test_generate_markdown(report_tool, markdown_template, test_data):
    """Test Markdown report generation."""
    # Create output path
    output_path = os.path.join(report_tool.settings.default_output_dir, "test_report.md")
    
    # Generate Markdown report
    result = await report_tool.run(
        op='generate_markdown',
        template_str=markdown_template,
        context={"title": test_data["title"], "content": test_data["content"]},
        output_path=output_path
    )
    
    # Verify result
    assert isinstance(result, str)
    assert os.path.isfile(result)
    assert result == output_path
    
    # Verify content
    with open(result, 'r', encoding='utf-8') as f:
        content = f.read()
        assert f"# {test_data['title']}" in content
        assert test_data["content"] in content

@pytest.mark.asyncio
async def test_generate_image(report_tool, test_data):
    """Test image report generation."""
    # Create output path
    output_path = os.path.join(report_tool.settings.default_output_dir, "test_chart.png")
    
    # Generate image report
    result = await report_tool.run(
        op='generate_image',
        chart_type='bar',
        data=test_data["data"],
        x_col='Category',
        y_col='Value',
        title=test_data["title"],
        output_path=output_path
    )
    
    # Verify result
    assert isinstance(result, str)
    assert os.path.isfile(result)
    assert result == output_path
    
    # Verify file size
    assert os.path.getsize(result) > 0

@pytest.mark.asyncio
async def test_batch_generate(report_tool, html_template, test_data):
    """Test batch report generation."""
    # Create output paths
    output_path1 = os.path.join(report_tool.settings.default_output_dir, "batch1.html")
    output_path2 = os.path.join(report_tool.settings.default_output_dir, "batch2.html")
    
    # Generate batch reports
    result = await report_tool.run(
        op='batch_generate',
        operation='generate_html',
        contexts=[
            {
                "template_str": html_template,
                "context": {"title": "Batch 1", "content": test_data["content"]}
            },
            {
                "template_str": html_template,
                "context": {"title": "Batch 2", "content": test_data["content"]}
            }
        ],
        output_paths=[output_path1, output_path2]
    )
    
    # Verify result
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(os.path.isfile(path) for path in result)
    
    # Verify content
    with open(output_path1, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "<h1>Batch 1</h1>" in content
    
    with open(output_path2, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "<h1>Batch 2</h1>" in content

@pytest.mark.asyncio
async def test_invalid_extension(report_tool, html_template):
    """Test security validation for invalid file extensions."""
    with pytest.raises(SecurityError):
        await report_tool.run(
            op='generate_html',
            template_str=html_template,
            context={"title": "Test", "content": "Content"},
            output_path="malicious.exe"
        )

@pytest.mark.asyncio
async def test_invalid_operation(report_tool):
    """Test validation for invalid operations."""
    with pytest.raises(ReportToolError):
        await report_tool.run(
            op='invalid_operation',
            template_str="<h1>Test</h1>",
            context={},
            output_path="test.html"
        )

@pytest.mark.asyncio
async def test_missing_required_params(report_tool):
    """Test validation for missing required parameters."""
    with pytest.raises(InputValidationError):
        await report_tool.run(
            op='generate_html',
            context={},  # Missing template_str or template_path
            output_path="test.html"
        )

@pytest.mark.asyncio
async def test_metrics(report_tool, html_template, test_data):
    """Test metrics collection."""
    # Generate a report
    await report_tool.run(
        op='generate_html',
        template_str=html_template,
        context={"title": test_data["title"], "content": test_data["content"]},
        output_path=os.path.join(report_tool.settings.default_output_dir, "metrics_test.html")
    )
    
    # Check metrics
    metrics = report_tool._metrics.to_dict()
    assert metrics["requests"] >= 1
    assert "avg_processing_time" in metrics
    assert metrics["avg_processing_time"] > 0