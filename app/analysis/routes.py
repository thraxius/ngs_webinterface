# analysis/routes.py
"""
Routes for analysis operations
"""

import os
import logging
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, send_file
from flask_login import login_required, current_user
from werkzeug.exceptions import BadRequest, NotFound, Forbidden

from app.core.utils import validate_path, is_valid_report_file
from .services import AnalysisService

logger = logging.getLogger('analysis')

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/analysis', methods=['GET'])
@login_required
def analysis():
    """Main analysis page with optimized job handling"""
    AnalysisService.cleanup_stuck_jobs()
    
    running_job = AnalysisService.get_running_job(current_user.id)
    
    if running_job:
        logger.info(f"Found running job: {running_job.job_code}")
    else:
        logger.info("No running jobs found")
    
    return render_template('analysis.html', running_job=running_job)


@analysis_bp.route('/get_samples', methods=['POST'])
@login_required  
def get_samples():
    """Get samples from folder with validation and optional recursive search"""
    folder_path = request.form.get('folder_path', '').strip()
    recursive = request.form.get('recursive', 'false').lower() == 'true'
    
    samples, error = AnalysisService.get_samples(folder_path, recursive)
    
    if error:
        if samples is None:
            return jsonify({"error": error}), 400
        else:
            return jsonify({"samples": [], "message": error}), 200
    
    return jsonify({"samples": samples})


@analysis_bp.route('/start_analysis', methods=['POST'])
@login_required
def start_analysis():
    """Start analysis with comprehensive validation"""
    try:
        # Extract form data
        folder_path = request.form.get('folder_path', '').strip()
        analysis_type = request.form.get('analysis_type', '').strip()
        run_name = request.form.get('run_name', '').strip()
        selected_samples = request.form.getlist('selected_samples')
        
        # Validation
        if not all([folder_path, analysis_type, selected_samples]):
            logger.warning("Missing required fields in start_analysis")
            return redirect(url_for('analysis.analysis'))
        
        # Create and start job
        job, error = AnalysisService.create_and_start_job(
            current_user.id,
            folder_path,
            analysis_type,
            run_name,
            selected_samples
        )
        
        if error:
            logger.error(f"Failed to start analysis: {error}")
        
        return redirect(url_for('analysis.analysis'))
        
    except Exception as e:
        logger.error(f"Error in start_analysis: {e}")
        return redirect(url_for('analysis.analysis'))


@analysis_bp.route("/browse_folder", methods=["GET"])
@login_required
def browse_folder():
    """Browse folders with caching and validation"""
    path = request.args.get("path", "").strip()
    
    folders, current_path, error = AnalysisService.browse_folder(path)
    
    if error:
        return jsonify({"error": error}), 400
    
    return jsonify({
        "current": current_path,
        "folders": folders
    })


@analysis_bp.route('/force_reset', methods=['POST'])
@login_required
def force_reset():
    """Force reset all running jobs for current user (emergency function)"""
    reset_count = AnalysisService.force_reset_user_jobs(current_user.id)
    logger.info(f"Force-reset {reset_count} jobs for user {current_user.username}")
    return redirect(url_for('analysis.analysis'))


@analysis_bp.route('/cancel_analysis/<int:job_id>', methods=['POST'])
@login_required
def cancel_analysis(job_id):
    """Cancel running analysis with proper validation"""
    success, error = AnalysisService.cancel_job(job_id, current_user.id)
    
    if not success and error:
        logger.error(f"Failed to cancel job {job_id}: {error}")
    
    return redirect(url_for('analysis.analysis'))


@analysis_bp.route('/api/progress/<int:job_id>')
@login_required
def api_progress(job_id):
    """API endpoint for job progress with status updates"""
    result = AnalysisService.get_job_progress(job_id, current_user.id)
    
    if "error" in result and result["error"] == "Unauthorized":
        return jsonify(result), 403
    
    return jsonify(result)


@analysis_bp.route('/api/log/<int:job_id>')
@login_required
def api_log(job_id):
    """API endpoint for job logs with error handling"""
    result = AnalysisService.get_job_log(job_id, current_user.id)
    
    if "[ERROR] Keine Berechtigung" in result.get("log", ""):
        return jsonify(result), 403
    
    return jsonify(result)


@analysis_bp.route('/show_report')
@login_required
def show_report():
    """Serve reports securely with proper MIME types"""
    filepath = request.args.get('filepath', '').strip()
    
    try:
        if not filepath:
            raise BadRequest("Kein Dateipfad angegeben")
        
        # Validate path
        validated_path = validate_path(filepath)
        
        if not os.path.exists(validated_path):
            raise NotFound("Datei nicht gefunden")
        
        if not os.path.isfile(validated_path):
            raise BadRequest("Pfad zeigt nicht auf eine Datei")
        
        # Check file extension
        if not is_valid_report_file(os.path.basename(validated_path)):
            raise Forbidden("Dateityp nicht unterstützt")
        
        # Determine MIME type
        mime_types = {
            '.html': 'text/html',
            '.pdf': 'application/pdf', 
            '.txt': 'text/plain',
            '.csv': 'text/csv',
            '.json': 'application/json'
        }
        
        ext = os.path.splitext(validated_path)[1].lower()
        mime_type = mime_types.get(ext, 'application/octet-stream')
        
        logger.info(f"Serving report: {validated_path}")
        return send_file(validated_path, mimetype=mime_type)
        
    except (BadRequest, NotFound, Forbidden) as e:
        logger.warning(f"Client error in show_report: {e}")
        return str(e), e.code
    except Exception as e:
        logger.error(f"Error serving report {filepath}: {e}")
        return "Interner Serverfehler", 500


# Error handlers
@analysis_bp.errorhandler(BadRequest)
def handle_bad_request(error):
    logger.warning(f"Bad request: {error}")
    return jsonify({'error': str(error)}), 400


@analysis_bp.errorhandler(NotFound)
def handle_not_found(error):
    logger.warning(f"Not found: {error}")
    return jsonify({'error': 'Ressource nicht gefunden'}), 404


@analysis_bp.errorhandler(Forbidden)
def handle_forbidden(error):
    logger.warning(f"Forbidden: {error}")
    return jsonify({'error': 'Zugriff verweigert'}), 403