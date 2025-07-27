"""
规划代理
负责根据任务定义、触发上下文和历史学习生成执行计划
"""
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.models.data_models import Plan, PlanStep, Learning


class PlannerAgent:
    """规划代理，生成任务执行计划"""
    
    def __init__(self, task: Dict[str, Any], trigger_context: Dict[str, Any], 
                 learnings: List[Learning] = None):
        self.task = task
        self.trigger_context = trigger_context
        self.learnings = learnings or []
        self.logger = logging.getLogger(__name__)
    
    def generate_plan(self) -> Plan:
        """生成执行计划
        
        Returns:
            Plan: 完整的执行计划
        """
        self.logger.info(f"Generating plan for task: {self.task['id']}")
        
        # 分析任务需求
        task_analysis = self._analyze_task()
        
        # 应用历史学习
        learned_insights = self._apply_learnings()
        
        # 生成基础计划步骤
        base_steps = self._generate_base_steps(task_analysis)
        
        # 应用学习优化
        optimized_steps = self._optimize_steps_with_learnings(base_steps, learned_insights)
        
        # 添加依赖关系
        final_steps = self._add_dependencies(optimized_steps)
        
        # 创建计划对象
        plan = Plan(
            plan_id=str(uuid.uuid4()),
            task_id=self.task['id'],
            steps=final_steps,
            created_at=datetime.utcnow().isoformat(),
            reasoning=self._generate_reasoning(task_analysis, learned_insights)
        )
        
        self.logger.info(f"Generated plan with {len(final_steps)} steps for task {self.task['id']}")
        return plan
    
    def _analyze_task(self) -> Dict[str, Any]:
        """分析任务需求"""
        analysis = {
            'task_type': self._determine_task_type(),
            'complexity': self._assess_complexity(),
            'required_tools': self.task.get('authorized_tool_ids', []),
            'trigger_context': self.trigger_context,
            'success_criteria': self._define_success_criteria()
        }
        
        return analysis
    
    def _determine_task_type(self) -> str:
        """确定任务类型"""
        task_name = self.task.get('name', '').lower()
        task_desc = self.task.get('description', '').lower()
        
        # 基于关键词判断任务类型
        if any(keyword in task_name + task_desc for keyword in ['deploy', 'deployment', '部署']):
            return 'deployment'
        elif any(keyword in task_name + task_desc for keyword in ['test', 'testing', '测试']):
            return 'testing'
        elif any(keyword in task_name + task_desc for keyword in ['build', 'compile', '构建']):
            return 'build'
        elif any(keyword in task_name + task_desc for keyword in ['backup', '备份']):
            return 'backup'
        elif any(keyword in task_name + task_desc for keyword in ['monitor', 'monitoring', '监控']):
            return 'monitoring'
        else:
            return 'general'
    
    def _assess_complexity(self) -> str:
        """评估任务复杂度"""
        tool_count = len(self.task.get('authorized_tool_ids', []))
        
        if tool_count <= 2:
            return 'simple'
        elif tool_count <= 5:
            return 'medium'
        else:
            return 'complex'
    
    def _define_success_criteria(self) -> List[str]:
        """定义成功标准"""
        # 基于任务类型定义通用成功标准
        task_type = self._determine_task_type()
        
        criteria_map = {
            'deployment': [
                'Application deployed successfully',
                'Health checks pass',
                'No critical errors in logs'
            ],
            'testing': [
                'All tests pass',
                'No test failures or errors',
                'Coverage meets requirements'
            ],
            'build': [
                'Build completes without errors',
                'All artifacts generated',
                'Build output is valid'
            ],
            'backup': [
                'Backup created successfully',
                'Backup integrity verified',
                'Backup stored in designated location'
            ],
            'monitoring': [
                'Monitoring checks complete',
                'All metrics collected',
                'Alerts configured if needed'
            ],
            'general': [
                'Task completes without critical errors',
                'Expected output generated',
                'System remains stable'
            ]
        }
        
        return criteria_map.get(task_type, criteria_map['general'])
    
    def _apply_learnings(self) -> Dict[str, Any]:
        """应用历史学习经验"""
        insights = {
            'success_patterns': [],
            'failure_patterns': [],
            'optimizations': [],
            'warnings': []
        }
        
        for learning in self.learnings:
            # 筛选相关的学习经验
            if self._is_learning_relevant(learning):
                if learning.category == 'success_pattern':
                    insights['success_patterns'].append(learning)
                elif learning.category == 'failure_analysis':
                    insights['failure_patterns'].append(learning)
                elif learning.category == 'optimization':
                    insights['optimizations'].append(learning)
        
        return insights
    
    def _is_learning_relevant(self, learning: Learning) -> bool:
        """判断学习经验是否与当前任务相关"""
        # 简单的相关性判断，可以根据需要扩展
        learning_context = learning.context
        
        # 检查任务类型匹配
        if learning_context.get('task_type') == self._determine_task_type():
            return True
        
        # 检查工具匹配
        learning_tools = set(learning_context.get('tools_used', []))
        current_tools = set(self.task.get('authorized_tool_ids', []))
        if learning_tools & current_tools:  # 有交集
            return True
        
        return False
    
    def _generate_base_steps(self, task_analysis: Dict[str, Any]) -> List[PlanStep]:
        """生成基础计划步骤"""
        steps = []
        task_type = task_analysis['task_type']
        authorized_tools = task_analysis['required_tools']
        
        # 根据任务类型生成标准步骤模板
        if task_type == 'deployment':
            steps.extend(self._generate_deployment_steps(authorized_tools))
        elif task_type == 'testing':
            steps.extend(self._generate_testing_steps(authorized_tools))
        elif task_type == 'build':
            steps.extend(self._generate_build_steps(authorized_tools))
        elif task_type == 'backup':
            steps.extend(self._generate_backup_steps(authorized_tools))
        elif task_type == 'monitoring':
            steps.extend(self._generate_monitoring_steps(authorized_tools))
        else:
            steps.extend(self._generate_general_steps(authorized_tools))
        
        return steps
    
    def _generate_deployment_steps(self, tools: List[str]) -> List[PlanStep]:
        """生成部署任务步骤"""
        steps = []
        
        # 预部署检查
        if 'git_pull' in tools:
            steps.append(PlanStep(
                step_id="pre_deploy_git_pull",
                description="Pull latest code from repository",
                tool_name="git_pull",
                parameters={"branch": self.trigger_context.get("branch", "main")},
                critical=True
            ))
        
        # 构建步骤
        if 'build_app' in tools:
            steps.append(PlanStep(
                step_id="build_application",
                description="Build application",
                tool_name="build_app",
                parameters={},
                depends_on=["pre_deploy_git_pull"] if 'git_pull' in tools else [],
                critical=True
            ))
        
        # 部署步骤
        if 'deploy_app' in tools:
            steps.append(PlanStep(
                step_id="deploy_application",
                description="Deploy application to target environment",
                tool_name="deploy_app",
                parameters={"environment": self.trigger_context.get("environment", "production")},
                depends_on=["build_application"] if 'build_app' in tools else [],
                critical=True
            ))
        
        # 健康检查
        if 'health_check' in tools:
            steps.append(PlanStep(
                step_id="post_deploy_health_check",
                description="Perform health check after deployment",
                tool_name="health_check",
                parameters={"timeout": 60},
                depends_on=["deploy_application"] if 'deploy_app' in tools else [],
                critical=True
            ))
        
        return steps
    
    def _generate_testing_steps(self, tools: List[str]) -> List[PlanStep]:
        """生成测试任务步骤"""
        steps = []
        
        if 'run_tests' in tools:
            steps.append(PlanStep(
                step_id="execute_tests",
                description="Run test suite",
                tool_name="run_tests",
                parameters={"type": self.trigger_context.get("test_type", "all")},
                critical=True
            ))
        
        if 'generate_test_report' in tools:
            steps.append(PlanStep(
                step_id="generate_report",
                description="Generate test report",
                tool_name="generate_test_report",
                parameters={"format": "html"},
                depends_on=["execute_tests"],
                critical=False
            ))
        
        return steps
    
    def _generate_build_steps(self, tools: List[str]) -> List[PlanStep]:
        """生成构建任务步骤"""
        steps = []
        
        if 'clean_build' in tools:
            steps.append(PlanStep(
                step_id="clean_workspace",
                description="Clean build workspace",
                tool_name="clean_build",
                parameters={},
                critical=False
            ))
        
        if 'compile_code' in tools:
            steps.append(PlanStep(
                step_id="compile_application",
                description="Compile source code",
                tool_name="compile_code",
                parameters={"optimization": self.trigger_context.get("optimization", "release")},
                depends_on=["clean_workspace"] if 'clean_build' in tools else [],
                critical=True
            ))
        
        if 'package_app' in tools:
            steps.append(PlanStep(
                step_id="package_artifacts",
                description="Package build artifacts",
                tool_name="package_app",
                parameters={"format": self.trigger_context.get("package_format", "zip")},
                depends_on=["compile_application"],
                critical=True
            ))
        
        return steps
    
    def _generate_backup_steps(self, tools: List[str]) -> List[PlanStep]:
        """生成备份任务步骤"""
        steps = []
        
        if 'create_backup' in tools:
            steps.append(PlanStep(
                step_id="create_backup",
                description="Create system backup",
                tool_name="create_backup",
                parameters={"type": self.trigger_context.get("backup_type", "full")},
                critical=True
            ))
        
        if 'verify_backup' in tools:
            steps.append(PlanStep(
                step_id="verify_backup_integrity",
                description="Verify backup integrity",
                tool_name="verify_backup",
                parameters={},
                depends_on=["create_backup"],
                critical=True
            ))
        
        return steps
    
    def _generate_monitoring_steps(self, tools: List[str]) -> List[PlanStep]:
        """生成监控任务步骤"""
        steps = []
        
        if 'check_system_health' in tools:
            steps.append(PlanStep(
                step_id="system_health_check",
                description="Check system health metrics",
                tool_name="check_system_health",
                parameters={},
                critical=True
            ))
        
        if 'collect_metrics' in tools:
            steps.append(PlanStep(
                step_id="collect_performance_metrics",
                description="Collect performance metrics",
                tool_name="collect_metrics",
                parameters={"duration": self.trigger_context.get("duration", 300)},
                critical=False
            ))
        
        return steps
    
    def _generate_general_steps(self, tools: List[str]) -> List[PlanStep]:
        """生成通用任务步骤"""
        steps = []
        
        # 为每个授权工具生成一个基本步骤
        for i, tool in enumerate(tools):
            steps.append(PlanStep(
                step_id=f"execute_{tool}_{i+1}",
                description=f"Execute {tool}",
                tool_name=tool,
                parameters=self.trigger_context.get("tool_params", {}).get(tool, {}),
                critical=True
            ))
        
        return steps
    
    def _optimize_steps_with_learnings(self, steps: List[PlanStep], 
                                     insights: Dict[str, Any]) -> List[PlanStep]:
        """基于学习经验优化步骤"""
        optimized_steps = steps.copy()
        
        # 应用成功模式
        for pattern in insights['success_patterns']:
            optimized_steps = self._apply_success_pattern(optimized_steps, pattern)
        
        # 避免失败模式
        for pattern in insights['failure_patterns']:
            optimized_steps = self._avoid_failure_pattern(optimized_steps, pattern)
        
        # 应用优化建议
        for optimization in insights['optimizations']:
            optimized_steps = self._apply_optimization(optimized_steps, optimization)
        
        return optimized_steps
    
    def _apply_success_pattern(self, steps: List[PlanStep], pattern: Learning) -> List[PlanStep]:
        """应用成功模式"""
        # 实现成功模式的应用逻辑
        # 这里可以根据具体的学习内容调整步骤
        return steps
    
    def _avoid_failure_pattern(self, steps: List[PlanStep], pattern: Learning) -> List[PlanStep]:
        """避免失败模式"""
        # 实现失败模式的避免逻辑
        # 例如添加额外的验证步骤、调整参数等
        return steps
    
    def _apply_optimization(self, steps: List[PlanStep], optimization: Learning) -> List[PlanStep]:
        """应用优化建议"""
        # 实现优化建议的应用逻辑
        return steps
    
    def _add_dependencies(self, steps: List[PlanStep]) -> List[PlanStep]:
        """添加步骤间的依赖关系"""
        # 依赖关系在步骤生成时已经设置，这里可以进行额外的依赖分析和优化
        return steps
    
    def _generate_reasoning(self, task_analysis: Dict[str, Any], 
                          insights: Dict[str, Any]) -> str:
        """生成计划推理说明"""
        reasoning_parts = [
            f"Task Type: {task_analysis['task_type']}",
            f"Complexity: {task_analysis['complexity']}",
            f"Required Tools: {', '.join(task_analysis['required_tools'])}"
        ]
        
        if insights['success_patterns']:
            reasoning_parts.append(f"Applied {len(insights['success_patterns'])} success patterns")
        
        if insights['failure_patterns']:
            reasoning_parts.append(f"Avoided {len(insights['failure_patterns'])} failure patterns")
        
        if insights['optimizations']:
            reasoning_parts.append(f"Applied {len(insights['optimizations'])} optimizations")
        
        return "; ".join(reasoning_parts)