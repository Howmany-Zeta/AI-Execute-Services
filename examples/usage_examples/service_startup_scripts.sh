#!/bin/bash

# AIECS 独立服务启动脚本集合

echo "=================================================="
echo "AIECS 独立服务启动脚本"
echo "=================================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查服务状态
check_service() {
    local service_name=$1
    local check_command=$2
    
    echo -e "${BLUE}检查 $service_name...${NC}"
    if eval $check_command > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $service_name 运行中${NC}"
        return 0
    else
        echo -e "${RED}❌ $service_name 未运行${NC}"
        return 1
    fi
}

# 启动基础服务
start_infrastructure() {
    echo -e "${YELLOW}🔧 启动基础设施服务...${NC}"
    
    # 检查并启动 Redis
    if ! check_service "Redis" "redis-cli ping"; then
        echo "启动 Redis..."
        redis-server --daemonize yes --logfile /tmp/redis.log
        sleep 2
        check_service "Redis" "redis-cli ping"
    fi
    
    # 检查 PostgreSQL
    if ! check_service "PostgreSQL" "pg_isready -h localhost"; then
        echo -e "${YELLOW}请手动启动 PostgreSQL:${NC}"
        echo "  sudo systemctl start postgresql"
        echo "  或 sudo service postgresql start"
    fi
}

# 启动 AIECS 主服务
start_aiecs_main() {
    echo -e "${YELLOW}🚀 启动 AIECS 主服务...${NC}"
    
    # 检查配置
    if [[ -z "$OPENAI_API_KEY" && -z "$VERTEX_PROJECT_ID" && -z "$XAI_API_KEY" ]]; then
        echo -e "${RED}❌ 警告: 未配置任何 LLM 提供商${NC}"
        echo "请设置至少一个环境变量:"
        echo "  export OPENAI_API_KEY=your_key"
        echo "  export VERTEX_PROJECT_ID=your_project"
        echo "  export XAI_API_KEY=your_key"
    fi
    
    # 启动主服务
    echo "启动 AIECS 主服务在端口 8000..."
    aiecs &
    AIECS_PID=$!
    
    # 等待服务启动
    echo "等待服务启动..."
    sleep 5
    
    if check_service "AIECS Main" "curl -s http://localhost:8000/health"; then
        echo -e "${GREEN}🎉 AIECS 主服务启动成功！${NC}"
        echo "服务地址: http://localhost:8000"
        echo "API 文档: http://localhost:8000/docs"
    else
        echo -e "${RED}❌ AIECS 主服务启动失败${NC}"
        kill $AIECS_PID 2>/dev/null
        return 1
    fi
}

# 启动 Celery Worker
start_celery_worker() {
    echo -e "${YELLOW}⚡ 启动 Celery Worker...${NC}"
    
    celery -A aiecs.tasks.worker.celery_app worker \
           --loglevel=info \
           --concurrency=4 \
           --logfile=/tmp/celery_worker.log &
    WORKER_PID=$!
    
    sleep 3
    
    if ps -p $WORKER_PID > /dev/null; then
        echo -e "${GREEN}✅ Celery Worker 启动成功 (PID: $WORKER_PID)${NC}"
    else
        echo -e "${RED}❌ Celery Worker 启动失败${NC}"
    fi
}

# 启动 Celery Beat（定时任务）
start_celery_beat() {
    echo -e "${YELLOW}📅 启动 Celery Beat...${NC}"
    
    celery -A aiecs.tasks.worker.celery_app beat \
           --loglevel=info \
           --logfile=/tmp/celery_beat.log &
    BEAT_PID=$!
    
    sleep 3
    
    if ps -p $BEAT_PID > /dev/null; then
        echo -e "${GREEN}✅ Celery Beat 启动成功 (PID: $BEAT_PID)${NC}"
    else
        echo -e "${RED}❌ Celery Beat 启动失败${NC}"
    fi
}

# 启动 Flower 监控
start_flower() {
    echo -e "${YELLOW}🌸 启动 Flower 监控...${NC}"
    
    celery -A aiecs.tasks.worker.celery_app flower \
           --port=5555 \
           --logfile=/tmp/flower.log &
    FLOWER_PID=$!
    
    sleep 3
    
    if check_service "Flower" "curl -s http://localhost:5555"; then
        echo -e "${GREEN}✅ Flower 监控启动成功${NC}"
        echo "监控界面: http://localhost:5555"
    else
        echo -e "${RED}❌ Flower 启动失败${NC}"
        kill $FLOWER_PID 2>/dev/null
    fi
}

# 停止所有服务
stop_all_services() {
    echo -e "${YELLOW}🛑 停止所有 AIECS 服务...${NC}"
    
    # 查找并停止相关进程
    pkill -f "aiecs"
    pkill -f "celery.*aiecs"
    
    echo -e "${GREEN}✅ 所有服务已停止${NC}"
}

# 查看服务状态
check_all_services() {
    echo -e "${BLUE}📊 检查所有服务状态:${NC}"
    
    check_service "Redis" "redis-cli ping"
    check_service "PostgreSQL" "pg_isready -h localhost"
    check_service "AIECS Main" "curl -s http://localhost:8000/health"
    check_service "Flower" "curl -s http://localhost:5555"
    
    # 检查进程
    echo -e "${BLUE}📋 相关进程:${NC}"
    ps aux | grep -E "(aiecs|celery)" | grep -v grep || echo "  无相关进程运行"
}

# 完整启动流程
start_all() {
    echo -e "${GREEN}🚀 启动完整的 AIECS 服务栈...${NC}"
    
    start_infrastructure
    start_aiecs_main
    start_celery_worker
    start_celery_beat
    start_flower
    
    echo -e "\n${GREEN}🎉 AIECS 服务栈启动完成！${NC}"
    echo -e "\n📋 服务清单:"
    echo "  • AIECS API: http://localhost:8000"
    echo "  • API 文档: http://localhost:8000/docs"
    echo "  • Flower 监控: http://localhost:5555"
    echo "  • 健康检查: http://localhost:8000/health"
    echo -e "\n💡 停止服务: $0 stop"
}

# 主菜单
case "$1" in
    "start")
        start_all
        ;;
    "stop")
        stop_all_services
        ;;
    "status")
        check_all_services
        ;;
    "main")
        start_infrastructure
        start_aiecs_main
        ;;
    "worker")
        start_celery_worker
        ;;
    "beat") 
        start_celery_beat
        ;;
    "flower")
        start_flower
        ;;
    "infrastructure")
        start_infrastructure
        ;;
    *)
        echo "AIECS 服务管理脚本"
        echo ""
        echo "用法: $0 {start|stop|status|main|worker|beat|flower|infrastructure}"
        echo ""
        echo "命令说明:"
        echo "  start         - 启动完整的 AIECS 服务栈"
        echo "  stop          - 停止所有 AIECS 服务"
        echo "  status        - 检查所有服务状态"
        echo "  main          - 只启动 AIECS 主服务"
        echo "  worker        - 启动 Celery Worker"
        echo "  beat          - 启动 Celery Beat"
        echo "  flower        - 启动 Flower 监控"
        echo "  infrastructure- 启动基础设施(Redis等)"
        echo ""
        echo "示例:"
        echo "  $0 start      # 启动完整服务"
        echo "  $0 status     # 检查状态"
        echo "  $0 stop       # 停止服务"
        ;;
esac
