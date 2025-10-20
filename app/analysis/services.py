# analysis/services.py
"""
Business logic for analysis operations
Separated from routes for better testability and maintainability
"""

import os
import json
import re
import logging
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import time

from extensions import db
from models import AnalysisJob
from app.core.utils import validate_path, generate_job_code, truncate_log, is_valid_report_file, ANALYSIS_BASE_PATHS
from .utils import ssh_start_analysis, ssh_kill_job, ssh_get_log, extract_samples_with_details

logger = logging.getLogger('analysis')


class AnalysisService:
    """Service class for analysis operations"""
    
    @staticmethod
    def cleanup_stuck_jobs():
        """Clean up jobs that are stuck in running state"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=12)
        stuck_jobs = AnalysisJob.query.filter_by(status='running').filter(
            AnalysisJob.created_at < cutoff
        ).all()
        
        for job in stuck_jobs:
            job.status = "failed"
            logger.info(f"Marked stuck job {job.id} as failed")
        
        if stuck_jobs:
            db.session.commit()
    
    @staticmethod
    def get_running_job(user_id):
        """
        Get running job for user with validation
        
        Args:
            user_id: User ID
            
        Returns:
            AnalysisJob or None
        """
        running_job = db.session.query(AnalysisJob).filter_by(
            user_id=user_id, 
            status='running'
        ).first()
        
        # Double-check: if job exists but is old, mark as failed
        if running_job:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            if running_job.created_at < cutoff:
                logger.warning(f"Force-failing old running job {running_job.id}")
                running_job.status = "failed"
                running_job.updated_at = datetime.now(timezone.utc)
                db.session.commit()
                return None
            
            # Add job code if missing
            if not running_job.job_code:
                running_job.job_code = f"{running_job.job_type}{running_job.created_at.strftime('%y%m%d')}_{running_job.id:02d}"
        
        return running_job
    
    @staticmethod
    def get_samples(folder_path, recursive=False):
        """
        Get samples from folder with validation
        
        Args:
            folder_path: Path to folder
            recursive: Whether to search recursively
            
        Returns:
            Tuple of (samples_list, error_message)
        """
        try:
            validated_path = validate_path(folder_path)
            
            if not os.path.isdir(validated_path):
                return None, "Pfad ist kein gültiger Ordner"
            
            samples = extract_samples_with_details(validated_path, recursive=recursive)
            
            if not samples:
                search_type = "rekursiv in diesem Ordner und allen Unterordnern" if recursive else "in diesem Ordner"
                return [], f"Keine FASTQ-Dateien {search_type} gefunden"
            
            search_info = f" (rekursiv)" if recursive else ""
            logger.info(f"Found {len(samples)} samples in {folder_path}{search_info}")
            return samples, None
            
        except Exception as e:
            logger.error(f"Error in get_samples: {e}")
            return None, str(e)
    
    @staticmethod
    def create_and_start_job(user_id, folder_path, analysis_type, run_name, selected_samples):
        """
        Create and start a new analysis job
        
        Args:
            user_id: User ID
            folder_path: Path to input folder
            analysis_type: Type of analysis
            run_name: Name of the run
            selected_samples: List of selected samples
            
        Returns:
            Tuple of (job, error_message)
        """
        try:
            # Validate analysis type
            if analysis_type not in ANALYSIS_BASE_PATHS:
                return None, f"Invalid analysis type: {analysis_type}"
            
            # Check for running job
            running_job = AnalysisJob.query.filter_by(
                user_id=user_id, 
                status='running'
            ).first()
            
            if running_job:
                return None, "Es läuft bereits eine Analyse"
            
            # Validate path
            validated_path = validate_path(folder_path, analysis_type)
            
            # Use folder name as run_name if empty
            if not run_name:
                run_name = os.path.basename(os.path.normpath(folder_path))
            
            # Create job with correct counter
            now = datetime.now(timezone.utc)
            start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
            
            # Count only jobs of the same type from today
            job_count_today = db.session.query(AnalysisJob).filter(
                AnalysisJob.created_at >= start_of_day,
                AnalysisJob.job_type == analysis_type
            ).count() + 1
            
            job_code = generate_job_code(analysis_type, job_count_today)
            
            job = AnalysisJob(
                user_id=user_id,
                job_type=analysis_type,
                job_code=job_code,
                run_name=run_name,
                parameters=json.dumps({
                    "samples": selected_samples,
                    "input_path": validated_path,
                    "sample_count": len(selected_samples)
                }),
                status="queued",
                progress=0,
                created_at=now
            )
            
            logger.info(f"Creating job {job_code} for user {user_id} with {len(selected_samples)} samples")
            db.session.add(job)
            db.session.commit()
            
            # Start analysis
            success, result = ssh_start_analysis(
                analysis_type, 
                validated_path, 
                ",".join(selected_samples), 
                str(job.job_code)
            )
            
            if success:
                job.status = "running"
                db.session.commit()
                logger.info(f"Started analysis {job_code}")
                return job, None
            else:
                job.status = "failed"
                db.session.commit()
                error_msg = result or "Unbekannter Fehler beim Starten"
                logger.error(f"Failed to start analysis {job_code}: {error_msg}")
                return job, error_msg
                
        except Exception as e:
            logger.error(f"Error in create_and_start_job: {e}")
            db.session.rollback()
            return None, str(e)
    
    @staticmethod
    def cancel_job(job_id, user_id):
        """
        Cancel running analysis job
        
        Args:
            job_id: Job ID
            user_id: User ID (for authorization)
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            job = AnalysisJob.query.get(job_id)
            if not job:
                return False, "Job nicht gefunden"
            
            # Authorization check
            if job.user_id != user_id:
                logger.warning(f"Unauthorized cancel attempt by user {user_id} for job {job_id}")
                return False, "Keine Berechtigung"
            
            if job.status != "running":
                logger.info(f"Job {job_id} is not running (status: {job.status})")
                return False, "Job läuft nicht"
            
            # Kill job
            job_identifier = job.job_code or str(job.id)
            success, error = ssh_kill_job(job_identifier, job.job_type)
            
            if success:
                job.status = "failed"
                job.updated_at = datetime.now(timezone.utc)
                db.session.commit()
                logger.info(f"Cancelled analysis {job.job_code}")
                return True, None
            else:
                logger.error(f"Failed to cancel job {job_id}: {error}")
                return False, error
                
        except Exception as e:
            logger.error(f"Error in cancel_job: {e}")
            return False, str(e)
    
    @staticmethod
    def force_reset_user_jobs(user_id):
        """
        Force reset all running jobs for user (emergency function)
        
        Args:
            user_id: User ID
            
        Returns:
            Number of jobs reset
        """
        try:
            running_jobs = AnalysisJob.query.filter_by(
                user_id=user_id,
                status='running'
            ).all()
            
            reset_count = 0
            for job in running_jobs:
                job.status = 'failed'
                job.updated_at = datetime.now(timezone.utc)
                reset_count += 1
                logger.warning(f"Force-reset job {job.id} ({job.job_code})")
            
            db.session.commit()
            logger.info(f"Force-reset {reset_count} jobs for user {user_id}")
            return reset_count
                
        except Exception as e:
            logger.error(f"Error in force_reset: {e}")
            db.session.rollback()
            return 0
    
    @staticmethod
    def get_job_progress(job_id, user_id):
        """
        Get job progress and update status based on log
        
        Args:
            job_id: Job ID
            user_id: User ID (for authorization)
            
        Returns:
            Dict with status and optional error
        """
        try:
            job = AnalysisJob.query.get(job_id)
            if not job:
                return {"error": "Job nicht gefunden"}
            
            # Authorization check
            if job.user_id != user_id:
                logger.warning(f"Unauthorized access attempt to job {job_id} by user {user_id}")
                return {"error": "Unauthorized"}
            
            params = json.loads(job.parameters) if job.parameters else {}
            input_path = params.get("input_path")
            
            if not input_path:
                return {"status": job.status, "error": "Kein Eingabepfad"}
            
            # Check log for completion markers
            if job.status == "running":
                log_content = ssh_get_log(input_path, job.job_type)
                
                if log_content:
                    if re.search(r"Analysis is ready|ANALYSIS COMPLETE", log_content, re.IGNORECASE):
                        job.status = "finished"
                        job.updated_at = datetime.now(timezone.utc)
                        db.session.commit()
                        logger.info(f"Job {job.job_code} marked as finished")
                    elif re.search(r"Exiting pipeline|ANALYSIS FAILED|ERROR.*FATAL", log_content, re.IGNORECASE):
                        job.status = "failed"
                        job.updated_at = datetime.now(timezone.utc)
                        db.session.commit()
                        logger.info(f"Job {job.job_code} marked as failed")
            
            return {"status": job.status}
            
        except Exception as e:
            logger.error(f"Error in get_job_progress: {e}")
            return {"status": job.status if job else "unknown", "error": str(e)}
    
    @staticmethod
    def get_job_log(job_id, user_id):
        """
        Get job log content
        
        Args:
            job_id: Job ID
            user_id: User ID (for authorization)
            
        Returns:
            Dict with log content or error
        """
        try:
            job = AnalysisJob.query.get(job_id)
            if not job:
                return {"log": "[ERROR] Job nicht gefunden"}
            
            # Authorization check
            if job.user_id != user_id:
                logger.warning(f"Unauthorized log access attempt for job {job_id}")
                return {"log": "[ERROR] Keine Berechtigung"}
            
            params = json.loads(job.parameters) if job.parameters else {}
            input_path = params.get("input_path")
            
            if not input_path:
                return {"log": "[ERROR] Kein Eingabepfad in Job-Parametern"}
            
            log_content = ssh_get_log(input_path, job.job_type)
            log_content = truncate_log(log_content)
            return {"log": log_content}
            
        except Exception as e:
            logger.error(f"Error in get_job_log for job {job_id}: {e}")
            return {"log": f"[ERROR] Fehler beim Laden des Logs: {str(e)}"}
    
    @staticmethod
    @lru_cache(maxsize=128)
    def get_folder_list(path, timestamp):
        """
        Get list of folders in path (cached)
        
        Args:
            path: Path to browse
            timestamp: Timestamp for cache invalidation
            
        Returns:
            List of folder dictionaries
        """
        folders = []
        try:
            if os.path.exists(path):
                with os.scandir(path) as entries:
                    for entry in entries:
                        if entry.is_dir():
                            folders.append({"name": entry.name, "path": entry.path})
                
                # Sort case-insensitive
                folders.sort(key=lambda x: x["name"].lower())
        except (OSError, PermissionError) as e:
            logger.error(f"Error listing folders in {path}: {e}")
        
        return folders
    
    @staticmethod
    def browse_folder(path):
        """
        Browse folder with validation and caching
        
        Args:
            path: Path to browse
            
        Returns:
            Tuple of (folders_list, current_path, error_message)
        """
        try:
            # Determine analysis type from path or default
            analysis_type = None
            for atype, apath in ANALYSIS_BASE_PATHS.items():
                if path.startswith(apath):
                    analysis_type = atype
                    break
            
            # If no analysis type determined, default to first available
            if not analysis_type:
                analysis_type = list(ANALYSIS_BASE_PATHS.keys())[0]
                if not path:
                    path = ANALYSIS_BASE_PATHS[analysis_type]
            
            validated_path = validate_path(path, analysis_type)
            
            # Use cache with timestamp for invalidation
            timestamp = int(time.time() / 300)  # Cache for 5 minutes
            folders = AnalysisService.get_folder_list(validated_path, timestamp)
            
            return folders, validated_path, None
            
        except Exception as e:
            logger.error(f"Error in browse_folder: {e}")
            return [], "", str(e)