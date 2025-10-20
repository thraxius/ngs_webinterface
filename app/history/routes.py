# history/routes.py
"""
Routes for analysis history
"""

import os
import json
import logging
from flask import Blueprint, jsonify
from flask_login import login_required

from extensions import db
from models import AnalysisJob
from app.core.utils import SUPPORTED_REPORT_EXTENSIONS

logger = logging.getLogger('analysis')

history_bp = Blueprint('history', __name__)


@history_bp.route('/api/analysis_history')
@login_required
def api_analysis_history():
    """API endpoint for analysis history with optimized queries"""
    try:
        # Use eager loading to reduce DB queries
        jobs = db.session.query(AnalysisJob).order_by(
            AnalysisJob.created_at.desc()
        ).limit(10).all()
        
        jobs_data = []
        
        for job in jobs:
            # Parse parameters safely
            try:
                params = json.loads(job.parameters) if job.parameters else {}
                input_path = params.get("input_path", "")
            except (json.JSONDecodeError, TypeError) as e:
                input_path = ""
                logger.warning(f"Failed to parse parameters for job {job.id}: {e}")
            
            # Find reports efficiently - only for completed jobs
            reports = []
            if input_path and job.status in ['finished', 'failed']:
                reports_path = os.path.join(input_path, "reports")
                if os.path.exists(reports_path) and os.path.isdir(reports_path):
                    try:
                        for file in os.listdir(reports_path):
                            if any(file.lower().endswith(ext) for ext in SUPPORTED_REPORT_EXTENSIONS):
                                reports.append({
                                    'name': file,
                                    'path': os.path.join(reports_path, file)
                                })
                        logger.debug(f"Found {len(reports)} reports for job {job.job_code}")
                    except (OSError, PermissionError) as e:
                        logger.error(f"Error reading reports for job {job.id}: {e}")
            
            # Format job data
            job_data = {
                'id': job.id,
                'job_code': job.job_code or f"job_{job.id}",
                'job_type': job.job_type,
                'run_name': job.run_name or "Unbenannt",
                'status': job.status,
                'created_at': job.created_at.strftime('%d.%m.%Y %H:%M'),
                'reports': sorted(reports, key=lambda x: x['name'].lower()) if reports else []
            }
            jobs_data.append(job_data)
        
        return jsonify({'jobs': jobs_data})
        
    except Exception as e:
        logger.error(f"Error in api_analysis_history: {e}")
        return jsonify({'error': 'Fehler beim Laden der Historie'}), 500