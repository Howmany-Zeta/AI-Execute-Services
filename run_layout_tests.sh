#!/bin/bash
# DocumentLayoutTool 测试运行脚本
# 使用方法: ./run_layout_tests.sh [选项]
#
# 选项:
#   basic    - 基础测试运行
#   coverage - 带覆盖率报告
#   debug    - Debug模式
#   html     - 生成HTML报告

set -e

echo "=================================="
echo "DocumentLayoutTool 全面测试"
echo "=================================="
echo ""

cd "$(dirname "$0")"

case "${1:-basic}" in
    basic)
        echo "运行基础测试..."
        poetry run pytest test/test_document_layout_tool_comprehensive.py -v
        ;;
    
    coverage)
        echo "运行测试并生成覆盖率报告..."
        poetry run pytest test/test_document_layout_tool_comprehensive.py \
            --cov=. \
            --cov-report=term-missing:skip-covered \
            -v
        ;;
    
    debug)
        echo "运行Debug模式测试..."
        poetry run pytest test/test_document_layout_tool_comprehensive.py \
            -v \
            --log-cli-level=DEBUG \
            -s
        ;;
    
    html)
        echo "运行测试并生成HTML报告..."
        poetry run pytest test/test_document_layout_tool_comprehensive.py \
            --cov=. \
            --cov-report=html:test/htmlcov_layout \
            --cov-report=term \
            -v
        echo ""
        echo "HTML报告已生成: test/htmlcov_layout/index.html"
        ;;
    
    *)
        echo "错误: 未知选项 '$1'"
        echo ""
        echo "可用选项:"
        echo "  basic    - 基础测试运行"
        echo "  coverage - 带覆盖率报告"
        echo "  debug    - Debug模式"
        echo "  html     - 生成HTML报告"
        exit 1
        ;;
esac

echo ""
echo "测试完成！"

