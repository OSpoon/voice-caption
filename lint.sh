#!/bin/bash

# Voice Caption Lint 检查和修复脚本
# 支持 mypy、flake8、black、isort 等工具

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PYTHON_FILES="modules/ webui.py"
MAX_LINE_LENGTH=79
EXCLUDE_DIRS=".venv,venv,__pycache__,.git,.pytest_cache,node_modules"

# 函数：打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 函数：检查工具是否安装
check_tool() {
    local tool=$1
    if ! command -v "$tool" &> /dev/null; then
        print_error "$tool 未安装，请先安装: pip install $tool"
        return 1
    fi
    return 0
}

# 函数：安装缺失的工具
install_tools() {
    print_info "检查并安装 lint 工具..."
    
    local tools=("black" "isort" "flake8" "mypy")
    local missing_tools=()
    
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        print_warning "缺失工具: ${missing_tools[*]}"
        print_info "正在安装缺失的工具..."
        pip install "${missing_tools[@]}"
    else
        print_success "所有 lint 工具已安装"
    fi
}

# 函数：代码格式化 (black)
format_code() {
    print_info "使用 black 格式化代码..."
    
    if check_tool "black"; then
        black --line-length $MAX_LINE_LENGTH --exclude "$EXCLUDE_DIRS" $PYTHON_FILES
        if [ $? -eq 0 ]; then
            print_success "代码格式化完成"
        else
            print_error "代码格式化失败"
            return 1
        fi
    fi
}

# 函数：导入排序 (isort)
sort_imports() {
    print_info "使用 isort 排序导入..."
    
    if check_tool "isort"; then
        isort --profile black --line-length $MAX_LINE_LENGTH --skip-glob "$EXCLUDE_DIRS" $PYTHON_FILES
        if [ $? -eq 0 ]; then
            print_success "导入排序完成"
        else
            print_error "导入排序失败"
            return 1
        fi
    fi
}

# 函数：flake8 检查
check_flake8() {
    print_info "使用 flake8 检查代码风格..."
    
    if check_tool "flake8"; then
        flake8 --max-line-length=$MAX_LINE_LENGTH \
               --exclude="$EXCLUDE_DIRS" \
               --ignore=E203,W503,E501 \
               --statistics \
               $PYTHON_FILES
        
        local exit_code=$?
        if [ $exit_code -eq 0 ]; then
            print_success "flake8 检查通过"
        else
            print_warning "flake8 发现了一些问题"
            return $exit_code
        fi
    fi
}

# 函数：mypy 类型检查
check_mypy() {
    print_info "使用 mypy 进行类型检查..."
    
    if check_tool "mypy"; then
        mypy --ignore-missing-imports \
             --no-strict-optional \
             --allow-untyped-defs \
             --exclude="$EXCLUDE_DIRS" \
             $PYTHON_FILES
        
        local exit_code=$?
        if [ $exit_code -eq 0 ]; then
            print_success "mypy 类型检查通过"
        else
            print_warning "mypy 发现了一些类型问题"
            return $exit_code
        fi
    fi
}

# 函数：生成 lint 报告
generate_report() {
    local report_file="lint_report.txt"
    print_info "生成 lint 报告: $report_file"
    
    {
        echo "Voice Caption Lint 报告"
        echo "生成时间: $(date)"
        echo "="*50
        echo
        
        echo "flake8 检查结果:"
        flake8 --max-line-length=$MAX_LINE_LENGTH \
               --exclude="$EXCLUDE_DIRS" \
               --statistics \
               $PYTHON_FILES 2>&1 || true
        echo
        
        echo "mypy 检查结果:"
        mypy --ignore-missing-imports \
             --no-strict-optional \
             --allow-untyped-defs \
             --exclude="$EXCLUDE_DIRS" \
             $PYTHON_FILES 2>&1 || true
        echo
        
    } > "$report_file"
    
    print_success "报告已生成: $report_file"
}

# 函数：显示帮助信息
show_help() {
    echo "Voice Caption Lint 工具"
    echo
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  -i, --install  安装缺失的 lint 工具"
    echo "  -f, --format   格式化代码 (black + isort)"
    echo "  -c, --check    检查代码 (flake8 + mypy)"
    echo "  -a, --all      执行所有操作 (格式化 + 检查)"
    echo "  -r, --report   生成详细报告"
    echo "  --fix          尝试自动修复问题"
    echo
    echo "示例:"
    echo "  $0 --all       # 格式化并检查代码"
    echo "  $0 --format    # 仅格式化代码"
    echo "  $0 --check     # 仅检查代码"
    echo "  $0 --report    # 生成详细报告"
}

# 函数：自动修复
auto_fix() {
    print_info "尝试自动修复代码问题..."
    
    # 1. 格式化代码
    format_code
    
    # 2. 排序导入
    sort_imports
    
    # 3. 使用 autopep8 修复 PEP8 问题
    if command -v "autopep8" &> /dev/null; then
        print_info "使用 autopep8 修复 PEP8 问题..."
        autopep8 --in-place --aggressive --aggressive \
                 --max-line-length=$MAX_LINE_LENGTH \
                 --recursive $PYTHON_FILES
        print_success "autopep8 修复完成"
    else
        print_warning "autopep8 未安装，跳过自动修复"
    fi
    
    print_success "自动修复完成"
}

# 主函数
main() {
    local format_only=false
    local check_only=false
    local install_only=false
    local generate_report_only=false
    local auto_fix_only=false
    local run_all=false
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -i|--install)
                install_only=true
                shift
                ;;
            -f|--format)
                format_only=true
                shift
                ;;
            -c|--check)
                check_only=true
                shift
                ;;
            -a|--all)
                run_all=true
                shift
                ;;
            -r|--report)
                generate_report_only=true
                shift
                ;;
            --fix)
                auto_fix_only=true
                shift
                ;;
            *)
                print_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 如果没有指定参数，显示帮助
    if [ $# -eq 0 ] && [ "$format_only" = false ] && [ "$check_only" = false ] && \
       [ "$install_only" = false ] && [ "$generate_report_only" = false ] && \
       [ "$auto_fix_only" = false ] && [ "$run_all" = false ]; then
        show_help
        exit 0
    fi
    
    print_info "Voice Caption Lint 工具启动"
    print_info "检查目录: $PYTHON_FILES"
    print_info "最大行长度: $MAX_LINE_LENGTH"
    echo
    
    # 执行相应操作
    local exit_code=0
    
    if [ "$install_only" = true ]; then
        install_tools
    elif [ "$format_only" = true ]; then
        format_code
        sort_imports
    elif [ "$check_only" = true ]; then
        check_flake8 || exit_code=$?
        check_mypy || exit_code=$?
    elif [ "$generate_report_only" = true ]; then
        generate_report
    elif [ "$auto_fix_only" = true ]; then
        auto_fix
    elif [ "$run_all" = true ]; then
        # 格式化
        format_code
        sort_imports
        
        # 检查
        check_flake8 || exit_code=$?
        check_mypy || exit_code=$?
    fi
    
    echo
    if [ $exit_code -eq 0 ]; then
        print_success "所有操作完成！"
    else
        print_warning "完成，但发现了一些问题 (退出码: $exit_code)"
    fi
    
    exit $exit_code
}

# 运行主函数
main "$@"