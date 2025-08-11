#!/usr/bin/env python3
"""
Integration Test Runner
Runs all document processing flow integration tests
"""

import sys
import os
import asyncio
import subprocess
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def run_test_suite(test_file, description):
    """Run a specific test suite"""
    print(f"\n{'='*60}")
    print(f"Running {description}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    # Run pytest with verbose output
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        str(test_file),
        "-v", "-s", "--tb=short",
        "--disable-warnings"
    ], capture_output=False)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n{description} completed in {duration:.2f} seconds")
    
    if result.returncode == 0:
        print(f"✅ {description} PASSED")
    else:
        print(f"❌ {description} FAILED")
    
    return result.returncode == 0

def run_all_integration_tests():
    """Run all integration tests"""
    print("🚀 Starting Document Processing Flow Integration Tests")
    print(f"Project root: {project_root}")
    
    # Test suites to run
    test_suites = [
        {
            'file': 'test_document_processing_flow.py',
            'description': 'Document Processing Flow Tests'
        },
        {
            'file': 'test_error_recovery.py',
            'description': 'Error Recovery and Exception Handling Tests'
        },
        {
            'file': 'test_performance_load.py',
            'description': 'Performance and Load Tests'
        }
    ]
    
    # Results tracking
    results = {}
    total_start_time = time.time()
    
    # Run each test suite
    for suite in test_suites:
        test_file = Path(__file__).parent / suite['file']
        
        if not test_file.exists():
            print(f"⚠️  Test file not found: {test_file}")
            results[suite['description']] = False
            continue
        
        success = run_test_suite(test_file, suite['description'])
        results[suite['description']] = success
    
    # Summary
    total_duration = time.time() - total_start_time
    
    print(f"\n{'='*60}")
    print("INTEGRATION TEST SUMMARY")
    print(f"{'='*60}")
    
    passed_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    for description, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{description}: {status}")
    
    print(f"\nOverall Results: {passed_count}/{total_count} test suites passed")
    print(f"Total execution time: {total_duration:.2f} seconds")
    
    if passed_count == total_count:
        print("\n🎉 All integration tests passed!")
        return True
    else:
        print(f"\n💥 {total_count - passed_count} test suite(s) failed!")
        return False

def setup_test_environment():
    """Setup test environment"""
    print("🔧 Setting up test environment...")
    
    # Create necessary directories
    test_dirs = [
        project_root / "tests" / "integration",
        project_root / "logs",
        project_root / "data" / "uploads",
        project_root / "data" / "chroma_db"
    ]
    
    for directory in test_dirs:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")
    
    # Set environment variables for testing
    os.environ['TESTING'] = 'true'
    os.environ['LOG_LEVEL'] = 'INFO'
    os.environ['DATABASE_URL'] = 'sqlite:///./test_rag_system.db'
    
    print("✓ Environment variables set")
    print("✓ Test environment ready")

def cleanup_test_environment():
    """Cleanup test environment"""
    print("\n🧹 Cleaning up test environment...")
    
    # Remove test database
    test_db_path = project_root / "test_rag_system.db"
    if test_db_path.exists():
        test_db_path.unlink()
        print("✓ Removed test database")
    
    # Clean up test uploads
    uploads_dir = project_root / "data" / "uploads"
    if uploads_dir.exists():
        import shutil
        for item in uploads_dir.iterdir():
            if item.is_file() and item.name.startswith(('test_', 'perf_', 'concurrent_')):
                item.unlink()
        print("✓ Cleaned up test files")
    
    print("✓ Cleanup completed")

def check_dependencies():
    """Check if required dependencies are available"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'pytest',
        'asyncio',
        'psutil',
        'sqlalchemy',
        'fastapi'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Please install missing packages before running tests")
        return False
    
    print("✓ All dependencies available")
    return True

def main():
    """Main test runner"""
    print("🧪 RAG System Integration Test Runner")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Setup test environment
    setup_test_environment()
    
    try:
        # Run all integration tests
        success = run_all_integration_tests()
        
        if success:
            print("\n🎊 All integration tests completed successfully!")
            exit_code = 0
        else:
            print("\n💔 Some integration tests failed!")
            exit_code = 1
    
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        exit_code = 130
    
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        exit_code = 1
    
    finally:
        # Cleanup
        cleanup_test_environment()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()