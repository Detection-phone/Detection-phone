# Development Rules

## Basic Rules
1. Always use English in comments and documentation
2. Maintain consistent code structure
3. Document code changes
4. Test changes before implementation

## Project Structure
- `app.py` - main Flask application
- `config.py` - configuration and database models
- `phone_detector.py` - phone detection logic
- `templates/` - HTML files
- `static/` - static files (CSS, JS, images)
- `instance/` - configuration files
- `detections/` - detection storage

## Naming Conventions
- Python files: snake_case (e.g., `phone_detector.py`)
- Classes: PascalCase (e.g., `PhoneDetector`)
- Functions: snake_case (e.g., `detect_phone`)
- Variables: snake_case (e.g., `detection_count`)

## Code Organization
1. Each file should have a clear purpose
2. Keep related functionality together
3. Use meaningful file and folder names
4. Maintain a logical directory structure

## Security Rules
1. Never store sensitive data in code (passwords, API keys)
2. Use environment variables for sensitive data
3. Regularly update dependencies
4. Check code for vulnerabilities

## Testing Rules
1. Test new features before implementation
2. Maintain unit tests
3. Check functionality on different operating systems
4. Document found bugs

## Documentation Rules
1. Document all new functions
2. Update documentation for significant changes
3. Use docstrings in Python code
4. Maintain current API documentation

## Notification Handling Rules
1. Message Formatting:
   - Use templates from `templates/notifications/`
   - Maintain consistent message style
   - Shorten links in SMS messages

2. Error Handling:
   - Log all sending errors
   - Implement retry mechanism
   - Notify about critical errors
   - Keep message backups

3. Security:
   - Encrypt sensitive data
   - Use access tokens
   - Rotate API keys
   - Monitor usage limits

## Google Drive Integration Rules
1. File Structure:
   - Maintain folder hierarchy
   - Use timestamps in filenames
   - Generate metadata for each file
   - Implement cleanup mechanism

2. Permission Management:
   - Use service account
   - Restrict folder access
   - Regularly verify permissions
   - Log file operations

3. Optimization:
   - Compress images before upload
   - Use asynchronous uploading
   - Implement task queuing
   - Monitor space usage

4. Error Handling:
   - Implement retry mechanism
   - Log synchronization errors
   - Keep local backups
   - Notify about issues

## Notification Testing Rules
1. Unit Tests:
   - Test each notification type
   - Verify message formats
   - Check error handling
   - Test limits and restrictions

2. Integration Tests:
   - Verify data flow
   - Test queuing
   - Check synchronization
   - Verify priorities

3. Performance Tests:
   - Measure sending time
   - Check load
   - Test under load
   - Monitor resources

4. Security Tests:
   - Verify encryption
   - Test authorization
   - Check limits
   - Verify logs 