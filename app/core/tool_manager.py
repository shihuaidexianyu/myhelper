"""
工具管理器 - MCP服务网关
系统与外部世界交互的"唯一安全门"
"""

import requests
import logging
from typing import Dict, Any, Optional, List
import time
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class MCPServiceError(Exception):
    """MCP服务调用异常"""
    pass


class ToolManager:
    """工具管理器 - 负责安全地调用外部MCP服务"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.session = requests.Session()
        
        # 设置默认超时
        self.default_timeout = 30
        
        # 设置通用请求头
        self.session.headers.update({
            'User-Agent': 'MyHelper/0.1.0',
            'Content-Type': 'application/json'
        })
        
        logger.info("ToolManager初始化完成")
    
    def _get_service_config(self, service_name: str) -> Dict[str, Any]:
        """获取MCP服务配置"""
        config = self.config_manager.get_mcp_service_config(service_name)
        if not config:
            raise MCPServiceError(f"未找到MCP服务配置: {service_name}")
        return config
    
    def _prepare_request_headers(self, service_config: Dict[str, Any]) -> Dict[str, str]:
        """准备请求头"""
        headers = {}
        
        # 添加API Key
        api_key = service_config.get('api_key')
        if api_key:
            auth_type = service_config.get('auth_type', 'bearer')
            if auth_type.lower() == 'bearer':
                headers['Authorization'] = f'Bearer {api_key}'
            elif auth_type.lower() == 'apikey':
                headers['X-API-Key'] = api_key
            else:
                headers['Authorization'] = f'{auth_type} {api_key}'
        
        # 添加其他自定义头
        custom_headers = service_config.get('headers', {})
        headers.update(custom_headers)
        
        return headers
    
    def _handle_response(self, response: requests.Response, service_name: str) -> Dict[str, Any]:
        """处理响应"""
        try:
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                return response.json()
            else:
                return {
                    'status': 'success',
                    'data': response.text,
                    'content_type': content_type
                }
                
        except requests.exceptions.HTTPError as e:
            error_msg = f"MCP服务HTTP错误 {service_name}: {e}"
            logger.error(error_msg)
            
            # 尝试解析错误响应
            try:
                error_data = response.json()
                raise MCPServiceError(f"{error_msg}, 详情: {error_data}")
            except:
                raise MCPServiceError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"MCP服务请求错误 {service_name}: {e}"
            logger.error(error_msg)
            raise MCPServiceError(error_msg)
    
    def call_service(self, service_name: str, endpoint: str, 
                    method: str = 'POST', data: Optional[Dict] = None,
                    params: Optional[Dict] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
        """调用MCP服务"""
        try:
            # 获取服务配置
            service_config = self._get_service_config(service_name)
            
            # 构建URL
            base_url = service_config['url']
            full_url = urljoin(base_url, endpoint)
            
            # 准备请求头
            headers = self._prepare_request_headers(service_config)
            
            # 设置超时
            request_timeout = timeout or service_config.get('timeout', self.default_timeout)
            
            # 发送请求
            logger.info(f"调用MCP服务: {service_name} - {method} {full_url}")
            
            start_time = time.time()
            
            response = self.session.request(
                method=method.upper(),
                url=full_url,
                json=data if method.upper() in ['POST', 'PUT', 'PATCH'] else None,
                params=params,
                headers=headers,
                timeout=request_timeout
            )
            
            duration = time.time() - start_time
            logger.info(f"MCP服务调用完成: {service_name} - 耗时 {duration:.2f}s")
            
            # 处理响应
            return self._handle_response(response, service_name)
            
        except Exception as e:
            logger.error(f"MCP服务调用失败: {service_name} - {e}")
            raise
    
    def call_with_retry(self, service_name: str, endpoint: str,
                       method: str = 'POST', data: Optional[Dict] = None,
                       params: Optional[Dict] = None, timeout: Optional[int] = None,
                       max_retries: int = 3, retry_delay: float = 1.0) -> Dict[str, Any]:
        """带重试的MCP服务调用"""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return self.call_service(service_name, endpoint, method, data, params, timeout)
                
            except MCPServiceError as e:
                last_exception = e
                
                if attempt < max_retries:
                    # 计算退避延迟（指数退避）
                    delay = retry_delay * (2 ** attempt)
                    logger.warning(f"MCP服务调用失败，{delay}s后重试 (第{attempt + 1}次): {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"MCP服务调用重试次数用尽: {service_name}")
                    break
        
        # 重试失败，抛出最后的异常
        raise last_exception
    
    def get_available_services(self) -> List[str]:
        """获取可用的MCP服务列表"""
        mcp_services = self.config_manager.get('mcp_services', {})
        return list(mcp_services.keys())
    
    def check_service_health(self, service_name: str) -> Dict[str, Any]:
        """检查MCP服务健康状态"""
        try:
            service_config = self._get_service_config(service_name)
            
            # 尝试调用健康检查端点
            health_endpoint = service_config.get('health_endpoint', '/health')
            
            start_time = time.time()
            result = self.call_service(
                service_name=service_name,
                endpoint=health_endpoint,
                method='GET',
                timeout=10  # 健康检查使用较短超时
            )
            duration = time.time() - start_time
            
            return {
                'service': service_name,
                'status': 'healthy',
                'response_time': duration,
                'details': result
            }
            
        except Exception as e:
            return {
                'service': service_name,
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def check_all_services_health(self) -> Dict[str, Dict[str, Any]]:
        """检查所有MCP服务的健康状态"""
        services = self.get_available_services()
        health_status = {}
        
        for service_name in services:
            health_status[service_name] = self.check_service_health(service_name)
        
        return health_status
    
    # 常用的MCP服务调用方法
    
    def query_data(self, service_name: str, query: Dict[str, Any]) -> Dict[str, Any]:
        """查询数据"""
        return self.call_with_retry(
            service_name=service_name,
            endpoint='/query',
            method='POST',
            data=query
        )
    
    def send_notification(self, service_name: str, notification: Dict[str, Any]) -> Dict[str, Any]:
        """发送通知"""
        return self.call_with_retry(
            service_name=service_name,
            endpoint='/notify',
            method='POST',
            data=notification
        )
    
    def execute_action(self, service_name: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """执行动作"""
        return self.call_with_retry(
            service_name=service_name,
            endpoint='/execute',
            method='POST',
            data=action
        )
    
    def get_service_capabilities(self, service_name: str) -> Dict[str, Any]:
        """获取服务能力"""
        try:
            return self.call_service(
                service_name=service_name,
                endpoint='/capabilities',
                method='GET'
            )
        except:
            # 如果服务不支持capabilities端点，返回基本信息
            service_config = self._get_service_config(service_name)
            return {
                'service': service_name,
                'url': service_config['url'],
                'endpoints': ['query', 'notify', 'execute']  # 默认端点
            }
    
    def validate_service_config(self, service_name: str) -> bool:
        """验证服务配置"""
        try:
            service_config = self._get_service_config(service_name)
            
            # 检查必要字段
            required_fields = ['url']
            for field in required_fields:
                if field not in service_config:
                    logger.error(f"MCP服务配置缺少必要字段 {service_name}: {field}")
                    return False
            
            # 检查URL格式
            url = service_config['url']
            if not url.startswith(('http://', 'https://')):
                logger.error(f"MCP服务URL格式无效 {service_name}: {url}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"MCP服务配置验证失败 {service_name}: {e}")
            return False
    
    def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        return {
            'total_services': len(self.get_available_services()),
            'session_info': {
                'headers': dict(self.session.headers),
                'timeout': self.default_timeout
            }
        }