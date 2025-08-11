@echo off
REM Set permissions for RAG Knowledge QA System scripts

echo Setting permissions for deployment scripts...

REM Make scripts executable (Windows equivalent)
attrib -R scripts\*.sh
attrib -R scripts\*.bat

echo Permissions set successfully!
echo.
echo Available scripts:
echo   - deploy.sh [environment]     : Deploy the system
echo   - stop.sh [environment]       : Stop the system  
echo   - backup.sh [environment]     : Create backup
echo   - restore.sh backup.tar.gz    : Restore from backup
echo.
echo Usage examples:
echo   bash scripts/deploy.sh production
echo   bash scripts/stop.sh development
echo   bash scripts/backup.sh production
echo   bash scripts/restore.sh backups/rag_backup_20231201_120000.tar.gz

pause