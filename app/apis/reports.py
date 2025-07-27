"""
Reports API Blueprint
定义所有报告查询相关的HTTP接口
"""
from flask import Blueprint, request, jsonify
import logging
import os

from app.core.storage_manager import StorageManager


reports_bp = Blueprint('reports', __name__)
logger = logging.getLogger(__name__)


@reports_bp.route('/reports/<report_id>', methods=['GET'])
def get_report(report_id):
    """获取指定报告的详细信息
    
    GET /api/v1/reports/<report_id>
    
    Response:
    {
        "report_id": "uuid",
        "task_id": "task1",
        "status": "success",
        "timestamps": {...},
        "plan": {...},
        "execution_log": {...},
        "final_summary": "...",
        "error_details": null
    }
    """
    try:
        storage_manager = StorageManager()
        report = storage_manager.get_report(report_id)
        
        if not report:
            logger.warning(f"Report {report_id} not found")
            return jsonify({
                "error": "Report not found",
                "message": f"Report with ID '{report_id}' does not exist"
            }), 404
        
        logger.info(f"Retrieved report {report_id}")
        return jsonify(report), 200
        
    except Exception as e:
        logger.error(f"Error retrieving report {report_id}: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@reports_bp.route('/reports/<report_id>/status', methods=['GET'])
def get_report_status(report_id):
    """获取报告的状态信息
    
    GET /api/v1/reports/<report_id>/status
    
    Response:
    {
        "report_id": "uuid",
        "status": "running",
        "progress": {
            "current_step": "step_2",
            "total_steps": 5,
            "completed_steps": 1
        }
    }
    """
    try:
        storage_manager = StorageManager()
        report = storage_manager.get_report(report_id)
        
        if not report:
            return jsonify({
                "error": "Report not found",
                "message": f"Report with ID '{report_id}' does not exist"
            }), 404
        
        # 计算进度信息
        progress_info = _calculate_progress(report)
        
        status_info = {
            "report_id": report_id,
            "task_id": report.get('task_id'),
            "status": report.get('status'),
            "timestamps": report.get('timestamps', {}),
            "progress": progress_info,
            "final_message": report.get('final_summary') if report.get('status') == 'success' else None,
            "error_message": report.get('error', {}).get('message') if report.get('status') == 'failed' else None
        }
        
        return jsonify(status_info), 200
        
    except Exception as e:
        logger.error(f"Error retrieving report status {report_id}: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@reports_bp.route('/reports', methods=['GET'])
def list_reports():
    """列出所有报告
    
    GET /api/v1/reports?limit=10&offset=0&status=success&task_id=task1
    
    Response:
    {
        "reports": [
            {
                "report_id": "uuid",
                "task_id": "task1",
                "status": "success",
                "created_at": "2023-...",
                "finished_at": "2023-..."
            }
        ],
        "total_count": 25,
        "limit": 10,
        "offset": 0
    }
    """
    try:
        # 解析查询参数
        limit = min(int(request.args.get('limit', 50)), 100)  # 最大100条
        offset = int(request.args.get('offset', 0))
        status_filter = request.args.get('status')
        task_id_filter = request.args.get('task_id')
        
        storage_manager = StorageManager()
        reports_dir = os.path.join(storage_manager.data_dir, 'reports')
        
        if not os.path.exists(reports_dir):
            return jsonify({
                "reports": [],
                "total_count": 0,
                "limit": limit,
                "offset": offset
            }), 200
        
        # 获取所有报告文件
        report_files = []
        for filename in os.listdir(reports_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(reports_dir, filename)
                report_files.append((file_path, os.path.getmtime(file_path)))
        
        # 按修改时间降序排序
        report_files.sort(key=lambda x: x[1], reverse=True)
        
        # 读取和过滤报告
        reports = []
        for file_path, _ in report_files:
            try:
                report = storage_manager._read_json_file(file_path, storage_manager._reports_lock)
                if not report:
                    continue
                
                # 应用过滤器
                if status_filter and report.get('status') != status_filter:
                    continue
                if task_id_filter and report.get('task_id') != task_id_filter:
                    continue
                
                # 只返回基本信息
                report_summary = {
                    "report_id": report.get('report_id'),
                    "task_id": report.get('task_id'),
                    "status": report.get('status'),
                    "created_at": report.get('timestamps', {}).get('created_at'),
                    "started_at": report.get('timestamps', {}).get('started_at'),
                    "finished_at": report.get('timestamps', {}).get('finished_at'),
                    "trigger_context": report.get('trigger_context', {})
                }
                reports.append(report_summary)
                
            except Exception as e:
                logger.warning(f"Failed to read report file {file_path}: {e}")
                continue
        
        # 分页
        total_count = len(reports)
        paginated_reports = reports[offset:offset + limit]
        
        return jsonify({
            "reports": paginated_reports,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@reports_bp.route('/reports/<report_id>/logs', methods=['GET'])
def get_report_logs(report_id):
    """获取报告的执行日志
    
    GET /api/v1/reports/<report_id>/logs
    
    Response:
    {
        "execution_log": {...},
        "step_details": [...]
    }
    """
    try:
        storage_manager = StorageManager()
        report = storage_manager.get_report(report_id)
        
        if not report:
            return jsonify({
                "error": "Report not found",
                "message": f"Report with ID '{report_id}' does not exist"
            }), 404
        
        execution_log = report.get('execution_log')
        if not execution_log:
            return jsonify({
                "execution_log": None,
                "message": "No execution log available"
            }), 200
        
        # 格式化步骤详情
        step_details = []
        if execution_log.get('step_results'):
            for step_result in execution_log['step_results']:
                step_detail = {
                    "step_id": step_result.get('step_id'),
                    "status": step_result.get('status'),
                    "started_at": step_result.get('started_at'),
                    "finished_at": step_result.get('finished_at'),
                    "tool_name": step_result.get('mcp_request', {}).get('tool_name'),
                    "parameters": step_result.get('mcp_request', {}).get('params'),
                    "output": step_result.get('mcp_response', {}).get('output'),
                    "error": step_result.get('mcp_response', {}).get('error'),
                    "execution_time": step_result.get('mcp_response', {}).get('execution_time')
                }
                step_details.append(step_detail)
        
        return jsonify({
            "execution_log": execution_log,
            "step_details": step_details
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving report logs {report_id}: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


def _calculate_progress(report: dict) -> dict:
    """计算任务执行进度"""
    progress = {
        "current_step": None,
        "total_steps": 0,
        "completed_steps": 0,
        "percentage": 0
    }
    
    # 从计划中获取总步数
    plan = report.get('plan')
    if plan and plan.get('steps'):
        progress["total_steps"] = len(plan['steps'])
    
    # 从执行日志中获取完成的步数
    execution_log = report.get('execution_log')
    if execution_log and execution_log.get('step_results'):
        step_results = execution_log['step_results']
        completed_count = 0
        current_step = None
        
        for step_result in step_results:
            if step_result.get('status') in ['success', 'failed']:
                completed_count += 1
            elif step_result.get('status') == 'running':
                current_step = step_result.get('step_id')
        
        progress["completed_steps"] = completed_count
        progress["current_step"] = current_step
        
        # 计算百分比
        if progress["total_steps"] > 0:
            progress["percentage"] = round(
                (completed_count / progress["total_steps"]) * 100, 1
            )
    
    return progress


@reports_bp.errorhandler(404)
def not_found(error):
    """处理404错误"""
    return jsonify({
        "error": "Not found",
        "message": "The requested resource was not found"
    }), 404


@reports_bp.errorhandler(500)
def internal_error(error):
    """处理500错误"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500