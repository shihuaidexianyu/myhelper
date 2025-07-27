"""
Hooks API Blueprint
定义所有任务触发相关的HTTP接口
"""
from flask import Blueprint, request, jsonify, current_app
import logging

from app.core.storage_manager import StorageManager
from app.agents.master_agent import run_master_agent_task


hooks_bp = Blueprint('hooks', __name__)
logger = logging.getLogger(__name__)


@hooks_bp.route('/hooks/<task_id>', methods=['POST'])
def trigger_task(task_id):
    """触发任务执行
    
    POST /api/v1/hooks/<task_id>
    
    Request Body:
    {
        "trigger_context": {
            "branch": "main",
            "commit_hash": "abc123",
            "environment": "production",
            ...
        }
    }
    
    Response:
    {
        "status": "queued",
        "report_id": "uuid",
        "message": "Task queued successfully"
    }
    """
    try:
        # 1. 解析请求数据
        request_data = request.get_json() or {}
        trigger_context = request_data.get('trigger_context', {})
        
        logger.info(f"Received task trigger request for task_id: {task_id}")
        
        # 2. 验证任务存在
        storage_manager = StorageManager()
        task = storage_manager.get_task(task_id)
        
        if not task:
            logger.warning(f"Task {task_id} not found")
            return jsonify({
                "error": "Task not found",
                "message": f"Task with ID '{task_id}' does not exist"
            }), 404
        
        # 3. 创建初始报告
        report_id = storage_manager.create_report(task_id, trigger_context)
        logger.info(f"Created report {report_id} for task {task_id}")
        
        # 4. 提交后台任务
        thread_pool = current_app.thread_pool
        future = thread_pool.submit(
            run_master_agent_task,
            task_id=task_id,
            trigger_context=trigger_context,
            report_id=report_id
        )
        
        logger.info(f"Submitted task {task_id} to thread pool, report_id: {report_id}")
        
        # 5. 立即响应
        return jsonify({
            "status": "queued",
            "report_id": report_id,
            "message": f"Task '{task_id}' queued successfully"
        }), 202
        
    except Exception as e:
        logger.error(f"Error processing task trigger for {task_id}: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@hooks_bp.route('/hooks/<task_id>/validate', methods=['POST'])
def validate_task_trigger(task_id):
    """验证任务触发请求
    
    POST /api/v1/hooks/<task_id>/validate
    
    用于验证任务是否存在、参数是否正确，但不实际执行任务
    """
    try:
        # 解析请求数据
        request_data = request.get_json() or {}
        trigger_context = request_data.get('trigger_context', {})
        
        logger.info(f"Validating task trigger for task_id: {task_id}")
        
        # 验证任务存在
        storage_manager = StorageManager()
        task = storage_manager.get_task(task_id)
        
        if not task:
            return jsonify({
                "valid": False,
                "error": "Task not found",
                "message": f"Task with ID '{task_id}' does not exist"
            }), 404
        
        # 验证授权工具
        authorized_tool_ids = task.get('authorized_tool_ids', [])
        authorized_tools = storage_manager.get_authorized_tools(authorized_tool_ids)
        
        validation_result = {
            "valid": True,
            "task_id": task_id,
            "task_name": task.get('name'),
            "task_description": task.get('description'),
            "authorized_tools_count": len(authorized_tools),
            "authorized_tools": list(authorized_tools.keys()),
            "trigger_context": trigger_context
        }
        
        # 检查是否有无效的工具
        missing_tools = set(authorized_tool_ids) - set(authorized_tools.keys())
        if missing_tools:
            validation_result["warnings"] = [
                f"Tools not found in tools.json: {', '.join(missing_tools)}"
            ]
        
        logger.info(f"Task validation completed for {task_id}")
        return jsonify(validation_result), 200
        
    except Exception as e:
        logger.error(f"Error validating task trigger for {task_id}: {e}")
        return jsonify({
            "valid": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500


@hooks_bp.route('/hooks', methods=['GET'])
def list_available_tasks():
    """列出所有可用的任务
    
    GET /api/v1/hooks
    
    Response:
    {
        "tasks": [
            {
                "id": "task1",
                "name": "Task 1",
                "description": "Description",
                "authorized_tools_count": 3
            }
        ]
    }
    """
    try:
        storage_manager = StorageManager()
        
        # 读取所有任务
        tasks_file = storage_manager._read_json_file(
            storage_manager.data_dir + '/tasks.json',
            storage_manager._tasks_lock
        )
        
        task_list = []
        for task_id, task_data in tasks_file.items():
            authorized_tools = storage_manager.get_authorized_tools(
                task_data.get('authorized_tool_ids', [])
            )
            
            task_info = {
                "id": task_id,
                "name": task_data.get('name', task_id),
                "description": task_data.get('description', ''),
                "authorized_tools_count": len(authorized_tools),
                "authorized_tools": list(authorized_tools.keys()),
                "created_at": task_data.get('created_at'),
                "updated_at": task_data.get('updated_at')
            }
            task_list.append(task_info)
        
        return jsonify({
            "tasks": task_list,
            "total_count": len(task_list)
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing available tasks: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@hooks_bp.errorhandler(400)
def bad_request(error):
    """处理400错误"""
    return jsonify({
        "error": "Bad request",
        "message": "Invalid request format or parameters"
    }), 400


@hooks_bp.errorhandler(404)
def not_found(error):
    """处理404错误"""
    return jsonify({
        "error": "Not found",
        "message": "The requested resource was not found"
    }), 404


@hooks_bp.errorhandler(500)
def internal_error(error):
    """处理500错误"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500