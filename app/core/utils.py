# core/utils.py
"""
Core utility functions shared across the application
"""

import os
import logging
from datetime import datetime, timedelta
from werkzeug.exceptions import BadRequest, Forbidden

logger = logging.getLogger('core')

# Constants
ANALYSIS_BASE_PATHS = {
    'wgs': '/bacteria',
    'species': '/animalSpecies'
}

SUPPORTED_REPORT_EXTENSIONS = ('.html', '.pdf', '.txt', '.csv', '.json')
MAX_LOG_SIZE = 1024 * 1024  # 1MB
MAX_RECURSIVE_DEPTH = 5


class ApplicationError(Exception):
    """Base exception for application errors"""
    pass


def validate_path(path, analysis_type=None):
    """
    Validate and sanitize file paths with analysis-specific base paths
    
    Args:
        path: Path to validate
        analysis_type: Type of analysis (wgs, species, etc.)
        
    Returns:
        Validated absolute path
        
    Raises:
        BadRequest: If path is empty
        Forbidden: If path is outside allowed base path
    """
    if not path:
        raise BadRequest("Pfad ist leer")
    
    # Determine appropriate base path
    if analysis_type and analysis_type in ANALYSIS_BASE_PATHS:
        base_path = ANALYSIS_BASE_PATHS[analysis_type]
    else:
        # Default fallback or try to determine from path
        base_path = None
        for atype, apath in ANALYSIS_BASE_PATHS.items():
            if path.startswith(apath):
                base_path = apath
                break
        
        if not base_path:
            # Default to first available base path
            base_path = list(ANALYSIS_BASE_PATHS.values())[0]
    
    # Resolve path and check if it's within base_path
    resolved_path = os.path.abspath(path)
    base_resolved = os.path.abspath(base_path)
    
    if not resolved_path.startswith(base_resolved):
        raise Forbidden("Zugriff außerhalb des erlaubten Bereichs")
    
    return resolved_path


def generate_job_code(job_type, job_count_today):
    """
    Generate a human-readable job code
    
    Args:
        job_type: Type of analysis (wgs, species, etc.)
        job_count_today: Number of jobs of this type today
        
    Returns:
        Job code string (e.g., 'wgs241009_01')
    """
    now = datetime.now()
    return f"{job_type}{now.strftime('%y%m%d')}_{job_count_today:02d}"


def cleanup_old_cache(cache_dict, max_age_seconds=300):
    """
    Clean up old entries from a cache dictionary
    
    Args:
        cache_dict: Dictionary with (value, timestamp) tuples
        max_age_seconds: Maximum age in seconds
    """
    current_time = datetime.now()
    keys_to_delete = []
    
    for key, (value, timestamp) in cache_dict.items():
        age = (current_time - timestamp).total_seconds()
        if age > max_age_seconds:
            keys_to_delete.append(key)
    
    for key in keys_to_delete:
        del cache_dict[key]
        logger.debug(f"Removed expired cache entry: {key}")


def format_file_size(size_bytes):
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., '1.5 MB')
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def truncate_log(log_content, max_size=MAX_LOG_SIZE):
    """
    Truncate log content to maximum size
    
    Args:
        log_content: Log content string
        max_size: Maximum size in bytes
        
    Returns:
        Truncated log content with info message
    """
    if not log_content or len(log_content) <= max_size:
        return log_content
    
    truncated = log_content[-max_size:]
    return truncated + "\n[INFO] Log gekürzt..."


def is_valid_report_file(filename):
    """
    Check if filename is a valid report file
    
    Args:
        filename: Name of file to check
        
    Returns:
        True if valid report file, False otherwise
    """
    return any(filename.lower().endswith(ext) for ext in SUPPORTED_REPORT_EXTENSIONS)