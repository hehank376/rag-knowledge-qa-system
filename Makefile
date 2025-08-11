# RAG Knowledge QA System Makefile

.PHONY: install test lint format clean dev

# 安装依赖
install:
	pip install -r requirements.txt

# 安装开发依赖
install-dev: install
	pip install -e .

# 运行测试
test:
	pytest tests/ -v --cov=rag_system

# 代码检查
lint:
	flake8 rag_system/
	mypy rag_system/

# 代码格式化
format:
	black rag_system/
	black tests/

# 清理缓存文件
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/

# 开发模式运行
dev:
	uvicorn rag_system.main:app --reload --host 0.0.0.0 --port 8000

# 构建包
build:
	python setup.py sdist bdist_wheel

# 帮助信息
help:
	@echo "Available commands:"
	@echo "  install     - Install dependencies"
	@echo "  install-dev - Install development dependencies"
	@echo "  test        - Run tests"
	@echo "  lint        - Run code linting"
	@echo "  format      - Format code"
	@echo "  clean       - Clean cache files"
	@echo "  dev         - Run in development mode"
	@echo "  build       - Build package"
	@echo "  help        - Show this help message"