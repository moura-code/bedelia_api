"""
Progress tracking system for scraper operations.
"""

import logging
import time
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from .interfaces import ProgressTrackerProtocol


class TaskStatus(Enum):
    """Status of a tracked task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """Information about a tracked task."""
    name: str
    status: TaskStatus = TaskStatus.PENDING
    total_items: int = 0
    completed_items: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    current_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def progress_percentage(self) -> float:
        """Get progress as percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.completed_items / self.total_items) * 100
    
    @property
    def elapsed_time(self) -> Optional[float]:
        """Get elapsed time in seconds."""
        if not self.start_time:
            return None
        end_time = self.end_time or time.time()
        return end_time - self.start_time
    
    @property
    def estimated_remaining(self) -> Optional[float]:
        """Estimate remaining time in seconds."""
        if not self.start_time or self.completed_items == 0 or self.total_items == 0:
            return None
        
        elapsed = self.elapsed_time
        if not elapsed:
            return None
        
        rate = self.completed_items / elapsed
        remaining_items = self.total_items - self.completed_items
        return remaining_items / rate if rate > 0 else None


class ProgressTracker:
    """
    Progress tracking system with logging and callback support.
    Implements the ProgressTrackerProtocol.
    """
    
    def __init__(self, 
                 logger: Optional[logging.Logger] = None,
                 progress_callback: Optional[Callable[[TaskInfo], None]] = None):
        """
        Initialize progress tracker.
        
        Args:
            logger: Logger instance for progress messages
            progress_callback: Callback function called on progress updates
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.progress_callback = progress_callback
        self.tasks: Dict[str, TaskInfo] = {}
        self.current_task: Optional[str] = None
    
    def start_task(self, task_name: str, total_items: int = 0) -> None:
        """Start tracking a new task."""
        task_info = TaskInfo(
            name=task_name,
            status=TaskStatus.RUNNING,
            total_items=total_items,
            start_time=time.time()
        )
        
        self.tasks[task_name] = task_info
        self.current_task = task_name
        
        if total_items > 0:
            self.logger.info(f"Started task '{task_name}' (0/{total_items} items)")
        else:
            self.logger.info(f"Started task '{task_name}'")
        
        if self.progress_callback:
            self.progress_callback(task_info)
    
    def update_progress(self, completed: int, message: str = "") -> None:
        """Update progress for the current task."""
        if not self.current_task or self.current_task not in self.tasks:
            self.logger.warning("No active task to update progress")
            return
        
        task_info = self.tasks[self.current_task]
        task_info.completed_items = completed
        task_info.current_message = message
        
        # Log progress
        if task_info.total_items > 0:
            percentage = task_info.progress_percentage
            self.logger.info(
                f"Task '{task_info.name}': {completed}/{task_info.total_items} "
                f"({percentage:.1f}%) - {message}"
            )
        else:
            self.logger.info(f"Task '{task_info.name}': {completed} completed - {message}")
        
        if self.progress_callback:
            self.progress_callback(task_info)
    
    def complete_task(self, message: str = "") -> None:
        """Mark current task as completed."""
        if not self.current_task or self.current_task not in self.tasks:
            self.logger.warning("No active task to complete")
            return
        
        task_info = self.tasks[self.current_task]
        task_info.status = TaskStatus.COMPLETED
        task_info.end_time = time.time()
        task_info.current_message = message
        
        elapsed = task_info.elapsed_time
        elapsed_str = f" in {elapsed:.2f}s" if elapsed else ""
        
        if task_info.total_items > 0:
            self.logger.info(
                f"Completed task '{task_info.name}': {task_info.completed_items}/"
                f"{task_info.total_items} items{elapsed_str} - {message}"
            )
        else:
            self.logger.info(
                f"Completed task '{task_info.name}': {task_info.completed_items} items{elapsed_str} - {message}"
            )
        
        if self.progress_callback:
            self.progress_callback(task_info)
        
        self.current_task = None
    
    def fail_task(self, error_message: str) -> None:
        """Mark current task as failed."""
        if not self.current_task or self.current_task not in self.tasks:
            self.logger.warning("No active task to fail")
            return
        
        task_info = self.tasks[self.current_task]
        task_info.status = TaskStatus.FAILED
        task_info.end_time = time.time()
        task_info.current_message = error_message
        
        self.logger.error(f"Task '{task_info.name}' failed: {error_message}")
        
        if self.progress_callback:
            self.progress_callback(task_info)
        
        self.current_task = None
    
    def cancel_task(self, reason: str = "") -> None:
        """Cancel current task."""
        if not self.current_task or self.current_task not in self.tasks:
            self.logger.warning("No active task to cancel")
            return
        
        task_info = self.tasks[self.current_task]
        task_info.status = TaskStatus.CANCELLED
        task_info.end_time = time.time()
        task_info.current_message = reason
        
        self.logger.warning(f"Task '{task_info.name}' cancelled: {reason}")
        
        if self.progress_callback:
            self.progress_callback(task_info)
        
        self.current_task = None
    
    def get_task_info(self, task_name: str) -> Optional[TaskInfo]:
        """Get information about a specific task."""
        return self.tasks.get(task_name)
    
    def get_current_task(self) -> Optional[TaskInfo]:
        """Get information about the current task."""
        if not self.current_task:
            return None
        return self.tasks.get(self.current_task)
    
    def get_all_tasks(self) -> Dict[str, TaskInfo]:
        """Get information about all tasks."""
        return self.tasks.copy()
    
    def clear_completed_tasks(self) -> None:
        """Remove completed tasks from tracking."""
        completed_tasks = [
            name for name, task in self.tasks.items()
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
        ]
        
        for task_name in completed_tasks:
            del self.tasks[task_name]
        
        if completed_tasks:
            self.logger.info(f"Cleared {len(completed_tasks)} completed tasks")
