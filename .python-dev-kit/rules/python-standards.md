# Python Development Standards

## Code Style

### PEP 8 Compliance
- Follow PEP 8 style guide
- Use `black` for automatic formatting
- Maximum line length: 88 characters (black default)
- Use 4 spaces for indentation
- Use snake_case for variables and functions
- Use PascalCase for classes
- Use UPPER_CASE for constants

### Type Hints
- Use type hints for all function parameters and return values (PEP 484)
- Import from `typing` module for complex types
- Use `Optional[T]` for nullable types
- Use `Union[T1, T2]` for multiple possible types
- Use `List[T]`, `Dict[K, V]`, `Set[T]` for collections

### Docstrings
- Write docstrings for all public functions, classes, and modules
- Use Google style or NumPy style docstrings
- Include:
  - Brief description
  - Args/Parameters
  - Returns
  - Raises (if applicable)
  - Examples (if helpful)

## Architecture

### Separation of Concerns
- Keep modules focused and single-responsibility
- Separate business logic from presentation
- Use dependency injection for testability
- Follow SOLID principles

### Module Structure
```
project/
├── src/
│   ├── __init__.py
│   ├── core/              # Core business logic
│   ├── utils/             # Utility functions
│   ├── config/            # Configuration management
│   └── cli/               # CLI interface
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
├── setup.py or pyproject.toml
└── README.md
```

## Performance

### Optimization Guidelines
- Profile before optimizing
- Use built-in functions (implemented in C)
- Use list comprehensions instead of for loops
- Use generators for large datasets
- Choose appropriate data structures
- Consider caching for expensive operations

### Concurrency
- Use `asyncio` for I/O-bound operations
- Use `multiprocessing` for CPU-bound operations
- Be aware of GIL limitations with threads

## Security

### Input Validation
- Always validate user input
- Sanitize data from external sources
- Use parameterized queries for database operations
- Never trust user input

### Secrets Management
- Never hardcode secrets
- Use environment variables
- Use `.env` files with `python-dotenv`
- Add `.env` to `.gitignore`

## Testing

### Test Coverage
- Aim for >80% code coverage
- Write unit tests for all public functions
- Write integration tests for component interactions
- Test edge cases and error conditions

### Test Structure
- Use `pytest` as test framework
- Use fixtures for test setup/teardown
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)

## Error Handling

### Exception Handling
- Use specific exception types
- Provide helpful error messages
- Include context in error messages
- Log exceptions with stack traces
- Never silently catch all exceptions

### Custom Exceptions
- Create custom exception classes for domain-specific errors
- Inherit from appropriate built-in exceptions
- Provide clear error messages

## Logging

### Logging Best Practices
- Use Python's `logging` module
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Include timestamps and context
- Don't log sensitive data
- Use structured logging when possible

## Documentation

### Code Documentation
- Document complex algorithms
- Explain non-obvious code
- Add inline comments for tricky logic
- Keep comments up to date

### Project Documentation
- Maintain README with:
  - Project description
  - Installation instructions
  - Quick start guide
  - Usage examples
  - API reference link
  - Contributing guidelines
  - License information

## Dependencies

### Dependency Management
- Use `requirements.txt` or `pyproject.toml`
- Pin dependency versions for production
- Use virtual environments
- Regularly update dependencies
- Audit dependencies for vulnerabilities

## Best Practices Summary

1. **Readability**: Code is read more than written
2. **Simplicity**: Keep it simple
3. **Consistency**: Follow established patterns
4. **Testing**: Write tests for all code
5. **Documentation**: Document as you code
6. **Security**: Never trust user input
7. **Performance**: Profile before optimizing
8. **Error Handling**: Handle errors gracefully
9. **Logging**: Log appropriately
10. **Version Control**: Commit frequently with clear messages
