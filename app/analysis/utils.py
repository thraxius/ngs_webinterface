# analysis/utils.py
"""
Analysis-specific utility functions
SSH commands, FASTQ parsing, sample extraction
"""

import os
import re
import subprocess
import collections
import logging
from app.core.utils import MAX_RECURSIVE_DEPTH

logger = logging.getLogger('analysis')

# SSH command timeouts
SSH_COMMAND_TIMEOUT = 30
SSH_KILL_TIMEOUT = 10
SSH_LOG_TIMEOUT = 15


def ssh_command(mode, *args, capture_output=False, background=False, timeout=SSH_COMMAND_TIMEOUT):
    """
    Execute SSH commands with proper error handling
    
    Args:
        mode: Command mode (run, kill, get_log)
        *args: Additional arguments for the command
        capture_output: Whether to capture stdout
        background: Whether to run in background
        timeout: Command timeout in seconds
        
    Returns:
        Tuple of (result/success, error_message/pid)
    """
    cmd = ["/opt/ngs_webinterface/scripts/ssh_wrapper.sh", mode, *args]
    
    try:
        if background:
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            logger.info(f"Started background SSH command: {' '.join(cmd)} with PID {process.pid}")
            return True, process.pid
        else:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                check=False
            )
            logger.info(f"Executed SSH command: {' '.join(cmd)}")
            if result.returncode == 0:
                return result.stdout.strip() if capture_output else True, None
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unbekannter SSH-Fehler"
                logger.error(f"SSH command failed: {error_msg}")
                return None, error_msg
                
    except subprocess.TimeoutExpired:
        logger.error(f"SSH command timeout after {timeout}s")
        return None, f"SSH-Befehl Timeout nach {timeout}s"
    except Exception as e:
        logger.error(f"SSH command exception: {str(e)}")
        return None, str(e)


def ssh_start_analysis(*args):
    """
    Start analysis in background
    
    Args:
        *args: Arguments for analysis (type, path, samples, job_code)
        
    Returns:
        Tuple of (success, pid/error)
    """
    return ssh_command("run", *args, background=True)


def ssh_kill_job(*args):
    """
    Kill running job
    
    Args:
        *args: Arguments for killing job (job_code, job_type)
        
    Returns:
        Tuple of (success, error_message)
    """
    return ssh_command("kill", *args, timeout=SSH_KILL_TIMEOUT)


def ssh_get_log(*args):
    """
    Fetch log with size limit
    
    Args:
        *args: Arguments for fetching log (input_path, analysis_type)

    Returns:
        Log content string
    """
    result, error = ssh_command("get_log", *args, capture_output=True, timeout=SSH_LOG_TIMEOUT)
    
    if error:
        logger.error(f"Log fetch error: {error}")
        return f"[ERROR] Log nicht verfügbar: {error}"
    
    return result or "[INFO] Noch kein Log verfügbar"


def find_fastq_files_recursive(folder_path, depth=0):
    """
    Recursively find all FASTQ files in a directory and its subdirectories
    
    Args:
        folder_path: Root folder to search
        depth: Current recursion depth (internal)
        
    Returns:
        List of FASTQ file paths
    """
    if depth > MAX_RECURSIVE_DEPTH:
        logger.warning(f"Maximum recursion depth reached for {folder_path}")
        return []
    
    fastq_files = []
    
    try:
        with os.scandir(folder_path) as entries:
            for entry in entries:
                if entry.is_file() and (entry.name.endswith('.fastq.gz') or entry.name.endswith('.fastq')):
                    # Skip undetermined files
                    if not entry.name.startswith('Undetermined_'):
                        fastq_files.append(entry.path)
                elif entry.is_dir() and not entry.name.startswith('.'):
                    # Recursively search subdirectories
                    subfolder_files = find_fastq_files_recursive(entry.path, depth + 1)
                    fastq_files.extend(subfolder_files)
        
    except (OSError, PermissionError) as e:
        logger.error(f"Error scanning directory {folder_path}: {e}")
    
    return fastq_files


def extract_samples_with_details(folder_path, recursive=False):
    """
    Extract sample information from fastq files with optional recursive search
    
    Args:
        folder_path: Folder containing FASTQ files
        recursive: Whether to search recursively
        
    Returns:
        List of sample dictionaries
    """
    source_map = {
        "L": "Lebensmittel",
        "H": "Humanmedizinisch", 
        "V": "Veterinärmedizinisch",
        "U": "Umgebung",
        "R": "Referenz",
        "TA": "Tierart",
        "NTC": "Negativkontrolle",
        "PTC": "Positivkontrolle"
    }
    
    sample_dict = collections.OrderedDict()
    pattern_universal = re.compile(
        r"(?:"
        # --- IonTorrent ---
        r"\.R_(?P<ion_run>\d{4}_\d{2}_\d{2})_\d{2}_\d{2}_\d{2}_user_.*?-(?P<ion_source>[LHVUR]|TA|NTC|PTC)_(?P<ion_date>\d{8})\.IonXpress_(?P<ion_sample>\d{3})\.fastq(?:\.gz)?"
        r"|"
        # --- Illumina ---
        r"(?:(?P<illumina_source>[LHVUR])-(?P<illumina_id>[A-Za-z0-9\-]+)_S\d+_L\d{3}_R[12]_001)\.fastq(?:\.gz)?"
        r"|"
        # --- Illumina NTC / PTC ---
        r"(?P<special_source>NTC|PTC)_S\d+_L\d{3}_R[12]_001\.fastq(?:\.gz)?"
        r")$", re.IGNORECASE
    )

    try:
        # Get FASTQ files based on search mode
        if recursive:
            fastq_files = find_fastq_files_recursive(folder_path)
            logger.info(f"Found {len(fastq_files)} FASTQ files recursively in {folder_path}")
        else:
            fastq_files = []
            if os.path.exists(folder_path):
                with os.scandir(folder_path) as entries:
                    fastq_files = [
                        entry.path for entry in entries 
                        if entry.is_file() and (entry.name.endswith('.fastq.gz') or entry.name.endswith('.fastq'))
                        and not entry.name.startswith('Undetermined_')
                    ]
            logger.info(f"Found {len(fastq_files)} FASTQ files in {folder_path}")
        
        # Process each FASTQ file
        for file_path in fastq_files:
            file_name = os.path.basename(file_path)
            
            match = pattern_universal.search(file_name)
            if not match:
                logger.debug(f"{file_name} - Kein Pattern-Match")
                continue
                
            # IonTorrent
            if match.group("ion_source"):
                source_code = match.group("ion_source")
                run_date = match.group("ion_run").replace("_", "-")
                sample_date = match.group("ion_date")
                sample_num = match.group("ion_sample")
                formatted_sample_date = f"{sample_date[4:]}-{sample_date[2:4]}-{sample_date[:2]}"
                key = f"{source_code}-{formatted_sample_date}_S{sample_num}"
                if key not in sample_dict:
                    sample_dict[key] = {
                        "source": source_map.get(source_code, source_code),
                        "probennummer": f"{formatted_sample_date}_S{sample_num}",
                        "file_path": os.path.dirname(file_path),
                        "run_date": run_date,
                        "original_sample_date": sample_date
                    }
            
            # Illumina
            elif match.group("illumina_source"):
                source_code = match.group("illumina_source")
                raw_name = match.group("illumina_id")
                key = f"{source_code}-{raw_name}"
                if key not in sample_dict:
                    sample_dict[key] = {
                        "source": source_map.get(source_code, source_code),
                        "probennummer": raw_name,
                        "file_path": os.path.dirname(file_path)
                    }
            
            # Illumina NTC/PTC
            elif match.group("special_source"):
                source_code = match.group("special_source")
                if source_code not in sample_dict: 
                    sample_dict[source_code] = {
                        "source": source_map.get(source_code, source_code),
                        "probennummer": source_code,
                        "file_path": os.path.dirname(file_path)
                    }
            else:
                logger.debug(f"{file_name} - Match gefunden, aber keine Gruppe erkannt")
                
        return list(sample_dict.values())
        
    except (OSError, PermissionError, ValueError) as e:
        logger.error(f"Error extracting samples from {folder_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in extract_samples_with_details: {e}")
        raise