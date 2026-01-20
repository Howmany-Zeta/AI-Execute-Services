#!/usr/bin/env python3
"""
运行时测试：验证所有工具的配置加载是否正确

实际创建工具实例并测试配置分离
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_tool_config(tool_name: str, tool_class):
    """测试单个工具的配置"""
    try:
        # 混合配置：包含 executor 字段和工具特有字段
        config = {
            "enable_cache": True,
            "max_workers": 8,
            "timeout": 60,
            "retry_attempts": 3,
            "test_field": "test_value",
        }
        
        # 尝试创建工具
        tool = tool_class(config=config)
        
        # 验证配置分离
        executor_config = tool._extract_executor_config(config)
        
        # 检查是否正确过滤
        executor_fields = {'enable_cache', 'max_workers', 'timeout', 'retry_attempts'}
        has_executor_fields = any(k in executor_config for k in executor_fields)
        
        # 检查工具配置对象
        has_config_obj = hasattr(tool, 'config')
        
        if has_executor_fields and has_config_obj:
            return True, "✓ 配置正确"
        else:
            return False, "✗ 配置分离失败"
            
    except Exception as e:
        error_msg = str(e)
        # 检查是否是 extra='forbid' 错误
        if "Extra inputs are not permitted" in error_msg:
            return False, f"✗ ExecutorConfig 验证错误: {error_msg[:100]}"
        else:
            return False, f"✗ 其他错误: {error_msg[:100]}"


def main():
    """测试所有工具"""
    print("="*80)
    print("运行时测试：所有工具配置加载")
    print("="*80)
    
    # 定义要测试的工具
    tools_to_test = [
        # API Source
        ("APISourceTool", "aiecs.tools.apisource.tool", "APISourceTool"),
        
        # Document Tools
        ("DocumentParserTool", "aiecs.tools.docs.document_parser_tool", "DocumentParserTool"),
        ("DocumentWriterTool", "aiecs.tools.docs.document_writer_tool", "DocumentWriterTool"),
        ("DocumentCreatorTool", "aiecs.tools.docs.document_creator_tool", "DocumentCreatorTool"),
        ("DocumentLayoutTool", "aiecs.tools.docs.document_layout_tool", "DocumentLayoutTool"),
        ("ContentInsertionTool", "aiecs.tools.docs.content_insertion_tool", "ContentInsertionTool"),
        ("AIDocumentOrchestrator", "aiecs.tools.docs.ai_document_orchestrator", "AIDocumentOrchestrator"),
        ("AIDocumentWriterOrchestrator", "aiecs.tools.docs.ai_document_writer_orchestrator", "AIDocumentWriterOrchestrator"),
        
        # Knowledge Graph Tools
        ("KnowledgeGraphBuilderTool", "aiecs.tools.knowledge_graph.kg_builder_tool", "KnowledgeGraphBuilderTool"),
        ("GraphSearchTool", "aiecs.tools.knowledge_graph.graph_search_tool", "GraphSearchTool"),
        ("GraphReasoningTool", "aiecs.tools.knowledge_graph.graph_reasoning_tool", "GraphReasoningTool"),
        
        # Statistics Tools
        ("DataLoaderTool", "aiecs.tools.statistics.data_loader_tool", "DataLoaderTool"),
        ("DataProfilerTool", "aiecs.tools.statistics.data_profiler_tool", "DataProfilerTool"),
        ("DataTransformerTool", "aiecs.tools.statistics.data_transformer_tool", "DataTransformerTool"),
        ("DataVisualizerTool", "aiecs.tools.statistics.data_visualizer_tool", "DataVisualizerTool"),
        ("StatisticalAnalyzerTool", "aiecs.tools.statistics.statistical_analyzer_tool", "StatisticalAnalyzerTool"),
        ("AIInsightGeneratorTool", "aiecs.tools.statistics.ai_insight_generator_tool", "AIInsightGeneratorTool"),
        ("AIReportOrchestratorTool", "aiecs.tools.statistics.ai_report_orchestrator_tool", "AIReportOrchestratorTool"),
        
        # Task Tools
        ("ScraperTool", "aiecs.tools.scraper_tool.core", "ScraperTool"),
        ("ImageTool", "aiecs.tools.task_tools.image_tool", "ImageTool"),
        ("OfficeTool", "aiecs.tools.task_tools.office_tool", "OfficeTool"),
        ("ChartTool", "aiecs.tools.task_tools.chart_tool", "ChartTool"),
        ("PandasTool", "aiecs.tools.task_tools.pandas_tool", "PandasTool"),
        ("ReportTool", "aiecs.tools.task_tools.report_tool", "ReportTool"),
        ("ResearchTool", "aiecs.tools.task_tools.research_tool", "ResearchTool"),
        ("ClassifierTool", "aiecs.tools.task_tools.classfire_tool", "ClassifierTool"),
        ("StatsTool", "aiecs.tools.task_tools.stats_tool", "StatsTool"),
    ]
    
    results = []
    
    print(f"\n测试 {len(tools_to_test)} 个工具...\n")
    
    for tool_name, module_path, class_name in tools_to_test:
        print(f"测试 {tool_name}...", end=" ")
        
        try:
            # 动态导入
            module = __import__(module_path, fromlist=[class_name])
            tool_class = getattr(module, class_name)
            
            # 测试工具
            success, message = test_tool_config(tool_name, tool_class)
            print(message)
            results.append((tool_name, success, message))
            
        except Exception as e:
            error_msg = f"✗ 导入失败: {str(e)[:80]}"
            print(error_msg)
            results.append((tool_name, False, error_msg))
    
    # 打印总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    
    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed
    
    print(f"\n总计: {len(results)} 个工具")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    
    if failed > 0:
        print(f"\n失败的工具:")
        for name, success, message in results:
            if not success:
                print(f"  {name}: {message}")
    
    print("\n" + "="*80)
    if failed == 0:
        print("✅ 所有工具配置测试通过！")
    else:
        print(f"❌ {failed} 个工具配置测试失败")
    print("="*80)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

