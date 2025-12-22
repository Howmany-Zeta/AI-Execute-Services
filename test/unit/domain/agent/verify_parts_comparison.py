#!/usr/bin/env python3
"""
验证脚本：比较 Vertex AI multi-part response 中两个 parts 的内容
分析 line 724 (Candidate) 和 line 767 (Response) 的差异
"""

import json
import re
from typing import Dict, List, Any, Tuple

def extract_parts_from_log(log_file_path: str) -> Tuple[Dict, Dict]:
    """
    从日志文件中提取 Candidate 和 Response 的 parts 内容
    """
    with open(log_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 查找 Candidate 部分 (line 724 附近)
    candidate_start = None
    candidate_end = None
    for i, line in enumerate(lines):
        if "Candidate:" in line and i > 720:  # line 724 附近
            candidate_start = i
            break
    
    if candidate_start is None:
        raise ValueError("未找到 Candidate 部分")
    
    # 查找 Candidate 结束位置
    for i in range(candidate_start + 1, len(lines)):
        if "Response:" in lines[i]:
            candidate_end = i
            break
    
    if candidate_end is None:
        raise ValueError("未找到 Candidate 结束位置")
    
    # 提取 Candidate JSON
    candidate_lines = lines[candidate_start:candidate_end]
    candidate_text = ''.join(candidate_lines).replace("Candidate:", "").strip()
    candidate_data = json.loads(candidate_text)
    
    # 查找 Response 部分 (line 767 附近)
    response_start = None
    for i, line in enumerate(lines):
        if "Response:" in line and i > 760:  # line 767 附近
            response_start = i
            break
    
    if response_start is None:
        raise ValueError("未找到 Response 部分")
    
    # 提取 Response JSON (从 Response: 开始到文件结束或下一个主要部分)
    response_lines = lines[response_start:]
    response_text = ''.join(response_lines).replace("Response:", "").strip()
    
    # 找到第一个完整的 JSON 对象
    brace_count = 0
    response_json_end = 0
    for i, char in enumerate(response_text):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                response_json_end = i + 1
                break
    
    if response_json_end == 0:
        raise ValueError("未找到完整的 Response JSON")
    
    response_json = response_text[:response_json_end]
    response_data = json.loads(response_json)
    
    return candidate_data, response_data

def compare_parts(candidate_data: Dict, response_data: Dict) -> Dict[str, Any]:
    """
    比较两个 parts 的内容
    """
    result = {
        "comparison_summary": {},
        "detailed_analysis": {},
        "differences": [],
        "similarities": []
    }
    
    # 提取 parts
    candidate_parts = candidate_data.get("content", {}).get("parts", [])
    response_parts = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    
    result["comparison_summary"] = {
        "candidate_parts_count": len(candidate_parts),
        "response_parts_count": len(response_parts),
        "parts_match": len(candidate_parts) == len(response_parts)
    }
    
    # 详细比较每个 part
    for i, (candidate_part, response_part) in enumerate(zip(candidate_parts, response_parts)):
        part_analysis = {
            "part_index": i,
            "candidate_text": candidate_part.get("text", ""),
            "response_text": response_part.get("text", ""),
            "text_length_match": len(candidate_part.get("text", "")) == len(response_part.get("text", "")),
            "text_identical": candidate_part.get("text", "") == response_part.get("text", ""),
            "has_thinking_tags": "<thinking>" in candidate_part.get("text", ""),
            "thinking_tag_complete": _check_thinking_tag_completeness(candidate_part.get("text", ""))
        }
        
        result["detailed_analysis"][f"part_{i}"] = part_analysis
        
        # 检查差异
        if not part_analysis["text_identical"]:
            result["differences"].append({
                "part_index": i,
                "difference_type": "content_mismatch",
                "candidate_length": len(candidate_part.get("text", "")),
                "response_length": len(response_part.get("text", ""))
            })
        else:
            result["similarities"].append({
                "part_index": i,
                "similarity_type": "identical_content"
            })
    
    return result

def _check_thinking_tag_completeness(text: str) -> Dict[str, Any]:
    """
    检查 <thinking> 标签的完整性
    """
    analysis = {
        "has_opening_tag": "<thinking>" in text,
        "has_closing_tag": "</thinking>" in text,
        "is_complete": False,
        "opening_count": text.count("<thinking>"),
        "closing_count": text.count("</thinking>"),
        "tag_balanced": False
    }
    
    if analysis["has_opening_tag"] and analysis["has_closing_tag"]:
        analysis["is_complete"] = True
        analysis["tag_balanced"] = analysis["opening_count"] == analysis["closing_count"]
    
    return analysis

def analyze_thinking_tags(text: str) -> Dict[str, Any]:
    """
    分析 thinking 标签的详细情况
    """
    analysis = {
        "thinking_content": "",
        "non_thinking_content": "",
        "tag_structure": {},
        "issues": []
    }
    
    # 提取 thinking 内容
    thinking_match = re.search(r'<thinking>(.*?)</thinking>', text, re.DOTALL)
    if thinking_match:
        analysis["thinking_content"] = thinking_match.group(1).strip()
        analysis["tag_structure"]["has_complete_tags"] = True
    else:
        # 检查是否有不完整的标签
        if "<thinking>" in text and "</thinking>" not in text:
            analysis["issues"].append("incomplete_thinking_tag")
            analysis["tag_structure"]["has_opening_only"] = True
        elif "</thinking>" in text and "<thinking>" not in text:
            analysis["issues"].append("orphaned_closing_tag")
            analysis["tag_structure"]["has_closing_only"] = True
    
    # 提取非 thinking 内容
    if analysis["thinking_content"]:
        analysis["non_thinking_content"] = text.replace(f"<thinking>{analysis['thinking_content']}</thinking>", "").strip()
    else:
        analysis["non_thinking_content"] = text
    
    return analysis

def generate_verification_report(log_file_path: str) -> str:
    """
    生成完整的验证报告
    """
    try:
        # 提取数据
        candidate_data, response_data = extract_parts_from_log(log_file_path)
        
        # 比较 parts
        comparison_result = compare_parts(candidate_data, response_data)
        
        # 分析 thinking 标签
        thinking_analysis = {}
        for i, part in enumerate(candidate_data.get("content", {}).get("parts", [])):
            text = part.get("text", "")
            thinking_analysis[f"part_{i}"] = analyze_thinking_tags(text)
        
        # 生成报告
        report = f"""
# Vertex AI Multi-Part Response 验证报告

## 📊 基本信息
- **Candidate Parts 数量**: {comparison_result['comparison_summary']['candidate_parts_count']}
- **Response Parts 数量**: {comparison_result['comparison_summary']['response_parts_count']}
- **Parts 数量匹配**: {'✅' if comparison_result['comparison_summary']['parts_match'] else '❌'}

## 🔍 详细分析

### Parts 内容比较
"""
        
        for part_key, analysis in comparison_result["detailed_analysis"].items():
            report += f"""
#### {part_key.upper()}
- **内容长度匹配**: {'✅' if analysis['text_length_match'] else '❌'}
- **内容完全相同**: {'✅' if analysis['text_identical'] else '❌'}
- **包含 thinking 标签**: {'✅' if analysis['has_thinking_tags'] else '❌'}
- **thinking 标签完整**: {'✅' if analysis['thinking_tag_complete']['is_complete'] else '❌'}
"""
            
            if analysis['has_thinking_tags']:
                tag_analysis = analysis['thinking_tag_complete']
                report += f"""
**Thinking 标签分析**:
- 开始标签数量: {tag_analysis['opening_count']}
- 结束标签数量: {tag_analysis['closing_count']}
- 标签平衡: {'✅' if tag_analysis['tag_balanced'] else '❌'}
"""
        
        # 添加差异总结
        if comparison_result["differences"]:
            report += f"""
## ⚠️ 发现的差异
"""
            for diff in comparison_result["differences"]:
                report += f"- Part {diff['part_index']}: {diff['difference_type']}\n"
        else:
            report += """
## ✅ 未发现差异
所有 parts 内容完全匹配
"""
        
        # 添加 thinking 标签分析
        report += """
## 🏷️ Thinking 标签详细分析
"""
        for part_key, analysis in thinking_analysis.items():
            report += f"""
### {part_key.upper()}
- **Thinking 内容长度**: {len(analysis['thinking_content'])} 字符
- **非 Thinking 内容长度**: {len(analysis['non_thinking_content'])} 字符
- **标签结构**: {analysis['tag_structure']}
"""
            if analysis['issues']:
                report += f"- **发现的问题**: {', '.join(analysis['issues'])}\n"
        
        return report
        
    except Exception as e:
        return f"验证过程中发生错误: {str(e)}"

def main():
    """
    主函数
    """
    log_file_path = "/home/coder1/python-middleware-dev/test_debug_output.log"
    
    print("🔍 开始验证 Vertex AI Multi-Part Response...")
    print("=" * 80)
    
    try:
        report = generate_verification_report(log_file_path)
        print(report)
        
        # 保存报告到文件
        with open("/home/coder1/python-middleware-dev/parts_verification_report.md", "w", encoding="utf-8") as f:
            f.write(report)
        
        print("\n📄 验证报告已保存到: parts_verification_report.md")
        
    except Exception as e:
        print(f"❌ 验证失败: {str(e)}")

if __name__ == "__main__":
    main()
