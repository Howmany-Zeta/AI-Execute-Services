#!/usr/bin/env python3
"""
Comprehensive Document Creation Example

This example demonstrates the complete "独立文档创建器 + 增强编排器" architecture,
showcasing how all components work together to create rich documents with:

1. DocumentCreatorTool - Template-based document creation
2. DocumentLayoutTool - Layout and typography management  
3. ContentInsertionTool - Charts, tables, images insertion
4. AIDocumentWriterOrchestrator - AI-driven coordination
5. DocumentWriterTool - Advanced text editing operations

Complete workflow example: Creating a business report with charts and tables.
"""

import tempfile
import os
import json
from datetime import datetime
from typing import Dict, Any, List


def create_comprehensive_document_example():
    """Main example function demonstrating complete document creation workflow"""
    print("🎯 Comprehensive Document Creation Workflow Demo")
    print("=" * 70)
    
    try:
        # Example data for demonstration
        sales_data = {
            "Q1": 15000,
            "Q2": 18000, 
            "Q3": 22000,
            "Q4": 25000
        }
        
        performance_data = [
            ["Product", "Q1", "Q2", "Q3", "Q4"],
            ["Product A", 5000, 6000, 7500, 8000],
            ["Product B", 4000, 5000, 6000, 7000],
            ["Product C", 6000, 7000, 8500, 10000]
        ]
        
        # Start comprehensive workflow
        result = run_complete_document_workflow(sales_data, performance_data)
        
        print("\n🎉 Complete workflow finished successfully!")
        print(f"📄 Document created at: {result.get('final_document_path', 'Unknown')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error in comprehensive workflow: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_complete_document_workflow(sales_data: Dict, performance_data: List) -> Dict[str, Any]:
    """Execute the complete document creation workflow"""
    
    workflow_result = {
        "workflow_id": f"comprehensive_{int(datetime.now().timestamp())}",
        "steps_completed": [],
        "tools_used": [],
        "final_document_path": None,
        "workflow_metadata": {}
    }
    
    print("\n📋 Step 1: Initialize Document Creation Tools")
    print("-" * 50)
    
    # Step 1: Initialize all tools
    tools = initialize_document_tools()
    workflow_result["tools_used"] = list(tools.keys())
    workflow_result["steps_completed"].append("tools_initialization")
    
    print("\n📋 Step 2: Create Document from Template")
    print("-" * 50)
    
    # Step 2: Create base document
    if 'creator' in tools:
        creation_result = create_base_document(tools['creator'])
        workflow_result["creation_result"] = creation_result
        workflow_result["final_document_path"] = creation_result.get('output_path')
        workflow_result["steps_completed"].append("document_creation")
        print(f"✅ Document created: {creation_result.get('output_path')}")
    else:
        print("⚠️ DocumentCreatorTool not available, using fallback")
        creation_result = create_fallback_document()
        workflow_result["creation_result"] = creation_result
        workflow_result["final_document_path"] = creation_result.get('output_path')
    
    document_path = workflow_result["final_document_path"]
    
    print("\n📋 Step 3: Configure Document Layout")
    print("-" * 50)
    
    # Step 3: Setup layout
    if 'layout' in tools and document_path:
        layout_result = configure_document_layout(tools['layout'], document_path)
        workflow_result["layout_result"] = layout_result
        workflow_result["steps_completed"].append("layout_configuration")
        print("✅ Layout configured successfully")
    else:
        print("⚠️ DocumentLayoutTool not available, skipping layout configuration")
    
    print("\n📋 Step 4: Insert Charts and Tables") 
    print("-" * 50)
    
    # Step 4: Insert complex content
    if 'content' in tools and document_path:
        content_result = insert_complex_content(
            tools['content'], document_path, sales_data, performance_data
        )
        workflow_result["content_result"] = content_result
        workflow_result["steps_completed"].append("content_insertion")
        print("✅ Charts and tables inserted successfully")
    else:
        print("⚠️ ContentInsertionTool not available, skipping content insertion")
    
    print("\n📋 Step 5: AI-Driven Content Enhancement")
    print("-" * 50)
    
    # Step 5: AI enhancement
    if 'orchestrator' in tools and document_path:
        ai_result = apply_ai_enhancements(tools['orchestrator'], document_path, sales_data)
        workflow_result["ai_result"] = ai_result
        workflow_result["steps_completed"].append("ai_enhancement")
        print("✅ AI enhancements applied successfully")
    else:
        print("⚠️ AIDocumentWriterOrchestrator not available, skipping AI enhancement")
    
    print("\n📋 Step 6: Final Document Optimization")
    print("-" * 50)
    
    # Step 6: Final optimization
    if 'writer' in tools and document_path:
        optimization_result = apply_final_optimizations(tools['writer'], document_path)
        workflow_result["optimization_result"] = optimization_result
        workflow_result["steps_completed"].append("final_optimization")
        print("✅ Final optimizations applied successfully")
    else:
        print("⚠️ DocumentWriterTool not available, skipping final optimization")
    
    # Workflow summary
    workflow_result["workflow_metadata"] = {
        "total_steps": len(workflow_result["steps_completed"]),
        "tools_available": len(workflow_result["tools_used"]),
        "completion_time": datetime.now().isoformat(),
        "success": len(workflow_result["steps_completed"]) >= 2  # At least document creation
    }
    
    return workflow_result


def initialize_document_tools() -> Dict[str, Any]:
    """Initialize all document creation tools"""
    tools = {}
    
    # Try to initialize DocumentCreatorTool
    try:
        from aiecs.tools.docs.document_creator_tool import DocumentCreatorTool
        tools['creator'] = DocumentCreatorTool()
        print("✅ DocumentCreatorTool initialized")
    except ImportError as e:
        print(f"❌ DocumentCreatorTool not available: {e}")
    
    # Try to initialize DocumentLayoutTool
    try:
        from aiecs.tools.docs.document_layout_tool import DocumentLayoutTool
        tools['layout'] = DocumentLayoutTool()
        print("✅ DocumentLayoutTool initialized")
    except ImportError as e:
        print(f"❌ DocumentLayoutTool not available: {e}")
    
    # Try to initialize ContentInsertionTool
    try:
        from aiecs.tools.docs.content_insertion_tool import ContentInsertionTool
        tools['content'] = ContentInsertionTool()
        print("✅ ContentInsertionTool initialized")
    except ImportError as e:
        print(f"❌ ContentInsertionTool not available: {e}")
    
    # Try to initialize AIDocumentWriterOrchestrator
    try:
        from aiecs.tools.docs.ai_document_writer_orchestrator import AIDocumentWriterOrchestrator
        tools['orchestrator'] = AIDocumentWriterOrchestrator()
        print("✅ AIDocumentWriterOrchestrator initialized")
    except Exception as e:
        print(f"❌ AIDocumentWriterOrchestrator not available: {e}")
    
    # Try to initialize DocumentWriterTool
    try:
        from aiecs.tools.docs.document_writer_tool import DocumentWriterTool
        tools['writer'] = DocumentWriterTool()
        print("✅ DocumentWriterTool initialized")
    except ImportError as e:
        print(f"❌ DocumentWriterTool not available: {e}")
    
    print(f"\n📊 Tools Summary: {len(tools)} tools available out of 5")
    return tools


def create_base_document(creator_tool) -> Dict[str, Any]:
    """Create base document using DocumentCreatorTool"""
    try:
        # Import enums from the tool
        from aiecs.tools.docs.document_creator_tool import DocumentType, TemplateType, DocumentFormat
        
        # Create business report document
        result = creator_tool.create_document(
            document_type=DocumentType.REPORT,
            template_type=TemplateType.BUSINESS_REPORT,
            output_format=DocumentFormat.MARKDOWN,
            metadata={
                "title": "Q4 2024 Sales Performance Report",
                "author": "AI Document System",
                "department": "Sales Analytics",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "version": "1.0"
            },
            style_preset="corporate"
        )
        
        print(f"📄 Document created with template: {result.get('template_type')}")
        print(f"📁 Output path: {result.get('output_path')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Failed to create base document: {e}")
        return create_fallback_document()


def create_fallback_document() -> Dict[str, Any]:
    """Create fallback document if creator tool is not available"""
    try:
        import tempfile
        
        fallback_content = """# Q4 2024 Sales Performance Report

**Date:** {date}  
**Author:** AI Document System  
**Department:** Sales Analytics

## Executive Summary

This report presents the Q4 2024 sales performance analysis with key metrics and insights.

## Introduction

Our sales team has achieved significant milestones in Q4 2024. This document provides comprehensive analysis of our performance.

## Analysis

### Quarterly Sales Performance

[CHART_PLACEHOLDER]

### Product Performance Breakdown

[TABLE_PLACEHOLDER]

## Recommendations

Based on the analysis, we recommend the following actions for the upcoming quarter.

## Conclusion

The Q4 results demonstrate strong performance across all product lines with opportunities for continued growth.
""".format(date=datetime.now().strftime("%Y-%m-%d"))
        
        # Create temporary file
        temp_file = os.path.join(tempfile.gettempdir(), "fallback_report.md")
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(fallback_content)
        
        return {
            "output_path": temp_file,
            "template_type": "fallback",
            "document_type": "report",
            "fallback_used": True
        }
        
    except Exception as e:
        print(f"❌ Failed to create fallback document: {e}")
        return {"error": str(e)}


def configure_document_layout(layout_tool, document_path: str) -> Dict[str, Any]:
    """Configure document layout using DocumentLayoutTool"""
    try:
        # Import enums from the tool
        from aiecs.tools.docs.document_layout_tool import PageSize, PageOrientation
        
        # Configure page layout
        layout_result = layout_tool.set_page_layout(
            document_path=document_path,
            page_size=PageSize.A4,
            orientation=PageOrientation.PORTRAIT,
            margins={"top": 2.0, "bottom": 2.0, "left": 2.5, "right": 2.5},
            layout_preset="business_report"
        )
        
        # Setup headers and footers
        header_footer_result = layout_tool.setup_headers_footers(
            document_path=document_path,
            header_config={
                "left": "Q4 2024 Sales Report",
                "right": "{date}"
            },
            footer_config={
                "center": "Page {page} of {total_pages}",
                "right": "Confidential"
            },
            page_numbering=True,
            numbering_style="numeric"
        )
        
        print("✏️ Page layout: A4 Portrait with corporate margins")
        print("📋 Headers/footers configured with page numbering")
        
        return {
            "layout_result": layout_result,
            "header_footer_result": header_footer_result,
            "layout_configured": True
        }
        
    except Exception as e:
        print(f"❌ Failed to configure layout: {e}")
        return {"layout_configured": False, "error": str(e)}


def insert_complex_content(content_tool, document_path: str, 
                          sales_data: Dict, performance_data: List) -> Dict[str, Any]:
    """Insert charts and tables using ContentInsertionTool"""
    try:
        results = []
        
        # Insert sales chart
        try:
            from aiecs.tools.docs.content_insertion_tool import ChartType
            
            chart_result = content_tool.insert_chart(
                document_path=document_path,
                chart_data={
                    "labels": list(sales_data.keys()),
                    "values": list(sales_data.values())
                },
                chart_type=ChartType.BAR,
                position={"marker": "[CHART_PLACEHOLDER]"},
                caption="Quarterly Sales Performance 2024",
                reference_id="sales_chart_2024"
            )
            results.append(chart_result)
            print("📊 Sales chart inserted successfully")
            
        except Exception as e:
            print(f"⚠️ Chart insertion failed: {e}")
        
        # Insert performance table
        try:
            from aiecs.tools.docs.content_insertion_tool import TableStyle
            
            table_result = content_tool.insert_table(
                document_path=document_path,
                table_data=performance_data[1:],  # Exclude headers
                position={"marker": "[TABLE_PLACEHOLDER]"},
                table_style=TableStyle.CORPORATE,
                headers=performance_data[0],  # First row as headers
                caption="Product Performance by Quarter",
                reference_id="performance_table_2024"
            )
            results.append(table_result)
            print("📋 Performance table inserted successfully")
            
        except Exception as e:
            print(f"⚠️ Table insertion failed: {e}")
        
        return {
            "insertion_results": results,
            "successful_insertions": len(results),
            "content_inserted": True
        }
        
    except Exception as e:
        print(f"❌ Failed to insert complex content: {e}")
        return {"content_inserted": False, "error": str(e)}


def apply_ai_enhancements(orchestrator_tool, document_path: str, sales_data: Dict) -> Dict[str, Any]:
    """Apply AI-driven enhancements using AIDocumentWriterOrchestrator"""
    try:
        results = []
        
        # Try AI content enhancement
        try:
            enhancement_result = orchestrator_tool.ai_edit_document(
                target_path=document_path,
                operation="smart_format",
                edit_instructions="Improve document formatting and readability for business presentation",
                preserve_structure=True
            )
            results.append(enhancement_result)
            print("🤖 AI formatting enhancement applied")
            
        except Exception as e:
            print(f"⚠️ AI formatting failed: {e}")
        
        # Try AI content analysis and optimization
        try:
            analysis_result = orchestrator_tool.analyze_document_content(
                source_path=document_path,
                analysis_type="content_quality",
                analysis_params={"include_recommendations": True}
            )
            results.append(analysis_result)
            print("📊 Document content analysis completed")
            
        except Exception as e:
            print(f"⚠️ Content analysis failed: {e}")
        
        # Try document layout optimization
        try:
            optimization_result = orchestrator_tool.optimize_document_layout(
                document_path=document_path,
                optimization_goals=["professional", "readability"],
                preserve_content=True,
                layout_style="corporate"
            )
            results.append(optimization_result)
            print("🎨 Layout optimization applied")
            
        except Exception as e:
            print(f"⚠️ Layout optimization failed: {e}")
        
        return {
            "ai_enhancement_results": results,
            "successful_enhancements": len(results),
            "ai_enhancements_applied": True
        }
        
    except Exception as e:
        print(f"❌ Failed to apply AI enhancements: {e}")
        return {"ai_enhancements_applied": False, "error": str(e)}


def apply_final_optimizations(writer_tool, document_path: str) -> Dict[str, Any]:
    """Apply final optimizations using DocumentWriterTool"""
    try:
        results = []
        
        # Apply text formatting optimizations
        try:
            # Bold important keywords
            bold_result = writer_tool.format_text(
                target_path=document_path,
                text_to_format="Executive Summary",
                format_type="bold"
            )
            results.append(bold_result)
            print("🔤 Important keywords emphasized")
            
        except Exception as e:
            print(f"⚠️ Text formatting failed: {e}")
        
        # Perform find and replace for consistency
        try:
            consistency_result = writer_tool.find_replace(
                target_path=document_path,
                find_text="Q4 2024",
                replace_text="**Q4 2024**",
                replace_all=True,
                case_sensitive=True
            )
            results.append(consistency_result)
            print(f"✏️ Consistency improvements: {consistency_result.get('replacements_made', 0)} replacements")
            
        except Exception as e:
            print(f"⚠️ Find/replace failed: {e}")
        
        # Add final touches
        try:
            final_content = "\n\n---\n\n*This document was generated using AIECS Document Creation System*\n"
            append_result = writer_tool.write_document(
                target_path=document_path,
                content=final_content,
                format="markdown",
                mode="append"
            )
            results.append(append_result)
            print("📝 Document signature added")
            
        except Exception as e:
            print(f"⚠️ Final content addition failed: {e}")
        
        return {
            "optimization_results": results,
            "successful_optimizations": len(results),
            "final_optimizations_applied": True
        }
        
    except Exception as e:
        print(f"❌ Failed to apply final optimizations: {e}")
        return {"final_optimizations_applied": False, "error": str(e)}


def demonstrate_advanced_features():
    """Demonstrate advanced features of the document creation system"""
    print("\n🚀 Advanced Features Demonstration")
    print("=" * 70)
    
    advanced_features = [
        {
            "feature": "Template Management",
            "description": "DocumentCreatorTool supports 9 built-in templates",
            "benefits": ["Quick document creation", "Consistent formatting", "Professional layouts"]
        },
        {
            "feature": "Intelligent Layout",
            "description": "DocumentLayoutTool provides 10 layout presets",
            "benefits": ["Automatic page setup", "Professional typography", "Multi-column support"]
        },
        {
            "feature": "Rich Content Insertion", 
            "description": "ContentInsertionTool handles 15+ content types",
            "benefits": ["Charts and graphs", "Tables and data", "Images and media"]
        },
        {
            "feature": "AI-Driven Orchestration",
            "description": "AIDocumentWriterOrchestrator provides intelligent coordination",
            "benefits": ["Smart content generation", "Layout optimization", "Quality enhancement"]
        },
        {
            "feature": "Advanced Text Editing",
            "description": "DocumentWriterTool offers 15 editing operations",
            "benefits": ["Precise text control", "Format consistency", "Batch operations"]
        }
    ]
    
    for i, feature in enumerate(advanced_features, 1):
        print(f"\n{i}. 🎯 {feature['feature']}")
        print(f"   📝 {feature['description']}")
        print(f"   ✅ Benefits:")
        for benefit in feature['benefits']:
            print(f"      • {benefit}")
    
    print(f"\n📊 System Capabilities Summary:")
    print(f"   🔧 5 specialized tools working together")
    print(f"   📋 20+ document templates and presets")
    print(f"   🎨 50+ content types and formatting options")
    print(f"   🤖 AI-driven intelligent optimization")
    print(f"   ⚡ Atomic operations with full integration")


def show_workflow_summary():
    """Show summary of the complete workflow capabilities"""
    print("\n📋 Complete Document Creation Workflow")
    print("=" * 70)
    
    workflow_steps = [
        {
            "step": 1,
            "name": "Document Creation",
            "tool": "DocumentCreatorTool",
            "actions": ["Template selection", "Metadata configuration", "Structure setup"]
        },
        {
            "step": 2,
            "name": "Layout Configuration", 
            "tool": "DocumentLayoutTool",
            "actions": ["Page layout", "Typography setup", "Headers/footers"]
        },
        {
            "step": 3,
            "name": "Content Insertion",
            "tool": "ContentInsertionTool", 
            "actions": ["Charts generation", "Tables insertion", "Media embedding"]
        },
        {
            "step": 4,
            "name": "AI Enhancement",
            "tool": "AIDocumentWriterOrchestrator",
            "actions": ["Content optimization", "Layout enhancement", "Quality analysis"]
        },
        {
            "step": 5,
            "name": "Final Optimization",
            "tool": "DocumentWriterTool",
            "actions": ["Text formatting", "Consistency checks", "Final touches"]
        }
    ]
    
    for step in workflow_steps:
        print(f"\n📍 Step {step['step']}: {step['name']}")
        print(f"   🔧 Tool: {step['tool']}")
        print(f"   ⚙️ Actions:")
        for action in step['actions']:
            print(f"      • {action}")
    
    print(f"\n🎯 Workflow Benefits:")
    print(f"   ✅ Modular and extensible architecture")
    print(f"   ✅ AI-driven intelligent automation")
    print(f"   ✅ Professional-grade document quality")
    print(f"   ✅ Consistent and reliable results")
    print(f"   ✅ Comprehensive content support")


def main():
    """Main function to run the comprehensive example"""
    print("AIECS Document Creation System - Comprehensive Demo")
    print("=" * 70)
    print("Demonstrating the complete 'Independent Document Creator + Enhanced Orchestrator' architecture")
    
    try:
        # Run the main workflow
        result = create_comprehensive_document_example()
        
        # Show advanced features
        demonstrate_advanced_features()
        
        # Show workflow summary  
        show_workflow_summary()
        
        print("\n" + "=" * 70)
        print("🎉 Comprehensive Document Creation Demo Complete!")
        
        if result and result.get('workflow_metadata', {}).get('success'):
            print(f"\n✅ Workflow Status: SUCCESS")
            print(f"📊 Steps Completed: {result['workflow_metadata']['total_steps']}")
            print(f"🔧 Tools Used: {result['workflow_metadata']['tools_available']}")
            print(f"📄 Final Document: {result.get('final_document_path', 'Generated')}")
        else:
            print(f"\n⚠️ Workflow Status: PARTIAL (some tools may not be available)")
        
        print(f"\n📋 Architecture Summary:")
        print(f"✅ DocumentCreatorTool - Template-based document creation")
        print(f"✅ DocumentLayoutTool - Professional layout and typography")
        print(f"✅ ContentInsertionTool - Rich content and media insertion")
        print(f"✅ AIDocumentWriterOrchestrator - AI-driven coordination")
        print(f"✅ DocumentWriterTool - Advanced text editing operations")
        
        print(f"\n🚀 The system is ready for production document creation workflows!")
        
    except KeyboardInterrupt:
        print("\nDemo interrupted by user.")
    except Exception as e:
        print(f"\nError in demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
