# Code Review Checklist

## Functionality

- [ ] Requirements met
- [ ] Edge cases handled
- [ ] Error handling complete
- [ ] Business logic correct
- [ ] All features implemented

## Code Quality

- [ ] Follows PEP 8
- [ ] Type hints present
- [ ] Docstrings complete
- [ ] No code duplication
- [ ] Meaningful variable names
- [ ] Functions are focused (< 50 lines)
- [ ] Cyclomatic complexity < 10

## Security

- [ ] Input validation
- [ ] Output encoding
- [ ] No hardcoded secrets
- [ ] SQL injection prevention
- [ ] XSS protection
- [ ] CSRF tokens
- [ ] Secure dependencies

## Performance

- [ ] Efficient algorithms
- [ ] Appropriate data structures
- [ ] No obvious bottlenecks
- [ ] Caching where beneficial
- [ ] Database queries optimized
- [ ] No N+1 queries

## Testing

- [ ] Unit tests cover logic
- [ ] Integration tests present
- [ ] Edge cases tested
- [ ] Error conditions tested
- [ ] Tests are isolated
- [ ] Tests are fast

## Documentation

- [ ] README updated
- [ ] API docs complete
- [ ] Code comments clear
- [ ] Examples provided
- [ ] Changelog updated

## Best Practices

- [ ] Follows project conventions
- [ ] Uses standard library when possible
- [ ] Error messages helpful
- [ ] Logging appropriate
- [ ] No debug prints
- [ ] No commented-out code

## Review Process

1. **Initial Review**
   - Read through the code
   - Understand the changes
   - Identify major issues

2. **Detailed Review**
   - Go through checklist
   - Test the changes
   - Ask questions

3. **Feedback**
   - Provide constructive feedback
   - Suggest improvements
   - Explain reasoning

4. **Follow-up**
   - Verify fixes
   - Re-test if needed
   - Approve when ready

## Common Issues to Look For

1. **Code Smells**
   - Long functions
   - Deep nesting
   - Magic numbers
   - Dead code

2. **Anti-patterns**
   - God objects
   - Spaghetti code
   - Copy-paste programming

3. **Security Issues**
   - SQL injection
   - XSS vulnerabilities
   - Hardcoded secrets
   - Insecure random

4. **Performance Issues**
   - Inefficient algorithms
   - Unnecessary database queries
   - Memory leaks
   - Blocking I/O

## Approval Criteria

- All critical issues resolved
- All major issues addressed or documented
- Tests pass
- Code follows standards
- Documentation complete
- No security vulnerabilities
