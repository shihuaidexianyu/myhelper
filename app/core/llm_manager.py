"""
大语言模型管理器 - 与LLM服务通信的"翻译官"
"""

import requests
import logging
from typing import Dict, Any, Optional, List
import time
import json

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """LLM调用异常"""
    pass


class LLMManager:
    """大语言模型管理器 - 统一管理对LLM的API调用"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.session = requests.Session()
        
        # 设置默认超时
        self.default_timeout = 60
        
        # 请求计数和速率限制
        self.request_count = 0
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 最小请求间隔（秒）
        
        logger.info("LLMManager初始化完成")
    
    def _get_llm_config(self) -> Dict[str, Any]:
        """获取LLM配置"""
        config = self.config_manager.get_llm_config()
        if not config:
            raise LLMError("未找到LLM配置")
        return config
    
    def _rate_limit(self):
        """简单的速率限制"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _prepare_openai_request(self, messages: List[Dict[str, str]], 
                               config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """准备OpenAI格式的请求"""
        request_data = {
            "model": kwargs.get('model', config.get('model', 'gpt-3.5-turbo')),
            "messages": messages,
            "max_tokens": kwargs.get('max_tokens', config.get('max_tokens', 4000)),
            "temperature": kwargs.get('temperature', config.get('temperature', 0.7)),
            "stream": False
        }
        
        # 添加其他可选参数
        optional_params = ['top_p', 'frequency_penalty', 'presence_penalty', 'stop']
        for param in optional_params:
            if param in kwargs:
                request_data[param] = kwargs[param]
            elif param in config:
                request_data[param] = config[param]
        
        return request_data
    
    def _call_openai_api(self, messages: List[Dict[str, str]], 
                        config: Dict[str, Any], **kwargs) -> str:
        """调用OpenAI API"""
        api_base = config.get('api_base', 'https://api.openai.com/v1')
        api_key = config.get('api_key')
        
        if not api_key:
            raise LLMError("未配置OpenAI API Key")
        
        url = f"{api_base.rstrip('/')}/chat/completions"
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        request_data = self._prepare_openai_request(messages, config, **kwargs)
        
        try:
            # 速率限制
            self._rate_limit()
            
            logger.debug(f"调用OpenAI API: {url}")
            start_time = time.time()
            
            response = self.session.post(
                url=url,
                headers=headers,
                json=request_data,
                timeout=kwargs.get('timeout', self.default_timeout)
            )
            
            duration = time.time() - start_time
            self.request_count += 1
            
            response.raise_for_status()
            result = response.json()
            
            if 'choices' not in result or not result['choices']:
                raise LLMError("OpenAI API返回格式错误")
            
            content = result['choices'][0]['message']['content']
            
            # 记录使用统计
            usage = result.get('usage', {})
            logger.info(f"OpenAI API调用成功 - 耗时: {duration:.2f}s, "
                       f"Token: {usage.get('total_tokens', 0)}")
            
            return content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API请求失败: {e}")
            raise LLMError(f"OpenAI API请求失败: {e}")
        except Exception as e:
            logger.error(f"OpenAI API调用异常: {e}")
            raise LLMError(f"OpenAI API调用异常: {e}")
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """聊天补全 - 主要接口"""
        try:
            config = self._get_llm_config()
            provider = config.get('provider', 'openai').lower()
            
            if provider == 'openai':
                return self._call_openai_api(messages, config, **kwargs)
            else:
                raise LLMError(f"不支持的LLM提供商: {provider}")
                
        except Exception as e:
            logger.error(f"LLM聊天补全失败: {e}")
            raise
    
    def simple_chat(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """简单聊天接口"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        return self.chat_completion(messages, **kwargs)
    
    def analyze_task(self, natural_language_goal: str) -> Dict[str, Any]:
        """分析任务目标，生成结构化的子任务图"""
        system_prompt = """你是一个智能任务规划助手。你的职责是将用户的自然语言目标分解为结构化的、带依赖关系的子任务图。

请按照以下JSON格式返回结果：
{
  "analysis": "对用户目标的理解和分析",
  "subtasks": [
    {
      "subtask_id": "task_1", 
      "subagent_name": "agent类型名称",
      "goal": "具体的子任务描述",
      "dependencies": []
    },
    {
      "subtask_id": "task_2",
      "subagent_name": "agent类型名称", 
      "goal": "具体的子任务描述",
      "dependencies": ["task_1"]
    }
  ]
}

可用的agent类型：
- DataQueryAgent: 数据查询和分析
- NotificationAgent: 发送通知
- ReportAgent: 生成报告
- ActionAgent: 执行具体动作
- ValidationAgent: 验证和检查

请确保：
1. 子任务之间的依赖关系合理
2. 每个子任务都有明确的目标
3. 选择合适的agent类型
4. 返回有效的JSON格式"""

        try:
            response = self.simple_chat(
                prompt=natural_language_goal,
                system_prompt=system_prompt,
                temperature=0.3  # 降低随机性以获得更一致的结果
            )
            
            # 尝试解析JSON响应
            try:
                # 清理响应文本，提取JSON部分
                response = response.strip()
                if response.startswith('```json'):
                    response = response[7:]
                if response.endswith('```'):
                    response = response[:-3]
                response = response.strip()
                
                result = json.loads(response)
                
                # 验证结果格式
                if 'subtasks' not in result:
                    raise ValueError("缺少subtasks字段")
                
                for subtask in result['subtasks']:
                    required_fields = ['subtask_id', 'subagent_name', 'goal', 'dependencies']
                    for field in required_fields:
                        if field not in subtask:
                            raise ValueError(f"子任务缺少必要字段: {field}")
                
                return result
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"LLM返回的JSON格式无效: {e}")
                logger.error(f"原始响应: {response}")
                
                # 返回一个默认的任务分解
                return {
                    "analysis": f"任务分析: {natural_language_goal}",
                    "subtasks": [
                        {
                            "subtask_id": "task_1",
                            "subagent_name": "ActionAgent",
                            "goal": natural_language_goal,
                            "dependencies": []
                        }
                    ]
                }
                
        except Exception as e:
            logger.error(f"任务分析失败: {e}")
            raise LLMError(f"任务分析失败: {e}")
    
    def generate_summary(self, mission_data: Dict[str, Any]) -> str:
        """生成任务总结"""
        system_prompt = """你是一个专业的任务总结助手。请根据任务的执行结果生成简洁、清晰的中文总结。

总结应该包括：
1. 任务的主要目标
2. 执行的关键步骤
3. 主要结果和成果
4. 如果有问题，说明遇到的困难

请用专业但易懂的语言，控制在200字以内。"""

        try:
            # 构建任务信息
            goal = mission_data.get('natural_language_goal', '未知任务')
            status = mission_data.get('status', '未知状态')
            subtasks = mission_data.get('subtask_graph', [])
            
            # 统计子任务执行情况
            completed_count = len([t for t in subtasks if t.get('status') == 'completed'])
            failed_count = len([t for t in subtasks if t.get('status') == 'failed'])
            
            prompt = f"""任务信息：
目标：{goal}
状态：{status}
子任务总数：{len(subtasks)}
已完成：{completed_count}
失败：{failed_count}

子任务详情：
"""
            
            for i, subtask in enumerate(subtasks[:5], 1):  # 只显示前5个子任务
                task_status = subtask.get('status', '未知')
                task_goal = subtask.get('goal', '未知')
                prompt += f"{i}. {task_goal} - {task_status}\n"
            
            if len(subtasks) > 5:
                prompt += f"... 还有{len(subtasks) - 5}个子任务\n"
            
            response = self.simple_chat(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=500
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"生成任务总结失败: {e}")
            return f"任务：{mission_data.get('natural_language_goal', '未知任务')} - 状态：{mission_data.get('status', '未知状态')}"
    
    def validate_response(self, response: str, expected_format: str) -> bool:
        """验证LLM响应格式"""
        try:
            if expected_format.lower() == 'json':
                json.loads(response)
                return True
            # 可以添加其他格式验证
            return True
        except:
            return False
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        return {
            'total_requests': self.request_count,
            'last_request_time': self.last_request_time,
            'rate_limit_interval': self.min_request_interval
        }
    
    def test_connection(self) -> bool:
        """测试LLM连接"""
        try:
            response = self.simple_chat(
                prompt="Hello, please respond with 'OK' to confirm the connection.",
                max_tokens=10,
                timeout=10
            )
            return 'OK' in response.upper()
        except:
            return False