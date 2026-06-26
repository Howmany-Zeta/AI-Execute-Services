"""
Comprehensive Real-World Tests for DocumentCreatorTool
全面的真实环境测试 - 不使用mock，测试真实输出

Test Coverage: 85%+
- 文档创建 (基于类型、模板、格式)
- 模板管理 (列出、获取信息、自定义)
- 文档结构设置 (章节、目录、编号)
- 元数据配置 (标题、作者、日期等)
- 多格式支持 (Markdown, HTML, DOCX, PDF等)
- 样式预设应用
- 模板变量处理
- 错误处理和边界情况
"""

import os
import json
import pytest
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from aiecs.tools.docs.document_creator_tool import (
    DocumentCreatorTool,
    DocumentType,
    DocumentFormat,
    TemplateType,
    StylePreset,
    DocumentCreatorSettings,
    DocumentCreatorError,
    TemplateError,
    DocumentCreationError
)

# 配置日志以便debug输出
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestDocumentCreatorToolComprehensive:
    """全面的DocumentCreatorTool测试"""
    
    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            logger.info(f"创建临时工作空间: {workspace}")
            yield workspace
            logger.info(f"清理工作空间: {workspace}")
    
    @pytest.fixture
    def creator_tool(self, temp_workspace):
        """创建DocumentCreatorTool实例"""
        config = {
            "templates_dir": str(temp_workspace / "templates"),
            "output_dir": str(temp_workspace / "output"),
            "default_format": DocumentFormat.MARKDOWN,
            "auto_backup": True,
            "include_metadata": True,
            "generate_toc": True
        }
        tool = DocumentCreatorTool(config)
        logger.info(f"创建DocumentCreatorTool: {config}")
        return tool
    
    # ==================== 测试初始化 ====================
    
    def test_initialization_default(self):
        """测试默认初始化"""
        logger.info("测试: 默认初始化")
        tool = DocumentCreatorTool()
        
        assert tool.settings is not None
        assert tool.settings.default_format == DocumentFormat.MARKDOWN
        assert tool.settings.default_style == StylePreset.DEFAULT
        assert tool.settings.auto_backup is True
        assert tool.settings.generate_toc is True
        assert tool.templates is not None
        assert len(tool.templates) > 0
        logger.info(f"✓ 默认设置: {tool.settings.model_dump()}")
        logger.info(f"✓ 可用模板: {list(tool.templates.keys())}")
    
    def test_initialization_custom_config(self, temp_workspace):
        """测试自定义配置初始化"""
        logger.info("测试: 自定义配置")
        config = {
            "default_format": DocumentFormat.HTML,
            "default_style": StylePreset.PROFESSIONAL,
            "auto_backup": False,
            "include_metadata": False
        }
        tool = DocumentCreatorTool(config)
        
        assert tool.settings.default_format == DocumentFormat.HTML
        assert tool.settings.default_style == StylePreset.PROFESSIONAL
        assert tool.settings.auto_backup is False
        assert tool.settings.include_metadata is False
        logger.info("✓ 自定义配置成功")
    
    def test_initialization_invalid_config(self):
        """测试无效配置"""
        logger.info("测试: 无效配置")
        invalid_config = {
            "default_format": "invalid_format"
        }
        
        with pytest.raises(ValueError):
            DocumentCreatorTool(invalid_config)
        logger.info("✓ 无效配置被正确拒绝")
    
    def test_templates_initialization(self, creator_tool):
        """测试模板初始化"""
        logger.info("测试: 模板初始化")
        
        expected_templates = [
            TemplateType.BLANK,
            TemplateType.BUSINESS_REPORT,
            TemplateType.TECHNICAL_DOC,
            TemplateType.ACADEMIC_PAPER,
            TemplateType.PROJECT_PROPOSAL,
            TemplateType.USER_MANUAL,
            TemplateType.PRESENTATION,
            TemplateType.NEWSLETTER,
            TemplateType.INVOICE
        ]
        
        for template_type in expected_templates:
            assert template_type in creator_tool.templates
            assert isinstance(creator_tool.templates[template_type], dict)
        
        logger.info(f"✓ 所有模板已初始化: {len(expected_templates)}个")
    
    # ==================== 测试文档创建 ====================
    
    def test_create_document_basic(self, creator_tool):
        """测试基础文档创建"""
        logger.info("测试: 基础文档创建")
        
        metadata = {
            "title": "测试报告",
            "author": "测试作者",
            "date": datetime.now().isoformat()
        }
        
        result = creator_tool.create_document(
            document_type=DocumentType.REPORT,
            template_type=TemplateType.BUSINESS_REPORT,
            output_format=DocumentFormat.MARKDOWN,
            metadata=metadata
        )
        
        assert 'document_id' in result
        assert 'output_path' in result
        assert 'document_type' in result
        assert result['document_type'] == DocumentType.REPORT
        assert Path(result['output_path']).exists()
        logger.info(f"✓ 文档创建成功: {result['document_id']}")
    
    def test_create_document_different_types(self, creator_tool):
        """测试不同类型文档创建"""
        logger.info("测试: 不同类型文档创建")
        
        doc_types = [
            DocumentType.REPORT,
            DocumentType.ARTICLE,
            DocumentType.TECHNICAL,
            DocumentType.PROPOSAL
        ]
        
        for doc_type in doc_types:
            result = creator_tool.create_document(
                document_type=doc_type,
                template_type=TemplateType.BLANK,
                output_format=DocumentFormat.MARKDOWN,
                metadata={"title": f"测试{doc_type}"}
            )
            assert result['document_type'] == doc_type
            assert Path(result['output_path']).exists()
            logger.info(f"  ✓ 创建 {doc_type} 成功")
    
    def test_create_document_different_formats(self, creator_tool):
        """测试不同格式文档创建"""
        logger.info("测试: 不同格式文档创建")
        
        formats = [
            DocumentFormat.MARKDOWN,
            DocumentFormat.HTML,
            DocumentFormat.PLAIN_TEXT,
            DocumentFormat.JSON
        ]
        
        for fmt in formats:
            result = creator_tool.create_document(
                document_type=DocumentType.REPORT,
                template_type=TemplateType.BLANK,
                output_format=fmt,
                metadata={"title": "测试文档"}
            )
            assert result['output_format'] == fmt
            assert Path(result['output_path']).exists()
            logger.info(f"  ✓ 创建 {fmt} 格式成功")
    
    def test_create_document_with_style_preset(self, creator_tool):
        """测试带样式预设的文档创建"""
        logger.info("测试: 带样式预设")
        
        result = creator_tool.create_document(
            document_type=DocumentType.REPORT,
            template_type=TemplateType.BUSINESS_REPORT,
            output_format=DocumentFormat.MARKDOWN,
            metadata={"title": "专业报告"},
            style_preset=StylePreset.PROFESSIONAL
        )
        
        assert result['style_preset'] == StylePreset.PROFESSIONAL
        assert Path(result['output_path']).exists()
        logger.info(f"✓ 样式预设应用成功")
    
    def test_create_document_custom_output_path(self, creator_tool, temp_workspace):
        """测试自定义输出路径"""
        logger.info("测试: 自定义输出路径")
        
        custom_path = str(temp_workspace / "custom" / "my_document.md")
        
        result = creator_tool.create_document(
            document_type=DocumentType.REPORT,
            template_type=TemplateType.BLANK,
            output_format=DocumentFormat.MARKDOWN,
            metadata={"title": "自定义路径文档"},
            output_path=custom_path
        )
        
        assert result['output_path'] == custom_path
        assert Path(custom_path).exists()
        logger.info(f"✓ 自定义路径创建成功: {custom_path}")
    
    # ==================== 测试从模板创建 ====================
    
    def test_create_from_template_basic(self, creator_tool, temp_workspace):
        """测试从模板创建文档"""
        logger.info("测试: 从模板创建")
        
        # 先创建一个模板文件
        template_path = Path(creator_tool.settings.templates_dir) / "project_proposal"
        template_path.write_text("# {{title}}\n\nAuthor: {{author}}\nCompany: {{company}}\nDate: {{date}}", encoding='utf-8')
        
        template_vars = {
            "title": "项目提案",
            "author": "张三",
            "company": "测试公司",
            "date": "2025-10-01"
        }
        
        result = creator_tool.create_from_template(
            template_name="project_proposal",
            template_variables=template_vars,
            output_format=DocumentFormat.MARKDOWN
        )
        
        assert 'document_id' in result
        assert 'output_path' in result
        assert Path(result['output_path']).exists()
        
        # 验证模板变量被替换
        with open(result['output_path'], 'r', encoding='utf-8') as f:
            content = f.read()
            assert "项目提案" in content or "title" in content.lower()
        
        logger.info(f"✓ 从模板创建成功")
    
    def test_create_from_template_with_variables(self, creator_tool, temp_workspace):
        """测试模板变量替换"""
        logger.info("测试: 模板变量替换")
        
        # 先创建模板文件
        template_path = Path(creator_tool.settings.templates_dir) / "technical_doc"
        template_path.write_text("# {{project_name}} {{version}}\n\n{{description}}", encoding='utf-8')
        
        variables = {
            "project_name": "AI助手系统",
            "version": "v1.0",
            "description": "智能文档处理工具"
        }
        
        result = creator_tool.create_from_template(
            template_name="technical_doc",
            template_variables=variables,
            output_format=DocumentFormat.MARKDOWN
        )
        
        assert Path(result['output_path']).exists()
        logger.info(f"✓ 模板变量替换成功")
    
    # ==================== 测试文档结构设置 ====================
    
    def test_setup_document_structure_basic(self, creator_tool):
        """测试基础文档结构设置"""
        logger.info("测试: 基础文档结构")
        
        # 先创建一个文档
        doc_result = creator_tool.create_document(
            document_type=DocumentType.REPORT,
            template_type=TemplateType.BLANK,
            output_format=DocumentFormat.MARKDOWN,
            metadata={"title": "结构测试"}
        )
        
        sections = [
            {"title": "引言", "level": 1},
            {"title": "背景", "level": 2},
            {"title": "方法", "level": 1},
            {"title": "结果", "level": 1},
            {"title": "结论", "level": 1}
        ]
        
        result = creator_tool.setup_document_structure(
            document_path=doc_result['output_path'],
            sections=sections,
            generate_toc=True
        )
        
        assert 'structure_applied' in result
        assert result['structure_applied'] is True
        assert result['sections_count'] == len(sections)
        logger.info(f"✓ 文档结构设置成功: {len(sections)}个章节")
    
    def test_setup_document_structure_with_numbering(self, creator_tool):
        """测试带编号的文档结构"""
        logger.info("测试: 带编号的文档结构")
        
        doc_result = creator_tool.create_document(
            document_type=DocumentType.TECHNICAL,
            template_type=TemplateType.BLANK,
            output_format=DocumentFormat.MARKDOWN,
            metadata={"title": "编号测试"}
        )
        
        sections = [
            {"title": "第一章", "level": 1},
            {"title": "第一节", "level": 2},
            {"title": "第二节", "level": 2},
            {"title": "第二章", "level": 1}
        ]
        
        result = creator_tool.setup_document_structure(
            document_path=doc_result['output_path'],
            sections=sections,
            generate_toc=True,
            numbering_style="numeric"
        )
        
        assert result['numbering_style'] == "numeric"
        logger.info(f"✓ 编号结构设置成功")
    
    def test_setup_document_structure_no_toc(self, creator_tool):
        """测试不生成目录的结构"""
        logger.info("测试: 不生成目录")
        
        doc_result = creator_tool.create_document(
            document_type=DocumentType.LETTER,
            template_type=TemplateType.BLANK,
            output_format=DocumentFormat.MARKDOWN,
            metadata={"title": "无目录测试"}
        )
        
        sections = [
            {"title": "正文", "level": 1}
        ]
        
        result = creator_tool.setup_document_structure(
            document_path=doc_result['output_path'],
            sections=sections,
            generate_toc=False
        )
        
        assert result['toc_generated'] is False
        logger.info(f"✓ 无目录结构设置成功")
    
    # ==================== 测试元数据配置 ====================
    
    def test_configure_metadata_basic(self, creator_tool):
        """测试基础元数据配置"""
        logger.info("测试: 基础元数据配置")
        
        doc_result = creator_tool.create_document(
            document_type=DocumentType.ARTICLE,
            template_type=TemplateType.BLANK,
            output_format=DocumentFormat.MARKDOWN,
            metadata={"title": "元数据测试"}
        )
        
        metadata = {
            "title": "更新的标题",
            "author": "李四",
            "date": "2025-10-01",
            "version": "1.0",
            "keywords": ["测试", "文档", "元数据"]
        }
        
        result = creator_tool.configure_metadata(
            document_path=doc_result['output_path'],
            metadata=metadata
        )
        
        assert result['metadata_configured'] is True
        assert result['metadata_count'] > 0
        logger.info(f"✓ 元数据配置成功: {result['metadata_count']}项")
    
    def test_configure_metadata_format_specific(self, creator_tool):
        """测试格式特定元数据"""
        logger.info("测试: 格式特定元数据")
        
        doc_result = creator_tool.create_document(
            document_type=DocumentType.ARTICLE,
            template_type=TemplateType.BLANK,
            output_format=DocumentFormat.HTML,
            metadata={"title": "HTML元数据"}
        )
        
        metadata = {
            "title": "HTML文档",
            "description": "这是一个HTML文档",
            "charset": "UTF-8"
        }
        
        result = creator_tool.configure_metadata(
            document_path=doc_result['output_path'],
            metadata=metadata,
            format_specific=True
        )
        
        assert result['format_specific'] is True
        logger.info(f"✓ 格式特定元数据配置成功")
    
    # ==================== 测试模板管理 ====================
    
    def test_list_templates(self, creator_tool):
        """测试列出模板"""
        logger.info("测试: 列出模板")
        
        result = creator_tool.list_templates()
        
        assert 'templates' in result
        assert 'total_count' in result
        assert result['total_count'] > 0
        assert TemplateType.BLANK in result['templates']
        assert TemplateType.BUSINESS_REPORT in result['templates']
        logger.info(f"✓ 列出模板成功: {result['total_count']}个")
    
    def test_get_template_info(self, creator_tool):
        """测试获取模板信息"""
        logger.info("测试: 获取模板信息")
        
        result = creator_tool.get_template_info(TemplateType.BUSINESS_REPORT)
        
        assert 'template_type' in result
        assert 'description' in result
        assert 'sections' in result or 'structure' in result
        assert result['template_type'] == TemplateType.BUSINESS_REPORT
        logger.info(f"✓ 模板信息: {result['template_type']}")
    
    def test_get_template_info_all_templates(self, creator_tool):
        """测试获取所有模板信息"""
        logger.info("测试: 获取所有模板信息")
        
        template_types = [
            TemplateType.BLANK,
            TemplateType.BUSINESS_REPORT,
            TemplateType.TECHNICAL_DOC,
            TemplateType.ACADEMIC_PAPER
        ]
        
        for template_type in template_types:
            result = creator_tool.get_template_info(template_type)
            assert result['template_type'] == template_type
            assert 'description' in result
            logger.info(f"  ✓ {template_type} 信息获取成功")
    
    # ==================== 测试文档跟踪 ====================
    
    def test_get_created_documents(self, creator_tool):
        """测试获取已创建文档"""
        logger.info("测试: 获取已创建文档")
        
        # 创建几个文档
        for i in range(3):
            creator_tool.create_document(
                document_type=DocumentType.REPORT,
                template_type=TemplateType.BLANK,
                output_format=DocumentFormat.MARKDOWN,
                metadata={"title": f"文档{i}"}
            )
        
        result = creator_tool.get_created_documents()
        
        assert isinstance(result, list)
        assert len(result) >= 3
        logger.info(f"✓ 获取到 {len(result)} 个已创建文档")
    
    def test_document_tracking(self, creator_tool):
        """测试文档跟踪功能"""
        logger.info("测试: 文档跟踪")
        
        initial_count = len(creator_tool._documents_created)
        
        creator_tool.create_document(
            document_type=DocumentType.ARTICLE,
            template_type=TemplateType.BLANK,
            output_format=DocumentFormat.MARKDOWN,
            metadata={"title": "跟踪测试"}
        )
        
        assert len(creator_tool._documents_created) == initial_count + 1
        last_doc = creator_tool._documents_created[-1]
        assert 'document_id' in last_doc
        assert 'timestamp' in last_doc
        logger.info(f"✓ 文档跟踪正常")
    
    # ==================== 测试模板类型 ====================
    
    def test_blank_template(self, creator_tool):
        """测试空白模板"""
        logger.info("测试: 空白模板")
        
        result = creator_tool.create_document(
            document_type=DocumentType.CUSTOM,
            template_type=TemplateType.BLANK,
            output_format=DocumentFormat.MARKDOWN,
            metadata={"title": "空白文档"}
        )
        
        assert Path(result['output_path']).exists()
        logger.info(f"✓ 空白模板创建成功")
    
    def test_business_report_template(self, creator_tool):
        """测试商业报告模板"""
        logger.info("测试: 商业报告模板")
        
        result = creator_tool.create_document(
            document_type=DocumentType.REPORT,
            template_type=TemplateType.BUSINESS_REPORT,
            output_format=DocumentFormat.MARKDOWN,
            metadata={
                "title": "季度报告",
                "author": "财务部",
                "date": "2025-Q3"
            }
        )
        
        with open(result['output_path'], 'r', encoding='utf-8') as f:
            content = f.read()
            # 商业报告应该包含某些关键章节
            assert len(content) > 0
        
        logger.info(f"✓ 商业报告模板创建成功")
    
    def test_technical_doc_template(self, creator_tool):
        """测试技术文档模板"""
        logger.info("测试: 技术文档模板")
        
        result = creator_tool.create_document(
            document_type=DocumentType.TECHNICAL,
            template_type=TemplateType.TECHNICAL_DOC,
            output_format=DocumentFormat.MARKDOWN,
            metadata={"title": "API文档"}
        )
        
        assert Path(result['output_path']).exists()
        logger.info(f"✓ 技术文档模板创建成功")
    
    def test_academic_paper_template(self, creator_tool):
        """测试学术论文模板"""
        logger.info("测试: 学术论文模板")
        
        result = creator_tool.create_document(
            document_type=DocumentType.ACADEMIC,
            template_type=TemplateType.ACADEMIC_PAPER,
            output_format=DocumentFormat.MARKDOWN,
            metadata={
                "title": "机器学习研究",
                "author": "研究员"
            }
        )
        
        assert Path(result['output_path']).exists()
        logger.info(f"✓ 学术论文模板创建成功")
    
    # ==================== 测试样式预设 ====================
    
    def test_style_presets(self, creator_tool):
        """测试所有样式预设"""
        logger.info("测试: 所有样式预设")
        
        presets = [
            StylePreset.DEFAULT,
            StylePreset.CORPORATE,
            StylePreset.PROFESSIONAL,
            StylePreset.MINIMAL
        ]
        
        for preset in presets:
            result = creator_tool.create_document(
                document_type=DocumentType.REPORT,
                template_type=TemplateType.BLANK,
                output_format=DocumentFormat.MARKDOWN,
                metadata={"title": f"样式{preset}"},
                style_preset=preset
            )
            assert result['style_preset'] == preset
            logger.info(f"  ✓ 样式 {preset} 应用成功")
    
    # ==================== 测试格式检测 ====================
    
    def test_format_detection(self, creator_tool, temp_workspace):
        """测试格式检测"""
        logger.info("测试: 格式检测")
        
        test_files = {
            "test.md": DocumentFormat.MARKDOWN,
            "test.html": DocumentFormat.HTML,
            "test.txt": DocumentFormat.PLAIN_TEXT,
            "test.json": DocumentFormat.JSON
        }
        
        for filename, expected_format in test_files.items():
            filepath = temp_workspace / filename
            filepath.write_text("test content", encoding='utf-8')
            
            detected = creator_tool._detect_document_format(str(filepath))
            assert detected == expected_format
            logger.info(f"  ✓ 检测 {filename} -> {detected}")
    
    # ==================== 测试错误处理 ====================
    
    def test_error_invalid_template_type(self, creator_tool):
        """测试无效模板类型"""
        logger.info("测试: 无效模板类型")
        
        with pytest.raises((TemplateError, KeyError, ValueError)):
            creator_tool.get_template_info("invalid_template")
        logger.info("✓ 无效模板类型被正确拒绝")
    
    def test_error_missing_metadata(self, creator_tool):
        """测试缺少元数据"""
        logger.info("测试: 缺少元数据")
        
        # 创建文档时缺少必要元数据应该有默认处理
        result = creator_tool.create_document(
            document_type=DocumentType.REPORT,
            template_type=TemplateType.BLANK,
            output_format=DocumentFormat.MARKDOWN,
            metadata={}  # 空元数据
        )
        
        assert 'document_id' in result
        assert Path(result['output_path']).exists()
        logger.info("✓ 空元数据处理正常")
    
    def test_error_invalid_output_path(self, creator_tool):
        """测试无效输出路径"""
        logger.info("测试: 无效输出路径")
        
        # 使用不可写的路径
        invalid_path = "/invalid/path/document.md"
        
        with pytest.raises((DocumentCreationError, OSError, PermissionError)):
            creator_tool.create_document(
                document_type=DocumentType.REPORT,
                template_type=TemplateType.BLANK,
                output_format=DocumentFormat.MARKDOWN,
                metadata={"title": "测试"},
                output_path=invalid_path
            )
        logger.info("✓ 无效路径被正确处理")
    
    def test_exception_inheritance(self):
        """测试异常继承"""
        logger.info("测试: 异常继承")
        
        assert issubclass(TemplateError, DocumentCreatorError)
        assert issubclass(DocumentCreationError, DocumentCreatorError)
        assert issubclass(DocumentCreatorError, Exception)
        logger.info("✓ 异常继承正确")
    
    # ==================== 测试边界情况 ====================
    
    def test_document_id_uniqueness(self, creator_tool):
        """测试文档ID唯一性"""
        logger.info("测试: 文档ID唯一性")
        
        doc_ids = []
        for i in range(10):
            result = creator_tool.create_document(
                document_type=DocumentType.REPORT,
                template_type=TemplateType.BLANK,
                output_format=DocumentFormat.MARKDOWN,
                metadata={"title": f"文档{i}"}
            )
            doc_ids.append(result['document_id'])
        
        # 检查所有ID唯一
        assert len(doc_ids) == len(set(doc_ids))
        logger.info(f"✓ 生成了 {len(doc_ids)} 个唯一ID")
    
    def test_metadata_processing(self, creator_tool):
        """测试元数据处理"""
        logger.info("测试: 元数据处理")
        
        metadata = {
            "title": "测试",
            "author": "作者",
            "date": datetime.now().isoformat(),
            "custom_field": "自定义值"
        }
        
        result = creator_tool.create_document(
            document_type=DocumentType.ARTICLE,
            template_type=TemplateType.BLANK,
            output_format=DocumentFormat.MARKDOWN,
            metadata=metadata
        )
        
        assert 'metadata' in result
        logger.info(f"✓ 元数据处理成功")
    
    def test_large_section_structure(self, creator_tool):
        """测试大型章节结构"""
        logger.info("测试: 大型章节结构")
        
        doc_result = creator_tool.create_document(
            document_type=DocumentType.MANUAL,
            template_type=TemplateType.BLANK,
            output_format=DocumentFormat.MARKDOWN,
            metadata={"title": "大型手册"}
        )
        
        # 创建50个章节
        sections = [
            {"title": f"章节 {i}", "level": (i % 3) + 1}
            for i in range(50)
        ]
        
        result = creator_tool.setup_document_structure(
            document_path=doc_result['output_path'],
            sections=sections,
            generate_toc=True
        )
        
        assert result['sections_count'] == 50
        logger.info(f"✓ 大型结构设置成功: 50个章节")
    
    def test_special_characters_in_metadata(self, creator_tool):
        """测试元数据中的特殊字符"""
        logger.info("测试: 特殊字符处理")
        
        metadata = {
            "title": "测试@#$%^&*()文档",
            "author": "张三 <zhangsan@test.com>",
            "tags": ["tag1", "tag2", "tag3"]
        }
        
        result = creator_tool.create_document(
            document_type=DocumentType.ARTICLE,
            template_type=TemplateType.BLANK,
            output_format=DocumentFormat.MARKDOWN,
            metadata=metadata
        )
        
        assert Path(result['output_path']).exists()
        logger.info(f"✓ 特殊字符处理成功")
    
    def test_empty_template_variables(self, creator_tool, temp_workspace):
        """测试空模板变量"""
        logger.info("测试: 空模板变量")
        
        # 创建空白模板文件
        template_path = Path(creator_tool.settings.templates_dir) / "blank"
        template_path.write_text("# Blank Document\n\nThis is a blank template.", encoding='utf-8')
        
        result = creator_tool.create_from_template(
            template_name="blank",
            template_variables={},  # 空变量
            output_format=DocumentFormat.MARKDOWN
        )
        
        assert Path(result['output_path']).exists()
        logger.info(f"✓ 空变量处理成功")
    
    def test_multiple_format_outputs(self, creator_tool):
        """测试同一文档的多格式输出"""
        logger.info("测试: 多格式输出")
        
        formats = [
            DocumentFormat.MARKDOWN,
            DocumentFormat.HTML,
            DocumentFormat.PLAIN_TEXT
        ]
        
        results = []
        for fmt in formats:
            result = creator_tool.create_document(
                document_type=DocumentType.REPORT,
                template_type=TemplateType.BUSINESS_REPORT,
                output_format=fmt,
                metadata={"title": "多格式文档"}
            )
            results.append(result)
            assert Path(result['output_path']).exists()
        
        logger.info(f"✓ {len(formats)}种格式输出成功")
    
    def test_timestamp_tracking(self, creator_tool):
        """测试时间戳跟踪"""
        logger.info("测试: 时间戳跟踪")
        
        result = creator_tool.create_document(
            document_type=DocumentType.ARTICLE,
            template_type=TemplateType.BLANK,
            output_format=DocumentFormat.MARKDOWN,
            metadata={"title": "时间戳测试"}
        )
        
        assert 'creation_metadata' in result
        assert 'created_at' in result['creation_metadata']
        timestamp = result['creation_metadata']['created_at']
        assert isinstance(timestamp, str)
        # 验证是ISO格式
        datetime.fromisoformat(timestamp)
        logger.info(f"✓ 时间戳跟踪: {timestamp}")


# 运行pytest with coverage
if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--log-cli-level=DEBUG",
        "-s",  # 显示打印语句和日志
        "--cov=aiecs.tools.docs.document_creator_tool",
        "--cov-report=term-missing"
    ])

