"""
执行代理
将抽象计划转化为具体行动的执行者
"""
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import time

from app.models.data_models import (
    Plan, PlanStep, ExecutionLog, ExecutionStepResult, 
    MCPRequest, MCPResponse, TaskStatus
)
from app.core.tool_manager import ToolManager


class ExecutorAgent:
    """执行代理，负责执行计划中的每个步骤"""
    
    def __init__(self, tool_manager: ToolManager):
        self.tool_manager = tool_manager
        self.logger = logging.getLogger(__name__)
    
    def execute(self, plan: Plan, authorized_tools: Dict[str, Dict]) -> ExecutionLog:
        """执行计划
        
        Args:
            plan: 待执行的计划
            authorized_tools: 授权的工具字典
            
        Returns:
            ExecutionLog: 详细的执行日志
        """
        self.logger.info(f"Starting execution of plan {plan.plan_id} with {len(plan.steps)} steps")
        
        # 创建执行日志
        execution_log = ExecutionLog(
            execution_id=str(uuid.uuid4()),
            plan_id=plan.plan_id,
            status="running",
            started_at=datetime.utcnow().isoformat(),
            finished_at=None,
            step_results=[],
            final_message=None
        )
        
        try:
            # 按依赖关系排序步骤
            sorted_steps = self._sort_steps_by_dependencies(plan.steps)
            
            # 执行每个步骤
            for step in sorted_steps:
                step_result = self._execute_step(step, authorized_tools, execution_log)
                execution_log.step_results.append(step_result)
                
                # 检查步骤执行结果
                if step_result.status == "failed" and step.critical:
                    execution_log.status = "failed"
                    execution_log.final_message = f"Critical step '{step.step_id}' failed: {step_result.error_message}"
                    break
                elif step_result.status == "failed":
                    self.logger.warning(f"Non-critical step '{step.step_id}' failed, continuing execution")
            
            # 如果所有步骤都执行完成且没有关键失败，标记为成功
            if execution_log.status == "running":
                execution_log.status = "success"
                execution_log.final_message = "All steps completed successfully"
        
        except Exception as e:
            self.logger.error(f"Unexpected error during plan execution: {e}")
            execution_log.status = "failed"
            execution_log.final_message = f"Execution failed due to unexpected error: {str(e)}"
        
        finally:
            execution_log.finished_at = datetime.utcnow().isoformat()
        
        self.logger.info(f"Plan execution completed with status: {execution_log.status}")
        return execution_log
    
    def _sort_steps_by_dependencies(self, steps: List[PlanStep]) -> List[PlanStep]:
        """根据依赖关系对步骤进行拓扑排序"""
        # 创建步骤字典以便快速查找
        step_dict = {step.step_id: step for step in steps}
        
        # 拓扑排序算法
        visited = set()
        temp_visited = set()
        sorted_steps = []
        
        def visit(step_id: str):
            if step_id in temp_visited:
                raise ValueError(f"Circular dependency detected involving step: {step_id}")
            if step_id in visited:
                return
            
            temp_visited.add(step_id)
            
            step = step_dict.get(step_id)
            if step:
                # 先访问所有依赖
                for dep_id in step.depends_on:
                    if dep_id in step_dict:
                        visit(dep_id)
                
                temp_visited.remove(step_id)
                visited.add(step_id)
                sorted_steps.append(step)
        
        # 访问所有步骤
        for step in steps:
            if step.step_id not in visited:
                visit(step.step_id)
        
        return sorted_steps
    
    def _execute_step(self, step: PlanStep, authorized_tools: Dict[str, Dict],
                     execution_log: ExecutionLog) -> ExecutionStepResult:
        """执行单个步骤"""
        self.logger.info(f"Executing step: {step.step_id} - {step.description}")
        
        start_time = datetime.utcnow().isoformat()
        
        # 检查依赖是否满足
        if not self._check_dependencies(step, execution_log):
            return ExecutionStepResult(
                step_id=step.step_id,
                status="skipped",
                started_at=start_time,
                finished_at=datetime.utcnow().isoformat(),
                mcp_request=MCPRequest(),
                mcp_response=MCPResponse(status="failed", error="Dependencies not satisfied"),
                error_message="Step skipped due to failed dependencies"
            )
        
        # 创建MCP请求
        mcp_request = MCPRequest(
            protocol="MCP",
            version="1.0",
            tool_name=step.tool_name,
            params=step.parameters,
            request_id=str(uuid.uuid4())
        )
        
        # 执行工具调用
        retry_count = 0
        max_retries = 3 if step.retry_on_failure else 1
        
        while retry_count < max_retries:
            try:
                mcp_response = self.tool_manager.execute_mcp_request(mcp_request, authorized_tools)
                
                # 判断执行结果
                if mcp_response.status == "success":
                    self.logger.info(f"Step {step.step_id} completed successfully")
                    return ExecutionStepResult(
                        step_id=step.step_id,
                        status="success",
                        started_at=start_time,
                        finished_at=datetime.utcnow().isoformat(),
                        mcp_request=mcp_request,
                        mcp_response=mcp_response,
                        error_message=None
                    )
                else:
                    # 失败情况，检查是否需要重试
                    retry_count += 1
                    if retry_count < max_retries:
                        self.logger.warning(f"Step {step.step_id} failed, retrying ({retry_count}/{max_retries})")
                        time.sleep(1)  # 简单的重试延迟
                        continue
                    else:
                        self.logger.error(f"Step {step.step_id} failed after {retry_count} attempts")
                        return ExecutionStepResult(
                            step_id=step.step_id,
                            status="failed",
                            started_at=start_time,
                            finished_at=datetime.utcnow().isoformat(),
                            mcp_request=mcp_request,
                            mcp_response=mcp_response,
                            error_message=mcp_response.error or "Tool execution failed"
                        )
            
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    self.logger.warning(f"Step {step.step_id} encountered error, retrying ({retry_count}/{max_retries}): {e}")
                    time.sleep(1)
                    continue
                else:
                    self.logger.error(f"Step {step.step_id} failed with exception after {retry_count} attempts: {e}")
                    return ExecutionStepResult(
                        step_id=step.step_id,
                        status="failed",
                        started_at=start_time,
                        finished_at=datetime.utcnow().isoformat(),
                        mcp_request=mcp_request,
                        mcp_response=MCPResponse(status="failed", error=str(e)),
                        error_message=f"Step execution failed with exception: {str(e)}"
                    )
    
    def _check_dependencies(self, step: PlanStep, execution_log: ExecutionLog) -> bool:
        """检查步骤的依赖是否已成功执行"""
        if not step.depends_on:
            return True
        
        # 检查每个依赖步骤的执行结果
        for dep_step_id in step.depends_on:
            dep_result = None
            for result in execution_log.step_results:
                if result.step_id == dep_step_id:
                    dep_result = result
                    break
            
            # 依赖步骤未执行或执行失败
            if not dep_result or dep_result.status != "success":
                self.logger.warning(f"Step {step.step_id} dependency {dep_step_id} not satisfied")
                return False
        
        return True
    
    def get_execution_summary(self, execution_log: ExecutionLog) -> Dict[str, Any]:
        """获取执行摘要"""
        total_steps = len(execution_log.step_results)
        successful_steps = len([r for r in execution_log.step_results if r.status == "success"])
        failed_steps = len([r for r in execution_log.step_results if r.status == "failed"])
        skipped_steps = len([r for r in execution_log.step_results if r.status == "skipped"])
        
        # 计算执行时间
        execution_time = None
        if execution_log.started_at and execution_log.finished_at:
            start = datetime.fromisoformat(execution_log.started_at.replace('Z', '+00:00'))
            finish = datetime.fromisoformat(execution_log.finished_at.replace('Z', '+00:00'))
            execution_time = (finish - start).total_seconds()
        
        summary = {
            "execution_id": execution_log.execution_id,
            "plan_id": execution_log.plan_id,
            "status": execution_log.status,
            "total_steps": total_steps,
            "successful_steps": successful_steps,
            "failed_steps": failed_steps,
            "skipped_steps": skipped_steps,
            "execution_time_seconds": execution_time,
            "final_message": execution_log.final_message,
            "step_details": []
        }
        
        # 添加步骤详情
        for result in execution_log.step_results:
            step_detail = {
                "step_id": result.step_id,
                "status": result.status,
                "tool_name": result.mcp_request.tool_name,
                "execution_time": result.mcp_response.execution_time if result.mcp_response else None,
                "error_message": result.error_message
            }
            summary["step_details"].append(step_detail)
        
        return summary