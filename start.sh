#!/bin/bash

# MyHelper 启动脚本

set -e

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

# 检查Python环境
check_python() {
    log_info "检查Python环境..."
    
    if ! command -v python &> /dev/null; then
        log_error "Python未安装或未在PATH中"
        exit 1
    fi
    
    python_version=$(python --version 2>&1 | cut -d' ' -f2)
    log_success "Python版本: $python_version"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖包..."
    
    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txt文件不存在"
        exit 1
    fi
    
    # 检查是否需要安装依赖
    if ! python -c "import flask" &> /dev/null; then
        log_warning "检测到缺少依赖包，正在安装..."
        pip install -r requirements.txt
    fi
    
    log_success "依赖检查完成"
}

# 检查配置
check_config() {
    log_info "检查配置文件..."
    
    if [ ! -f "config/default.json" ]; then
        log_error "默认配置文件不存在，请运行: python -m app.utils.filesystem_setup"
        exit 1
    fi
    
    # 检查LLM配置
    api_key=$(python -c "import json; config=json.load(open('config/default.json')); print(config.get('llm', {}).get('api_key', ''))" 2>/dev/null || echo "")
    
    if [ -z "$api_key" ]; then
        log_warning "LLM API密钥未配置，某些功能可能无法使用"
        log_info "请在config/default.json中设置llm.api_key"
    else
        log_success "LLM配置检测完成"
    fi
}

# 检查数据目录
check_data_dirs() {
    log_info "检查数据目录..."
    
    if [ ! -d "data" ]; then
        log_info "创建数据目录..."
        python -m app.utils.filesystem_setup
    fi
    
    # 检查目录权限
    if [ ! -w "data" ]; then
        log_error "数据目录没有写权限"
        exit 1
    fi
    
    log_success "数据目录检查完成"
}

# 启动应用
start_app() {
    log_info "启动MyHelper..."
    
    # 设置环境变量
    export FLASK_ENV="${FLASK_ENV:-production}"
    export MYHELPER_CONFIG="${MYHELPER_CONFIG:-config/default.json}"
    
    log_info "环境: $FLASK_ENV"
    log_info "配置文件: $MYHELPER_CONFIG"
    
    # 启动应用
    python main.py
}

# 显示帮助信息
show_help() {
    echo "MyHelper 启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  start       启动服务 (默认)"
    echo "  check       只进行环境检查"
    echo "  setup       初始化文件系统"
    echo "  help        显示此帮助信息"
    echo ""
    echo "环境变量:"
    echo "  FLASK_ENV           Flask环境 (development/production)"
    echo "  MYHELPER_CONFIG     配置文件路径"
    echo ""
    echo "示例:"
    echo "  $0 start                    # 启动服务"
    echo "  FLASK_ENV=development $0    # 开发模式启动"
    echo "  $0 check                    # 只检查环境"
}

# 主函数
main() {
    log_info "MyHelper 启动脚本 v1.0.0"
    echo ""
    
    case "${1:-start}" in
        start)
            check_python
            check_dependencies
            check_config
            check_data_dirs
            echo ""
            start_app
            ;;
        check)
            check_python
            check_dependencies
            check_config
            check_data_dirs
            log_success "所有检查通过！"
            ;;
        setup)
            log_info "初始化文件系统..."
            python -m app.utils.filesystem_setup
            log_success "文件系统初始化完成"
            ;;
        help)
            show_help
            ;;
        *)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
}

# 错误处理
trap 'log_error "脚本执行失败！"; exit 1' ERR

# 运行主函数
main "$@"