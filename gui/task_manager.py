"""Task Manager - Monitor and control background threads"""
import threading
from datetime import datetime


class TaskManager:
    """Global task manager for tracking background threads"""

    def __init__(self):
        self.tasks = {}  # task_id -> task_info
        self.lock = threading.Lock()

    def register_task(self, task_id, name, thread, stop_event=None, console=None):
        """Register a new task

        Args:
            task_id: Unique task identifier (e.g., console tab index)
            name: Task display name
            thread: Thread object
            stop_event: threading.Event to signal stop (optional)
            console: Console widget (optional)
        """
        with self.lock:
            self.tasks[task_id] = {
                'id': task_id,
                'name': name,
                'thread': thread,
                'stop_event': stop_event,
                'console': console,
                'start_time': datetime.now(),
                'status': 'running'
            }

    def unregister_task(self, task_id):
        """Remove a task from tracking"""
        with self.lock:
            if task_id in self.tasks:
                del self.tasks[task_id]

    def stop_task(self, task_id):
        """Signal a task to stop

        Returns:
            bool: True if stop signal sent, False if task not found
        """
        with self.lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]

            # Set stop event if available
            if task['stop_event']:
                task['stop_event'].set()

            # Update status
            task['status'] = 'stopping'

            return True

    def get_all_tasks(self):
        """Get list of all tasks

        Returns:
            list: List of task info dicts
        """
        with self.lock:
            # Clean up dead threads
            dead_tasks = []
            for task_id, task in self.tasks.items():
                if not task['thread'].is_alive():
                    dead_tasks.append(task_id)

            for task_id in dead_tasks:
                del self.tasks[task_id]

            # Return copy of current tasks
            return [task.copy() for task in self.tasks.values()]

    def get_task_count(self):
        """Get number of active tasks"""
        with self.lock:
            return len(self.tasks)

    def stop_all_tasks(self):
        """Stop all running tasks"""
        with self.lock:
            for task_id in list(self.tasks.keys()):
                self.stop_task(task_id)


# Global instance
_task_manager = TaskManager()


def get_task_manager():
    """Get global task manager instance"""
    return _task_manager
