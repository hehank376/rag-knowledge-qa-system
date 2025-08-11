# Document Processing Flow Integration Tests

This directory contains comprehensive integration tests for the RAG system's document processing pipeline, covering the complete flow from document upload to vectorization.

## Test Suites

### 1. Document Processing Flow Tests (`test_document_processing_flow.py`)
Tests the complete document processing workflow:
- **Complete Flow Testing**: End-to-end document processing from upload to vectorization
- **Format Support**: Testing different document formats (TXT, MD, PDF, DOCX)
- **Chunking Logic**: Verification of text splitting and chunking algorithms
- **Concurrent Processing**: Multi-document processing capabilities
- **Integration Verification**: Component interaction validation

### 2. Error Recovery Tests (`test_error_recovery.py`)
Tests error handling and recovery mechanisms:
- **Database Failures**: Connection loss and recovery scenarios
- **Service Failures**: Embedding service and vector store failures
- **Retry Mechanisms**: Exponential backoff and circuit breaker patterns
- **Rollback Operations**: Transaction rollback on partial failures
- **Resource Cleanup**: Memory and file cleanup on errors
- **Timeout Handling**: Operation timeout and cancellation

### 3. Performance and Load Tests (`test_performance_load.py`)
Tests system performance under various conditions:
- **Single Document Performance**: Processing time for different document sizes
- **Concurrent Load Testing**: Performance under concurrent processing
- **Memory Usage Analysis**: Memory consumption and leak detection
- **Database Performance**: CRUD operation performance metrics
- **Vector Operations**: Vector insertion and search performance
- **End-to-End Throughput**: Complete pipeline throughput measurement

## Running the Tests

### Prerequisites

1. **Install Dependencies**:
   ```bash
   pip install pytest pytest-asyncio psutil
   ```

2. **Environment Setup**:
   ```bash
   # Set environment variables
   export TESTING=true
   export LOG_LEVEL=INFO
   export DATABASE_URL=sqlite:///./test_rag_system.db
   ```

### Running All Tests

Use the integrated test runner:
```bash
python run_integration_tests.py
```

### Running Individual Test Suites

```bash
# Document processing flow tests
pytest test_document_processing_flow.py -v

# Error recovery tests
pytest test_error_recovery.py -v

# Performance and load tests
pytest test_performance_load.py -v -s
```

### Running Specific Test Categories

```bash
# Run only fast tests
pytest -m "not slow" -v

# Run only performance tests
pytest -m performance -v

# Run only error recovery tests
pytest -m error_recovery -v
```

### Advanced Test Options

```bash
# Run with detailed output
pytest -v -s --tb=long

# Run with coverage report
pytest --cov=rag_system --cov-report=html

# Run with profiling
pytest --profile

# Run specific test method
pytest test_document_processing_flow.py::TestDocumentProcessingFlow::test_complete_document_processing_flow -v
```

## Test Configuration

### Pytest Configuration (`pytest.ini`)
- Async test support enabled
- 5-minute timeout per test
- Detailed logging configuration
- Warning filters for clean output

### Environment Variables
- `TESTING=true`: Enables test mode
- `LOG_LEVEL=INFO`: Sets logging level
- `DATABASE_URL`: Test database connection
- `VECTOR_STORE_PATH`: Test vector store location

## Test Data

Tests automatically create temporary test documents:
- **Small documents** (1KB): Basic functionality testing
- **Medium documents** (10KB): Standard processing testing
- **Large documents** (100KB): Performance testing
- **Very large documents** (1MB): Stress testing

## Performance Benchmarks

### Expected Performance Metrics

| Document Size | Processing Time | Throughput |
|---------------|----------------|------------|
| Small (1KB)   | < 1 second     | > 10 docs/sec |
| Medium (10KB) | < 5 seconds    | > 2 docs/sec |
| Large (100KB) | < 15 seconds   | > 0.5 docs/sec |

### Memory Usage Limits
- **Peak memory growth**: < 500MB during processing
- **Net memory growth**: < 200MB after processing
- **Memory cleanup**: Proper garbage collection after errors

### Database Performance
- **Insert operations**: < 1 second average
- **Select operations**: < 1 second average
- **Update operations**: < 1 second average
- **Delete operations**: < 1 second average

## Error Scenarios Tested

### Database Errors
- Connection timeouts
- Transaction rollbacks
- Constraint violations
- Disk space issues

### Service Errors
- Embedding service unavailability
- Vector store connection failures
- API rate limiting
- Network timeouts

### Resource Errors
- Memory exhaustion
- Disk space limitations
- File permission issues
- Concurrent access conflicts

## Monitoring and Debugging

### Test Logs
Tests generate detailed logs in the following locations:
- Console output with timestamps
- Test-specific log files (if configured)
- Performance metrics output

### Debug Mode
Enable debug mode for detailed troubleshooting:
```bash
export LOG_LEVEL=DEBUG
pytest -v -s --tb=long
```

### Memory Profiling
Monitor memory usage during tests:
```bash
pytest --profile-memory test_performance_load.py
```

## Continuous Integration

### GitHub Actions Integration
```yaml
name: Integration Tests
on: [push, pull_request]
jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run integration tests
        run: python tests/integration/run_integration_tests.py
```

### Test Reports
Tests generate reports in multiple formats:
- JUnit XML for CI integration
- HTML coverage reports
- Performance metrics JSON
- Error logs and stack traces

## Troubleshooting

### Common Issues

1. **Database Connection Errors**:
   - Ensure test database is accessible
   - Check DATABASE_URL environment variable
   - Verify database permissions

2. **Memory Issues**:
   - Increase available memory for tests
   - Check for memory leaks in test code
   - Monitor system resources during tests

3. **Timeout Errors**:
   - Increase test timeout values
   - Check system performance
   - Verify network connectivity for external services

4. **File Permission Errors**:
   - Ensure write permissions in test directories
   - Check temporary file cleanup
   - Verify file system space

### Getting Help

For issues with integration tests:
1. Check the test logs for detailed error messages
2. Run tests with debug logging enabled
3. Verify all dependencies are installed correctly
4. Check system resources (memory, disk space)
5. Review the test configuration and environment variables

## Contributing

When adding new integration tests:
1. Follow the existing test structure and naming conventions
2. Add appropriate test markers for categorization
3. Include performance benchmarks for new functionality
4. Add error scenarios and recovery testing
5. Update this README with new test descriptions
6. Ensure tests are deterministic and can run in isolation