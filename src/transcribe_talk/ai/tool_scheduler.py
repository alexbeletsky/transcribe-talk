"""
Tool Scheduler - Manages tool execution.

This module provides the ToolScheduler class which is responsible for:
- Validating and executing tool call requests
- Managing tool execution lifecycle
- Handling confirmations and timeouts
- Emitting execution results
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Callable, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel
from rich.syntax import Syntax

from .events import FunctionResponseEvent, ToolCallInfo
from ..tools import ToolRegistry, ToolMetadata

logger = logging.getLogger(__name__)
console = Console()


class ToolCallState(Enum):
    """States of a tool call execution."""
    PENDING = "pending"
    VALIDATING = "validating"
    AWAITING_APPROVAL = "awaiting_approval"
    SCHEDULED = "scheduled"
    EXECUTING = "executing"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class ToolCall:
    """Represents a tool call with its execution state."""
    info: ToolCallInfo
    state: ToolCallState = ToolCallState.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ApprovalMode(Enum):
    """Tool approval modes."""
    ALWAYS = "always"      # Always require approval
    NEVER = "never"        # Never require approval (auto-confirm)
    SMART = "smart"        # Require approval for dangerous operations


class ToolScheduler:
    """
    Manages the lifecycle and execution of tool calls.
    
    Features:
    - Tool validation against registry
    - Interactive/automatic approval flows
    - Timeout enforcement
    - Retry logic
    - Result formatting
    """
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        approval_mode: ApprovalMode = ApprovalMode.SMART,
        default_timeout: float = 30.0,
        max_workers: int = 4,
        dry_run: bool = False
    ):
        """
        Initialize the ToolScheduler.
        
        Args:
            tool_registry: Registry of available tools
            approval_mode: How to handle tool approvals
            default_timeout: Default timeout for tool execution
            max_workers: Maximum concurrent tool executions
            dry_run: If True, simulate tool execution without running
        """
        self.tool_registry = tool_registry
        self.approval_mode = approval_mode
        self.default_timeout = default_timeout
        self.dry_run = dry_run
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tool_calls: Dict[str, ToolCall] = {}
        
        logger.info(
            f"ToolScheduler initialized (approval={approval_mode.value}, "
            f"timeout={default_timeout}s, workers={max_workers}, dry_run={dry_run})"
        )
    
    async def execute_tool_calls(
        self,
        tool_call_infos: List[ToolCallInfo],
        interactive: bool = True
    ) -> List[FunctionResponseEvent]:
        """
        Execute a list of tool calls.
        
        Args:
            tool_call_infos: List of tool call information
            interactive: Whether to allow interactive prompts
            
        Returns:
            List of function response events
        """
        results = []
        
        for info in tool_call_infos:
            event = await self.execute_tool_call(info, interactive)
            results.append(event)
        
        return results
    
    async def execute_tool_call(
        self,
        info: ToolCallInfo,
        interactive: bool = True
    ) -> FunctionResponseEvent:
        """
        Execute a single tool call.
        
        Args:
            info: Tool call information
            interactive: Whether to allow interactive prompts
            
        Returns:
            Function response event
        """
        tool_call = ToolCall(info=info)
        self._tool_calls[info.id] = tool_call
        
        try:
            # Validate tool
            tool_call.state = ToolCallState.VALIDATING
            tool_func = self.tool_registry.get_tool(info.name)
            tool_metadata = self.tool_registry.get_metadata(info.name)
            
            if not tool_func or not tool_metadata:
                raise ValueError(f"Unknown tool: {info.name}")
            
            # Check approval if needed
            if self._requires_approval(tool_metadata, interactive):
                tool_call.state = ToolCallState.AWAITING_APPROVAL
                approved = await self._get_approval(info, tool_metadata, interactive)
                if not approved:
                    tool_call.state = ToolCallState.CANCELLED
                    return FunctionResponseEvent(
                        tool_call_id=info.id,
                        result="Tool execution cancelled by user",
                        success=False,
                        error_message="User cancelled execution"
                    )
            
            # Execute tool
            tool_call.state = ToolCallState.EXECUTING
            tool_call.start_time = datetime.now()
            
            # Determine timeout
            timeout = tool_metadata.timeout_seconds or self.default_timeout
            
            # Execute with timeout or simulate in dry-run mode
            if self.dry_run:
                # Simulate execution
                logger.info(f"[DRY-RUN] Would execute tool: {info.name} with args: {info.arguments}")
                result = f"[DRY-RUN] Tool '{info.name}' would be executed with arguments: {info.arguments}"
                # Simulate a small delay
                await asyncio.sleep(0.5)
            else:
                # Actually execute the tool
                result = await self._execute_with_timeout(
                    tool_func,
                    info.arguments,
                    timeout
                )
            
            # Success
            tool_call.end_time = datetime.now()
            tool_call.state = ToolCallState.SUCCESS
            tool_call.result = str(result)
            
            return FunctionResponseEvent(
                tool_call_id=info.id,
                result=tool_call.result,
                success=True
            )
            
        except asyncio.TimeoutError:
            tool_call.state = ToolCallState.TIMEOUT
            tool_call.error = f"Tool execution timed out after {timeout}s"
            logger.error(f"Tool {info.name} timed out")
            
            return FunctionResponseEvent(
                tool_call_id=info.id,
                result="",
                success=False,
                error_message=tool_call.error
            )
            
        except Exception as e:
            tool_call.state = ToolCallState.ERROR
            tool_call.error = str(e)
            logger.error(f"Tool {info.name} failed: {e}")
            
            return FunctionResponseEvent(
                tool_call_id=info.id,
                result="",
                success=False,
                error_message=tool_call.error
            )
        
        finally:
            if tool_call.end_time is None:
                tool_call.end_time = datetime.now()
    
    def _requires_approval(self, metadata: ToolMetadata, interactive: bool) -> bool:
        """
        Determine if a tool requires approval.
        
        Args:
            metadata: Tool metadata
            interactive: Whether we're in interactive mode
            
        Returns:
            Whether approval is required
        """
        if not interactive:
            return False
            
        if self.approval_mode == ApprovalMode.NEVER:
            return False
        elif self.approval_mode == ApprovalMode.ALWAYS:
            return True
        else:  # SMART mode
            return metadata.requires_confirmation
    
    async def _get_approval(
        self,
        info: ToolCallInfo,
        metadata: ToolMetadata,
        interactive: bool
    ) -> bool:
        """
        Get user approval for tool execution.
        
        Args:
            info: Tool call information
            metadata: Tool metadata
            interactive: Whether we're in interactive mode
            
        Returns:
            Whether the tool was approved
        """
        if not interactive:
            # In non-interactive mode, follow default behavior
            return self.approval_mode != ApprovalMode.ALWAYS
        
        # Format tool info for display
        console.print("\n[yellow]Tool Execution Request[/yellow]")
        
        # Create a panel with tool details
        details = f"[bold]Tool:[/bold] {info.name}\n"
        details += f"[bold]Description:[/bold] {metadata.description}\n"
        details += f"[bold]Category:[/bold] {metadata.category.value}\n"
        
        if info.arguments:
            details += "\n[bold]Arguments:[/bold]\n"
            # Pretty print arguments
            for key, value in info.arguments.items():
                details += f"  {key}: {value}\n"
        
        panel = Panel(
            details,
            title="Tool Details",
            border_style="yellow"
        )
        console.print(panel)
        
        # Ask for confirmation
        return Confirm.ask(
            "[yellow]Execute this tool?[/yellow]",
            default=True
        )
    
    async def _execute_with_timeout(
        self,
        func: Callable,
        arguments: Dict[str, Any],
        timeout: float
    ) -> Any:
        """
        Execute a function with timeout.
        
        Args:
            func: Function to execute
            arguments: Function arguments
            timeout: Timeout in seconds
            
        Returns:
            Function result
            
        Raises:
            asyncio.TimeoutError: If execution times out
        """
        # Check if the function is async
        if asyncio.iscoroutinefunction(func):
            # Execute async function directly
            return await asyncio.wait_for(
                func(**arguments),
                timeout=timeout
            )
        else:
            # Execute sync function in thread pool
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(
                self._executor,
                func,
                **arguments
            )
            return await asyncio.wait_for(future, timeout=timeout)
    
    def get_tool_call_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all tool calls.
        
        Returns:
            Summary dictionary
        """
        summary = {
            "total_calls": len(self._tool_calls),
            "successful": 0,
            "failed": 0,
            "cancelled": 0,
            "timed_out": 0,
            "average_duration": 0.0,
            "calls": []
        }
        
        total_duration = 0.0
        completed_count = 0
        
        for call_id, tool_call in self._tool_calls.items():
            if tool_call.state == ToolCallState.SUCCESS:
                summary["successful"] += 1
            elif tool_call.state == ToolCallState.ERROR:
                summary["failed"] += 1
            elif tool_call.state == ToolCallState.CANCELLED:
                summary["cancelled"] += 1
            elif tool_call.state == ToolCallState.TIMEOUT:
                summary["timed_out"] += 1
            
            # Calculate duration
            if tool_call.start_time and tool_call.end_time:
                duration = (tool_call.end_time - tool_call.start_time).total_seconds()
                total_duration += duration
                completed_count += 1
            else:
                duration = None
            
            summary["calls"].append({
                "id": call_id,
                "tool": tool_call.info.name,
                "state": tool_call.state.value,
                "duration": duration,
                "error": tool_call.error
            })
        
        if completed_count > 0:
            summary["average_duration"] = total_duration / completed_count
        
        return summary
    
    def clear_history(self) -> None:
        """Clear tool call history."""
        self._tool_calls.clear()
        logger.info("Tool call history cleared")
    
    def __del__(self):
        """Cleanup executor on deletion."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)