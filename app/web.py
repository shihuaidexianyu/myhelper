"""
Web Interface Blueprint
提供基于Jinja2的可视化配置界面
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
import json
import os
from app.core.storage_manager import StorageManager

web_bp = Blueprint('web', __name__)

@web_bp.route('/')
def index():
    """主页"""
    return render_template('index.html')

@web_bp.route('/tasks')
def tasks():
    """任务管理页面"""
    storage_manager = StorageManager()
    tasks_file = storage_manager._read_json_file(
        storage_manager.data_dir + '/tasks.json',
        storage_manager._tasks_lock
    )
    return render_template('tasks.html', tasks=tasks_file)

@web_bp.route('/tools')
def tools():
    """工具管理页面"""
    storage_manager = StorageManager()
    tools_file = storage_manager._read_json_file(
        storage_manager.data_dir + '/tools.json',
        storage_manager._tools_lock
    )
    return render_template('tools.html', tools=tools_file)

@web_bp.route('/reports')
def reports():
    """报告查看页面"""
    storage_manager = StorageManager()
    reports_dir = os.path.join(storage_manager.data_dir, 'reports')
    
    reports = []
    if os.path.exists(reports_dir):
        for filename in os.listdir(reports_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(reports_dir, filename)
                try:
                    report = storage_manager._read_json_file(file_path, storage_manager._reports_lock)
                    if report:
                        reports.append({
                            'report_id': report.get('report_id'),
                            'task_id': report.get('task_id'),
                            'status': report.get('status'),
                            'created_at': report.get('timestamps', {}).get('created_at'),
                            'finished_at': report.get('timestamps', {}).get('finished_at')
                        })
                except Exception:
                    continue
    
    # 按创建时间排序
    reports.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return render_template('reports.html', reports=reports)

@web_bp.route('/report/<report_id>')
def report_detail(report_id):
    """报告详情页面"""
    storage_manager = StorageManager()
    report = storage_manager.get_report(report_id)
    
    if not report:
        flash('报告不存在', 'error')
        return redirect(url_for('web.reports'))
    
    return render_template('report_detail.html', report=report)

@web_bp.route('/task/new')
def new_task():
    """新建任务页面"""
    storage_manager = StorageManager()
    tools_file = storage_manager._read_json_file(
        storage_manager.data_dir + '/tools.json',
        storage_manager._tools_lock
    )
    return render_template('task_form.html', tools=tools_file, task=None)

@web_bp.route('/task/<task_id>/edit')
def edit_task(task_id):
    """编辑任务页面"""
    storage_manager = StorageManager()
    task = storage_manager.get_task(task_id)
    
    if not task:
        flash('任务不存在', 'error')
        return redirect(url_for('web.tasks'))
    
    tools_file = storage_manager._read_json_file(
        storage_manager.data_dir + '/tools.json',
        storage_manager._tools_lock
    )
    return render_template('task_form.html', tools=tools_file, task=task, task_id=task_id)

@web_bp.route('/task/save', methods=['POST'])
def save_task():
    """保存任务"""
    try:
        task_id = request.form.get('task_id')
        name = request.form.get('name')
        description = request.form.get('description')
        goal = request.form.get('goal')
        authorized_tool_ids = request.form.getlist('authorized_tool_ids')
        
        if not all([name, description, goal]):
            flash('请填写所有必需字段', 'error')
            return redirect(request.referrer)
        
        storage_manager = StorageManager()
        
        if task_id:
            # 更新现有任务
            storage_manager.update_task(task_id, {
                'name': name,
                'description': description,
                'goal': goal,
                'authorized_tool_ids': authorized_tool_ids
            })
            flash('任务更新成功', 'success')
        else:
            # 创建新任务
            new_task_id = storage_manager.create_task(
                name=name,
                description=description,
                goal=goal,
                authorized_tool_ids=authorized_tool_ids
            )
            flash(f'任务创建成功，ID: {new_task_id}', 'success')
        
        return redirect(url_for('web.tasks'))
        
    except Exception as e:
        flash(f'保存失败: {str(e)}', 'error')
        return redirect(request.referrer)

@web_bp.route('/task/<task_id>/delete', methods=['POST'])
def delete_task(task_id):
    """删除任务"""
    try:
        storage_manager = StorageManager()
        storage_manager.delete_task(task_id)
        flash('任务删除成功', 'success')
    except Exception as e:
        flash(f'删除失败: {str(e)}', 'error')
    
    return redirect(url_for('web.tasks'))

@web_bp.route('/tool/save', methods=['POST'])
def save_tool():
    """保存工具配置"""
    try:
        tool_id = request.form.get('tool_id')
        name = request.form.get('name')
        description = request.form.get('description')
        command_template = request.form.get('command_template')
        
        if not all([tool_id, name, description, command_template]):
            flash('请填写所有必需字段', 'error')
            return redirect(request.referrer)
        
        storage_manager = StorageManager()
        
        # 读取当前工具配置
        tools_file = storage_manager._read_json_file(
            storage_manager.data_dir + '/tools.json',
            storage_manager._tools_lock
        )
        
        tools_file[tool_id] = {
            'name': name,
            'description': description,
            'command_template': command_template
        }
        
        # 保存工具配置
        storage_manager._write_json_file(
            storage_manager.data_dir + '/tools.json',
            tools_file,
            storage_manager._tools_lock
        )
        
        flash('工具配置保存成功', 'success')
        return redirect(url_for('web.tools'))
        
    except Exception as e:
        flash(f'保存失败: {str(e)}', 'error')
        return redirect(request.referrer)