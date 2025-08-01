"""
Autonomy Routes for Jarvis
Handles autonomous operations, memory management, decision-making, workflows, and learning endpoints
"""

import os
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from src.utils.security import verify_auth_token, log_security_event
from src.services.autonomy_service import (
    autonomy_engine, memory_manager, secret_manager, 
    job_scheduler, webhook_processor
)
from src.services.workflow_service import workflow_engine, goal_decomposer
from src.services.learning_service import learning_engine, pattern_recognizer, adaptation_engine
from src.models.database import get_database_stats

autonomy_bp = Blueprint('autonomy', __name__)

# Memory Management Endpoints

@autonomy_bp.route('/memory/store', methods=['POST'])
def store_memory():
    """Store data in memory"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.json
        key = data.get('key')
        value = data.get('value')
        category = data.get('category', 'general')
        expires_in_hours = data.get('expires_in_hours')
        
        if not key or value is None:
            return jsonify({"error": "Key and value are required"}), 400
        
        success = memory_manager.store(key, value, category, expires_in_hours)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Memory stored: {key}",
                "key": key,
                "category": category
            })
        else:
            return jsonify({"error": "Failed to store memory"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/memory/retrieve/<key>', methods=['GET'])
def retrieve_memory(key):
    """Retrieve data from memory"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        value = memory_manager.retrieve(key)
        
        if value is not None:
            return jsonify({
                "status": "success",
                "key": key,
                "value": value
            })
        else:
            return jsonify({"error": "Memory not found"}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/memory/search', methods=['GET'])
def search_memory():
    """Search memory entries"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        category = request.args.get('category')
        pattern = request.args.get('pattern')
        
        memories = memory_manager.search(category, pattern)
        
        return jsonify({
            "status": "success",
            "memories": memories,
            "count": len(memories)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/memory/delete/<key>', methods=['DELETE'])
def delete_memory(key):
    """Delete memory entry"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        success = memory_manager.delete(key)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Memory deleted: {key}"
            })
        else:
            return jsonify({"error": "Memory not found"}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Secret Management Endpoints

@autonomy_bp.route('/secrets/store', methods=['POST'])
def store_secret():
    """Store encrypted secret"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.json
        key = data.get('key')
        value = data.get('value')
        description = data.get('description')
        category = data.get('category', 'general')
        
        if not key or not value:
            return jsonify({"error": "Key and value are required"}), 400
        
        success = secret_manager.store_secret(key, value, description, category)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Secret stored: {key}",
                "key": key,
                "category": category
            })
        else:
            return jsonify({"error": "Failed to store secret"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/secrets/retrieve/<key>', methods=['GET'])
def retrieve_secret(key):
    """Retrieve and decrypt secret"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        value = secret_manager.get_secret(key)
        
        if value is not None:
            return jsonify({
                "status": "success",
                "key": key,
                "value": value
            })
        else:
            return jsonify({"error": "Secret not found"}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/secrets/list', methods=['GET'])
def list_secrets():
    """List secrets (without values)"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        category = request.args.get('category')
        secrets = secret_manager.list_secrets(category)
        
        return jsonify({
            "status": "success",
            "secrets": secrets,
            "count": len(secrets)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Job Scheduling Endpoints

@autonomy_bp.route('/jobs/schedule', methods=['POST'])
def schedule_job():
    """Schedule a job for execution"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.json
        command = data.get('command')
        parameters = data.get('parameters', {})
        job_type = data.get('job_type', 'command')
        priority = data.get('priority', 5)
        delay_minutes = data.get('delay_minutes', 0)
        max_retries = data.get('max_retries', 3)
        
        if not command:
            return jsonify({"error": "Command is required"}), 400
        
        job_id = job_scheduler.schedule_job(
            command, parameters, job_type, priority, delay_minutes, max_retries
        )
        
        if job_id:
            return jsonify({
                "status": "success",
                "message": "Job scheduled successfully",
                "job_id": job_id,
                "command": command,
                "scheduled_for": (datetime.utcnow().timestamp() + delay_minutes * 60) * 1000
            })
        else:
            return jsonify({"error": "Failed to schedule job"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/jobs/pending', methods=['GET'])
def get_pending_jobs():
    """Get pending jobs"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        limit = int(request.args.get('limit', 10))
        jobs = job_scheduler.get_pending_jobs(limit)
        
        return jsonify({
            "status": "success",
            "jobs": jobs,
            "count": len(jobs)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/jobs/status/<job_id>', methods=['PUT'])
def update_job_status(job_id):
    """Update job status"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.json
        status = data.get('status')
        result = data.get('result')
        error_message = data.get('error_message')
        
        if not status:
            return jsonify({"error": "Status is required"}), 400
        
        success = job_scheduler.update_job_status(job_id, status, result, error_message)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Job status updated: {job_id}",
                "job_id": job_id,
                "new_status": status
            })
        else:
            return jsonify({"error": "Job not found"}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Webhook Processing Endpoints

@autonomy_bp.route('/webhooks/store', methods=['POST'])
def store_webhook():
    """Store webhook event"""
    try:
        data = request.json
        event_id = data.get('event_id')
        source = data.get('source')
        event_type = data.get('event_type')
        payload = data.get('payload', {})
        headers = dict(request.headers)
        
        if not event_id or not source or not event_type:
            return jsonify({"error": "event_id, source, and event_type are required"}), 400
        
        success = webhook_processor.store_webhook(event_id, source, event_type, payload, headers)
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Webhook stored successfully",
                "event_id": event_id,
                "source": source,
                "event_type": event_type
            })
        else:
            return jsonify({"error": "Failed to store webhook"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/webhooks/unprocessed', methods=['GET'])
def get_unprocessed_webhooks():
    """Get unprocessed webhook events"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        source = request.args.get('source')
        limit = int(request.args.get('limit', 10))
        
        webhooks = webhook_processor.get_unprocessed_webhooks(source, limit)
        
        return jsonify({
            "status": "success",
            "webhooks": webhooks,
            "count": len(webhooks)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Autonomy Engine Endpoints

@autonomy_bp.route('/autonomy/session/create', methods=['POST'])
def create_autonomy_session():
    """Create new autonomy session"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.json
        goal = data.get('goal')
        metadata = data.get('metadata', {})
        
        if not goal:
            return jsonify({"error": "Goal is required"}), 400
        
        session_id = autonomy_engine.create_autonomy_session(goal, metadata)
        
        if session_id:
            return jsonify({
                "status": "success",
                "message": "Autonomy session created",
                "session_id": session_id,
                "goal": goal
            })
        else:
            return jsonify({"error": "Failed to create autonomy session"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/autonomy/session/<session_id>/progress', methods=['PUT'])
def update_session_progress(session_id):
    """Update session progress"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.json
        progress = data.get('progress')
        current_step = data.get('current_step')
        
        if progress is None:
            return jsonify({"error": "Progress is required"}), 400
        
        success = autonomy_engine.update_session_progress(session_id, progress, current_step)
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Session progress updated",
                "session_id": session_id,
                "progress": progress
            })
        else:
            return jsonify({"error": "Session not found"}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/autonomy/decision', methods=['POST'])
def make_autonomous_decision():
    """Make autonomous decision"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.json
        context = data.get('context', {})
        options = data.get('options', [])
        
        if not options:
            return jsonify({"error": "Options are required"}), 400
        
        decision = autonomy_engine.make_autonomous_decision(context, options)
        
        return jsonify({
            "status": "success",
            "decision": decision
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/autonomy/extend', methods=['POST'])
def self_extend_capability():
    """Self-extend capabilities"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.json
        capability_name = data.get('capability_name')
        implementation = data.get('implementation')
        description = data.get('description')
        
        if not capability_name or not implementation:
            return jsonify({"error": "capability_name and implementation are required"}), 400
        
        success = autonomy_engine.self_extend_capability(capability_name, implementation, description)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Capability '{capability_name}' scheduled for integration",
                "capability_name": capability_name
            })
        else:
            return jsonify({"error": "Failed to extend capability"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/autonomy/performance', methods=['GET'])
def analyze_performance():
    """Analyze system performance"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        analysis = autonomy_engine.analyze_performance()
        
        return jsonify({
            "status": "success",
            "analysis": analysis
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Workflow Management Endpoints

@autonomy_bp.route('/workflows/create', methods=['POST'])
def create_workflow():
    """Create new autonomous workflow"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.json
        goal = data.get('goal')
        context = data.get('context', {})
        
        if not goal:
            return jsonify({"error": "Goal is required"}), 400
        
        workflow_id = workflow_engine.create_workflow(goal, context)
        
        if workflow_id:
            return jsonify({
                "status": "success",
                "message": "Workflow created successfully",
                "workflow_id": workflow_id,
                "goal": goal
            })
        else:
            return jsonify({"error": "Failed to create workflow"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/workflows/<workflow_id>/execute', methods=['POST'])
def execute_workflow(workflow_id):
    """Execute workflow"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        success = workflow_engine.execute_workflow(workflow_id)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Workflow {workflow_id} execution started",
                "workflow_id": workflow_id
            })
        else:
            return jsonify({"error": "Failed to execute workflow"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/workflows/<workflow_id>/status', methods=['GET'])
def get_workflow_status(workflow_id):
    """Get workflow status"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        status = workflow_engine.get_workflow_status(workflow_id)
        
        return jsonify({
            "status": "success",
            "workflow_status": status
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/workflows/<workflow_id>/cancel', methods=['POST'])
def cancel_workflow(workflow_id):
    """Cancel workflow"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        success = workflow_engine.cancel_workflow(workflow_id)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Workflow {workflow_id} cancelled",
                "workflow_id": workflow_id
            })
        else:
            return jsonify({"error": "Workflow not found"}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/workflows/analyze-goal', methods=['POST'])
def analyze_goal():
    """Analyze goal complexity"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.json
        goal = data.get('goal')
        
        if not goal:
            return jsonify({"error": "Goal is required"}), 400
        
        analysis = goal_decomposer.analyze_goal_complexity(goal)
        
        return jsonify({
            "status": "success",
            "goal_analysis": analysis
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Learning and Adaptation Endpoints

@autonomy_bp.route('/learning/analyze', methods=['POST'])
def analyze_learning():
    """Analyze patterns and learn from interactions"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        learning_data = learning_engine.learn_from_interactions()
        
        return jsonify({
            "status": "success",
            "learning_data": learning_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/learning/patterns', methods=['GET'])
def get_command_patterns():
    """Get command usage patterns"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        days = int(request.args.get('days', 7))
        patterns = pattern_recognizer.analyze_command_patterns(days)
        
        return jsonify({
            "status": "success",
            "patterns": patterns
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/learning/anomalies', methods=['GET'])
def detect_anomalies():
    """Detect anomalous behavior patterns"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        anomalies = pattern_recognizer.detect_anomalies()
        
        return jsonify({
            "status": "success",
            "anomalies": anomalies
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/learning/predict', methods=['POST'])
def predict_next_command():
    """Predict next likely command"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.json
        recent_commands = data.get('recent_commands', [])
        
        prediction = pattern_recognizer.predict_next_command(recent_commands)
        
        return jsonify({
            "status": "success",
            "prediction": prediction
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/learning/summary', methods=['GET'])
def get_learning_summary():
    """Get learning progress summary"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        summary = learning_engine.get_learning_summary()
        
        return jsonify({
            "status": "success",
            "learning_summary": summary
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/adaptations/execute', methods=['POST'])
def execute_adaptations():
    """Execute scheduled adaptations"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        result = adaptation_engine.execute_scheduled_adaptations()
        
        return jsonify({
            "status": "success",
            "execution_result": result
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Database Statistics Endpoint

@autonomy_bp.route('/database/stats', methods=['GET'])
def get_database_statistics():
    """Get database statistics"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        stats = get_database_stats()
        
        return jsonify({
            "status": "success",
            "database_stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Utility Endpoints

@autonomy_bp.route('/autonomy/cleanup', methods=['POST'])
def cleanup_expired_data():
    """Clean up expired data"""
    try:
        if not verify_auth_token(request):
            return jsonify({"error": "Unauthorized"}), 401
        
        # Clean up expired memory entries
        expired_count = memory_manager.cleanup_expired()
        
        return jsonify({
            "status": "success",
            "message": "Cleanup completed",
            "expired_memories_removed": expired_count
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@autonomy_bp.route('/autonomy/health', methods=['GET'])
def health_check():
    """Health check for autonomy system"""
    try:
        # Basic health checks
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "memory_manager": "operational",
                "secret_manager": "operational",
                "job_scheduler": "operational",
                "webhook_processor": "operational",
                "autonomy_engine": "operational",
                "workflow_engine": "operational",
                "learning_engine": "operational",
                "adaptation_engine": "operational"
            }
        }
        
        # Get basic stats
        stats = get_database_stats()
        health_status["database_stats"] = stats
        
        return jsonify(health_status)
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),

            "timestamp": datetime.utcnow().isoformat()
        }), 500

