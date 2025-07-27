"""
工具管理器与安全网关
MCP的实现者，系统的安全核心，所有具体操作的唯一执行入口
"""
import subprocess
import requests
import importlib
import sys
import json
import time
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import asdict

from app.models.data_models import (
    MCPRequest, MCPResponse, Tool, ToolType, ParameterType, 
    validate_mcp_request
)
from app.core.storage_manager import StorageManager


class ToolManager:
    """工具管理器，处理所有MCP请求的执行"""
    
    def __init__(self, storage_manager: StorageManager):
        self.storage_manager = storage_manager
        self.logger = logging.getLogger(__name__)
    
    def execute_mcp_request(self, request: MCPRequest, authorized_tools: Dict[str, Dict]) -> MCPResponse:
        """执行MCP请求
        
        Args:
            request: MCP请求对象
            authorized_tools: 当前任务授权的工具字典
            
        Returns:
            MCPResponse: 标准化的响应对象
        """
        start_time = time.time()
        
        try:
            # 1. 协议校验
            if request.protocol != "MCP" or request.version != "1.0":
                return MCPResponse(
                    status="failed",
                    error=f"Invalid protocol {request.protocol}/{request.version}",
                    request_id=request.request_id,
                    execution_time=time.time() - start_time
                )
            
            # 2. 权限校验
            if request.tool_name not in authorized_tools:
                return MCPResponse(
                    status="failed",
                    error=f"Tool '{request.tool_name}' not authorized for this task",
                    request_id=request.request_id,
                    execution_time=time.time() - start_time
                )
            
            # 3. 加载工具定义
            tool_def = authorized_tools[request.tool_name]
            tool = self._dict_to_tool(tool_def)
            
            # 4. 参数校验
            validation_errors = validate_mcp_request(request, tool)
            if validation_errors:
                return MCPResponse(
                    status="failed",
                    error=f"Parameter validation failed: {'; '.join(validation_errors)}",
                    request_id=request.request_id,
                    execution_time=time.time() - start_time
                )
            
            # 5. 处理器分发
            if tool.type == ToolType.SHELL_COMMAND:
                result = self._execute_shell_command(tool, request.params)
            elif tool.type == ToolType.HTTP_REQUEST:
                result = self._execute_http_request(tool, request.params)
            elif tool.type == ToolType.PYTHON_FUNCTION:
                result = self._execute_python_function(tool, request.params)
            else:
                return MCPResponse(
                    status="failed",
                    error=f"Unsupported tool type: {tool.type}",
                    request_id=request.request_id,
                    execution_time=time.time() - start_time
                )
            
            # 6. 返回结果
            execution_time = time.time() - start_time
            self.logger.info(f"Tool '{request.tool_name}' executed successfully in {execution_time:.2f}s")
            
            return MCPResponse(
                status="success" if result['success'] else "failed",
                output=result.get('output'),
                error=result.get('error'),
                request_id=request.request_id,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Unexpected error executing tool '{request.tool_name}': {e}")
            
            return MCPResponse(
                status="failed",
                error=f"Unexpected error: {str(e)}",
                request_id=request.request_id,
                execution_time=execution_time
            )
    
    def _dict_to_tool(self, tool_dict: Dict) -> Tool:
        """将字典转换为Tool对象"""
        from app.models.data_models import ToolParameter
        
        parameters = []
        for param_dict in tool_dict.get('parameters', []):
            parameters.append(ToolParameter(
                name=param_dict['name'],
                type=ParameterType(param_dict['type']),
                description=param_dict['description'],
                required=param_dict.get('required', False),
                default=param_dict.get('default')
            ))
        
        return Tool(
            id=tool_dict['id'],
            name=tool_dict['name'],
            type=ToolType(tool_dict['type']),
            description=tool_dict['description'],
            parameters=parameters,
            command=tool_dict.get('command'),
            url=tool_dict.get('url'),
            function=tool_dict.get('function'),
            timeout=tool_dict.get('timeout', 30),
            retry_count=tool_dict.get('retry_count', 0)
        )
    
    def _execute_shell_command(self, tool: Tool, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行shell命令"""
        try:
            # 构建命令，替换参数占位符
            command = tool.command
            for param_name, param_value in params.items():
                placeholder = f"{{{param_name}}}"
                command = command.replace(placeholder, str(param_value))
            
            self.logger.info(f"Executing shell command: {command}")
            
            # 安全执行命令
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=tool.timeout,
                cwd=os.getcwd(),  # 可以根据需要限制工作目录
                env=os.environ.copy()  # 继承环境变量
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'output': result.stdout,
                    'stderr': result.stderr
                }
            else:
                return {
                    'success': False,
                    'output': result.stdout,
                    'error': f"Command failed with exit code {result.returncode}: {result.stderr}"
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f"Command timed out after {tool.timeout} seconds"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Command execution error: {str(e)}"
            }
    
    def _execute_http_request(self, tool: Tool, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行HTTP请求"""
        try:
            # 构建URL，替换参数占位符
            url = tool.url
            headers = params.get('headers', {})
            method = params.get('method', 'GET').upper()
            data = params.get('data')
            json_data = params.get('json')
            
            # 替换URL中的占位符
            for param_name, param_value in params.items():
                if param_name not in ['headers', 'method', 'data', 'json']:
                    placeholder = f"{{{param_name}}}"
                    url = url.replace(placeholder, str(param_value))
            
            self.logger.info(f"Executing HTTP {method} request to: {url}")
            
            # 发送请求
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                json=json_data,
                timeout=tool.timeout
            )
            
            # 检查响应
            if response.status_code < 400:
                return {
                    'success': True,
                    'output': {
                        'status_code': response.status_code,
                        'headers': dict(response.headers),
                        'content': response.text
                    }
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'output': {
                        'status_code': response.status_code,
                        'headers': dict(response.headers),
                        'content': response.text
                    }
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': f"HTTP request timed out after {tool.timeout} seconds"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"HTTP request error: {str(e)}"
            }
    
    def _execute_python_function(self, tool: Tool, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行Python函数"""
        try:
            # 解析函数路径，格式: module.function
            if '.' not in tool.function:
                return {
                    'success': False,
                    'error': f"Invalid function format: {tool.function}. Expected 'module.function'"
                }
            
            module_name, function_name = tool.function.rsplit('.', 1)
            
            self.logger.info(f"Executing Python function: {tool.function}")
            
            # 动态导入模块
            try:
                module = importlib.import_module(module_name)
            except ImportError as e:
                return {
                    'success': False,
                    'error': f"Cannot import module '{module_name}': {str(e)}"
                }
            
            # 获取函数
            if not hasattr(module, function_name):
                return {
                    'success': False,
                    'error': f"Function '{function_name}' not found in module '{module_name}'"
                }
            
            function = getattr(module, function_name)
            
            # 执行函数
            result = function(**params)
            
            return {
                'success': True,
                'output': result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Python function execution error: {str(e)}"
            }