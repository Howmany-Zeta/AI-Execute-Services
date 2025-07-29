#!/bin/bash

# Python Middleware 项目启动脚本
# 启动 Redis, Celery Workers, 和 FastAPI 服务器

set -e

echo "🚀 启动 Python Middleware 项目..."

# 检查是否在正确的目录
if [ ! -f "pyproject.toml" ]; then
    echo "❌ 错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Redis 是否运行
check_redis() {
    log_info "检查 Redis 连接..."
    if redis-cli ping > /dev/null 2>&1; then
        log_success "Redis 已运行"
        return 0
    else
        log_warning "Redis 未运行，尝试启动..."
        return 1
    fi
}

# 启动 Redis (如果需要)
start_redis() {
    if ! check_redis; then
        log_info "启动 Redis 服务器..."
        if command -v redis-server > /dev/null 2>&1; then
            redis-server --daemonize yes --port 6379
            sleep 2
            if check_redis; then
                log_success "Redis 启动成功"
            else
                log_error "Redis 启动失败"
                exit 1
            fi
        else
            log_error "Redis 未安装，请先安装 Redis"
            echo "Ubuntu/Debian: sudo apt-get install redis-server"
            echo "CentOS/RHEL: sudo yum install redis"
            echo "macOS: brew install redis"
            exit 1
        fi
    fi
}

# 启动 Celery Worker
start_celery_worker() {
    log_info "启动 Celery Worker..."

    # 快速任务队列 Worker
    poetry run celery -A app.tasks.worker.celery_app worker \
        --loglevel=info \
        --queues=fast_tasks \
        --concurrency=4 \
        --hostname=fast_worker@%h \
        --detach \
        --pidfile=/tmp/celery_fast_worker.pid \
        --logfile=/tmp/celery_fast_worker.log

    # 重型任务队列 Worker
    poetry run celery -A app.tasks.worker.celery_app worker \
        --loglevel=info \
        --queues=heavy_tasks \
        --concurrency=2 \
        --hostname=heavy_worker@%h \
        --detach \
        --pidfile=/tmp/celery_heavy_worker.pid \
        --logfile=/tmp/celery_heavy_worker.log

    log_success "Celery Workers 启动成功"
}

# 启动 Celery Beat (定时任务调度器)
start_celery_beat() {
    log_info "启动 Celery Beat..."
    poetry run celery -A app.tasks.worker.celery_app beat \
        --loglevel=info \
        --detach \
        --pidfile=/tmp/celery_beat.pid \
        --logfile=/tmp/celery_beat.log

    log_success "Celery Beat 启动成功"
}

# 启动 Celery Flower (监控界面)
start_celery_flower() {
    log_info "启动 Celery Flower 监控界面..."
    poetry run celery -A app.tasks.worker.celery_app flower \
        --port=5555 \
        --detach \
        --pidfile=/tmp/celery_flower.pid \
        --logfile=/tmp/celery_flower.log

    log_success "Celery Flower 启动成功 (http://localhost:5555)"
}

# 启动 FastAPI 服务器
start_fastapi_server() {
    log_info "启动 FastAPI 服务器..."
    poetry run uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --log-level info &

    FASTAPI_PID=$!
    echo $FASTAPI_PID > /tmp/fastapi.pid
    log_success "FastAPI 服务器启动成功 (http://localhost:8000)"
}

# 检查服务状态
check_services() {
    log_info "检查服务状态..."

    # 检查 Redis
    if check_redis; then
        log_success "✓ Redis 运行正常"
    else
        log_error "✗ Redis 未运行"
    fi

    # 检查 Celery Workers
    if [ -f "/tmp/celery_fast_worker.pid" ] && kill -0 $(cat /tmp/celery_fast_worker.pid) 2>/dev/null; then
        log_success "✓ Celery Fast Worker 运行正常"
    else
        log_error "✗ Celery Fast Worker 未运行"
    fi

    if [ -f "/tmp/celery_heavy_worker.pid" ] && kill -0 $(cat /tmp/celery_heavy_worker.pid) 2>/dev/null; then
        log_success "✓ Celery Heavy Worker 运行正常"
    else
        log_error "✗ Celery Heavy Worker 未运行"
    fi

    # 检查 Celery Beat
    if [ -f "/tmp/celery_beat.pid" ] && kill -0 $(cat /tmp/celery_beat.pid) 2>/dev/null; then
        log_success "✓ Celery Beat 运行正常"
    else
        log_error "✗ Celery Beat 未运行"
    fi

    # 检查 Celery Flower
    if [ -f "/tmp/celery_flower.pid" ] && kill -0 $(cat /tmp/celery_flower.pid) 2>/dev/null; then
        log_success "✓ Celery Flower 运行正常"
    else
        log_error "✗ Celery Flower 未运行"
    fi

    # 检查 FastAPI
    if [ -f "/tmp/fastapi.pid" ] && kill -0 $(cat /tmp/fastapi.pid) 2>/dev/null; then
        log_success "✓ FastAPI 服务器运行正常"
    else
        log_error "✗ FastAPI 服务器未运行"
    fi
}

# 主启动流程
main() {
    case "${1:-start}" in
        "start")
            log_info "开始启动所有服务..."
            start_redis
            start_celery_worker
            start_celery_beat
            start_celery_flower
            start_fastapi_server

            sleep 3
            check_services

            log_success "🎉 所有服务启动完成!"
            echo ""
            echo "服务访问地址:"
            echo "  - FastAPI 服务器: http://localhost:8000"
            echo "  - FastAPI 文档: http://localhost:8000/docs"
            echo "  - Celery Flower 监控: http://localhost:5555"
            echo "  - WebSocket 连接: ws://localhost:8000/socket.io"
            echo ""
            echo "日志文件位置:"
            echo "  - Celery Fast Worker: /tmp/celery_fast_worker.log"
            echo "  - Celery Heavy Worker: /tmp/celery_heavy_worker.log"
            echo "  - Celery Beat: /tmp/celery_beat.log"
            echo "  - Celery Flower: /tmp/celery_flower.log"
            ;;
        "status")
            check_services
            ;;
        "stop")
            log_info "停止所有服务..."

            # 停止 FastAPI
            if [ -f "/tmp/fastapi.pid" ]; then
                kill $(cat /tmp/fastapi.pid) 2>/dev/null || true
                rm -f /tmp/fastapi.pid
                log_success "FastAPI 服务器已停止"
            fi

            # 停止 Celery 服务
            for service in celery_fast_worker celery_heavy_worker celery_beat celery_flower; do
                if [ -f "/tmp/${service}.pid" ]; then
                    kill $(cat /tmp/${service}.pid) 2>/dev/null || true
                    rm -f /tmp/${service}.pid
                    log_success "${service} 已停止"
                fi
            done

            log_success "所有服务已停止"
            ;;
        "restart")
            $0 stop
            sleep 2
            $0 start
            ;;
        *)
            echo "用法: $0 {start|stop|restart|status}"
            echo ""
            echo "命令说明:"
            echo "  start   - 启动所有服务 (Redis, Celery, FastAPI)"
            echo "  stop    - 停止所有服务"
            echo "  restart - 重启所有服务"
            echo "  status  - 检查服务状态"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
