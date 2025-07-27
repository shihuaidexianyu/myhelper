"""
报告代理
负责生成最终报告和学习经验
"""
import uuid
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from app.models.data_models import Plan, ExecutionLog, Learning


class ReporterAgent:
    """报告代理，生成任务执行报告和学习经验"""
    
    def __init__(self, plan: Plan, execution_log: ExecutionLog):
        self.plan = plan
        self.execution_log = execution_log
        self.logger = logging.getLogger(__name__)
    
    def generate_report_and_learnings(self) -> Tuple[str, List[Learning]]:
        """生成最终报告和学习经验
        
        Returns:
            Tuple[str, List[Learning]]: (最终报告摘要, 学习经验列表)
        """
        self.logger.info(f"Generating report for execution {self.execution_log.execution_id}")
        
        # 生成执行摘要
        execution_summary = self._generate_execution_summary()
        
        # 分析执行结果
        analysis = self._analyze_execution_results()
        
        # 生成最终报告
        final_report = self._create_final_report(execution_summary, analysis)
        
        # 提取学习经验
        learnings = self._extract_learnings(analysis)
        
        self.logger.info(f"Generated report with {len(learnings)} learning insights")
        return final_report, learnings
    
    def _generate_execution_summary(self) -> Dict[str, Any]:
        """生成执行摘要"""
        total_steps = len(self.execution_log.step_results)
        successful_steps = len([r for r in self.execution_log.step_results if r.status == "success"])
        failed_steps = len([r for r in self.execution_log.step_results if r.status == "failed"])
        skipped_steps = len([r for r in self.execution_log.step_results if r.status == "skipped"])
        
        # 计算执行时间
        execution_time = self._calculate_execution_time()
        
        # 计算成功率
        success_rate = (successful_steps / total_steps * 100) if total_steps > 0 else 0
        
        summary = {
            "execution_id": self.execution_log.execution_id,
            "plan_id": self.plan.plan_id,
            "task_id": self.plan.task_id,
            "overall_status": self.execution_log.status,
            "total_steps": total_steps,
            "successful_steps": successful_steps,
            "failed_steps": failed_steps,
            "skipped_steps": skipped_steps,
            "success_rate": round(success_rate, 2),
            "execution_time_seconds": execution_time,
            "started_at": self.execution_log.started_at,
            "finished_at": self.execution_log.finished_at,
            "final_message": self.execution_log.final_message
        }
        
        return summary
    
    def _calculate_execution_time(self) -> Optional[float]:
        """计算总执行时间"""
        if not self.execution_log.started_at or not self.execution_log.finished_at:
            return None
        
        try:
            start = datetime.fromisoformat(self.execution_log.started_at.replace('Z', '+00:00'))
            finish = datetime.fromisoformat(self.execution_log.finished_at.replace('Z', '+00:00'))
            return (finish - start).total_seconds()
        except Exception as e:
            self.logger.warning(f"Could not calculate execution time: {e}")
            return None
    
    def _analyze_execution_results(self) -> Dict[str, Any]:
        """分析执行结果"""
        analysis = {
            "performance_metrics": self._analyze_performance(),
            "failure_analysis": self._analyze_failures(),
            "success_patterns": self._identify_success_patterns(),
            "bottlenecks": self._identify_bottlenecks(),
            "recommendations": self._generate_recommendations()
        }
        
        return analysis
    
    def _analyze_performance(self) -> Dict[str, Any]:
        """分析性能指标"""
        step_times = []
        tool_performance = {}
        
        for result in self.execution_log.step_results:
            if result.mcp_response and result.mcp_response.execution_time:
                step_times.append(result.mcp_response.execution_time)
                
                tool_name = result.mcp_request.tool_name
                if tool_name not in tool_performance:
                    tool_performance[tool_name] = []
                tool_performance[tool_name].append(result.mcp_response.execution_time)
        
        # 计算统计指标
        performance_metrics = {
            "average_step_time": sum(step_times) / len(step_times) if step_times else 0,
            "max_step_time": max(step_times) if step_times else 0,
            "min_step_time": min(step_times) if step_times else 0,
            "total_tool_calls": len(self.execution_log.step_results),
            "tool_performance": {}
        }
        
        # 分析每个工具的性能
        for tool_name, times in tool_performance.items():
            performance_metrics["tool_performance"][tool_name] = {
                "call_count": len(times),
                "average_time": sum(times) / len(times),
                "max_time": max(times),
                "min_time": min(times)
            }
        
        return performance_metrics
    
    def _analyze_failures(self) -> Dict[str, Any]:
        """分析失败情况"""
        failed_steps = [r for r in self.execution_log.step_results if r.status == "failed"]
        
        if not failed_steps:
            return {"has_failures": False, "failure_count": 0}
        
        # 分析失败模式
        failure_reasons = {}
        failed_tools = {}
        
        for failed_step in failed_steps:
            # 统计失败原因
            error_msg = failed_step.error_message or "Unknown error"
            failure_reasons[error_msg] = failure_reasons.get(error_msg, 0) + 1
            
            # 统计失败的工具
            tool_name = failed_step.mcp_request.tool_name
            failed_tools[tool_name] = failed_tools.get(tool_name, 0) + 1
        
        analysis = {
            "has_failures": True,
            "failure_count": len(failed_steps),
            "failure_rate": len(failed_steps) / len(self.execution_log.step_results) * 100,
            "failure_reasons": failure_reasons,
            "failed_tools": failed_tools,
            "critical_failures": [
                step for step in failed_steps 
                if self._is_critical_step(step.step_id)
            ]
        }
        
        return analysis
    
    def _identify_success_patterns(self) -> List[Dict[str, Any]]:
        """识别成功模式"""
        successful_steps = [r for r in self.execution_log.step_results if r.status == "success"]
        patterns = []
        
        if not successful_steps:
            return patterns
        
        # 分析成功的工具组合
        successful_tools = [step.mcp_request.tool_name for step in successful_steps]
        tool_sequence = " -> ".join(successful_tools)
        
        patterns.append({
            "type": "tool_sequence",
            "description": f"Successful tool execution sequence: {tool_sequence}",
            "confidence": 0.8,
            "context": {
                "tool_count": len(successful_tools),
                "unique_tools": len(set(successful_tools)),
                "sequence": successful_tools
            }
        })
        
        # 分析快速执行的步骤
        fast_steps = [
            step for step in successful_steps 
            if step.mcp_response and step.mcp_response.execution_time and 
            step.mcp_response.execution_time < 5.0  # 少于5秒的被认为是快速的
        ]
        
        if fast_steps:
            patterns.append({
                "type": "fast_execution",
                "description": f"{len(fast_steps)} steps executed in under 5 seconds",
                "confidence": 0.7,
                "context": {
                    "fast_step_count": len(fast_steps),
                    "average_time": sum(s.mcp_response.execution_time for s in fast_steps) / len(fast_steps)
                }
            })
        
        return patterns
    
    def _identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """识别性能瓶颈"""
        bottlenecks = []
        
        # 识别执行时间过长的步骤
        for result in self.execution_log.step_results:
            if (result.mcp_response and result.mcp_response.execution_time and 
                result.mcp_response.execution_time > 30.0):  # 超过30秒被认为是瓶颈
                
                bottlenecks.append({
                    "type": "slow_step",
                    "step_id": result.step_id,
                    "tool_name": result.mcp_request.tool_name,
                    "execution_time": result.mcp_response.execution_time,
                    "description": f"Step {result.step_id} took {result.mcp_response.execution_time:.2f} seconds"
                })
        
        # 识别频繁失败重试的步骤
        retry_steps = [
            result for result in self.execution_log.step_results 
            if result.status == "failed" and "retry" in (result.error_message or "").lower()
        ]
        
        if retry_steps:
            bottlenecks.append({
                "type": "frequent_retries",
                "description": f"{len(retry_steps)} steps required retries",
                "steps": [step.step_id for step in retry_steps]
            })
        
        return bottlenecks
    
    def _generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于失败分析生成建议
        failed_steps = [r for r in self.execution_log.step_results if r.status == "failed"]
        if failed_steps:
            failed_tools = set(step.mcp_request.tool_name for step in failed_steps)
            recommendations.append(f"Review and test the following tools: {', '.join(failed_tools)}")
        
        # 基于性能分析生成建议
        slow_steps = [
            r for r in self.execution_log.step_results 
            if (r.mcp_response and r.mcp_response.execution_time and 
                r.mcp_response.execution_time > 20.0)
        ]
        if slow_steps:
            recommendations.append("Consider optimizing slow-executing steps or adding timeout configurations")
        
        # 基于整体成功率生成建议
        success_rate = len([r for r in self.execution_log.step_results if r.status == "success"]) / len(self.execution_log.step_results) * 100
        if success_rate < 80:
            recommendations.append("Overall success rate is below 80%, consider reviewing task configuration and tool reliability")
        
        return recommendations
    
    def _is_critical_step(self, step_id: str) -> bool:
        """判断步骤是否是关键步骤"""
        for step in self.plan.steps:
            if step.step_id == step_id:
                return step.critical
        return False
    
    def _create_final_report(self, summary: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """创建最终报告"""
        report_lines = [
            f"# Execution Report",
            f"**Task ID:** {summary['task_id']}",
            f"**Execution ID:** {summary['execution_id']}",
            f"**Status:** {summary['overall_status'].upper()}",
            f"**Success Rate:** {summary['success_rate']}%",
            "",
            "## Summary",
            f"- Total Steps: {summary['total_steps']}",
            f"- Successful: {summary['successful_steps']}",
            f"- Failed: {summary['failed_steps']}",
            f"- Skipped: {summary['skipped_steps']}",
            f"- Execution Time: {summary['execution_time_seconds']:.2f} seconds" if summary['execution_time_seconds'] else "- Execution Time: N/A",
            ""
        ]
        
        # 添加性能指标
        perf = analysis['performance_metrics']
        if perf['total_tool_calls'] > 0:
            report_lines.extend([
                "## Performance Metrics",
                f"- Average Step Time: {perf['average_step_time']:.2f} seconds",
                f"- Max Step Time: {perf['max_step_time']:.2f} seconds",
                f"- Total Tool Calls: {perf['total_tool_calls']}",
                ""
            ])
        
        # 添加失败分析
        if analysis['failure_analysis']['has_failures']:
            failure_analysis = analysis['failure_analysis']
            report_lines.extend([
                "## Failure Analysis",
                f"- Failure Rate: {failure_analysis['failure_rate']:.2f}%",
                f"- Failed Tools: {', '.join(failure_analysis['failed_tools'].keys())}",
                ""
            ])
        
        # 添加建议
        if analysis['recommendations']:
            report_lines.extend([
                "## Recommendations",
                *[f"- {rec}" for rec in analysis['recommendations']],
                ""
            ])
        
        # 添加最终消息
        if summary['final_message']:
            report_lines.extend([
                "## Final Message",
                summary['final_message']
            ])
        
        return "\n".join(report_lines)
    
    def _extract_learnings(self, analysis: Dict[str, Any]) -> List[Learning]:
        """从分析结果中提取学习经验"""
        learnings = []
        
        # 从成功模式中提取学习
        for pattern in analysis['success_patterns']:
            learning = Learning(
                learning_id=str(uuid.uuid4()),
                task_id=self.plan.task_id,
                category="success_pattern",
                title=f"Success Pattern: {pattern['type']}",
                description=pattern['description'],
                context={
                    "pattern_type": pattern['type'],
                    "execution_context": pattern['context'],
                    "plan_id": self.plan.plan_id,
                    "execution_id": self.execution_log.execution_id
                },
                created_at=datetime.utcnow().isoformat(),
                confidence_score=pattern['confidence']
            )
            learnings.append(learning)
        
        # 从失败分析中提取学习
        if analysis['failure_analysis']['has_failures']:
            failure_analysis = analysis['failure_analysis']
            learning = Learning(
                learning_id=str(uuid.uuid4()),
                task_id=self.plan.task_id,
                category="failure_analysis",
                title="Failure Pattern Analysis",
                description=f"Identified {failure_analysis['failure_count']} failures with {failure_analysis['failure_rate']:.1f}% failure rate",
                context={
                    "failure_reasons": failure_analysis['failure_reasons'],
                    "failed_tools": failure_analysis['failed_tools'],
                    "failure_rate": failure_analysis['failure_rate'],
                    "plan_id": self.plan.plan_id,
                    "execution_id": self.execution_log.execution_id
                },
                created_at=datetime.utcnow().isoformat(),
                confidence_score=0.9  # 失败分析通常很可靠
            )
            learnings.append(learning)
        
        # 从性能瓶颈中提取学习
        if analysis['bottlenecks']:
            learning = Learning(
                learning_id=str(uuid.uuid4()),
                task_id=self.plan.task_id,
                category="optimization",
                title="Performance Bottleneck Identification",
                description=f"Identified {len(analysis['bottlenecks'])} performance bottlenecks",
                context={
                    "bottlenecks": analysis['bottlenecks'],
                    "recommendations": analysis['recommendations'],
                    "plan_id": self.plan.plan_id,
                    "execution_id": self.execution_log.execution_id
                },
                created_at=datetime.utcnow().isoformat(),
                confidence_score=0.8
            )
            learnings.append(learning)
        
        return learnings