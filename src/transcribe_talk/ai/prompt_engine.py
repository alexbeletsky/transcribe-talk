"""
Prompt Engine - Context assembly for AI conversations.

This module provides the PromptEngine class which is responsible for:
- Gathering system prompts and context
- Managing environmental information
- Preparing structured message lists for the AI
"""

import os
import platform
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from .history import Message, MessageRole

logger = logging.getLogger(__name__)


class PromptEngine:
    """
    Assembles context and prompts for AI conversations.
    
    This class is responsible for:
    - Building system prompts with context
    - Gathering environmental information
    - Managing long-term memory (future: CONTEXT.md)
    - Formatting messages for the ChatService
    """
    
    def __init__(self, workspace_path: Optional[Path] = None):
        """
        Initialize the PromptEngine.
        
        Args:
            workspace_path: Optional workspace path for context
        """
        self.workspace_path = workspace_path or Path.cwd()
        self._system_prompt_template = self._get_default_system_prompt()
        self._custom_context: List[str] = []
        
        logger.info(f"PromptEngine initialized with workspace: {self.workspace_path}")
    
    def set_system_prompt_template(self, template: str) -> None:
        """
        Set a custom system prompt template.
        
        Args:
            template: System prompt template with placeholders
        """
        self._system_prompt_template = template
        logger.debug("System prompt template updated")
    
    def add_custom_context(self, context: str) -> None:
        """
        Add custom context that will be included in prompts.
        
        Args:
            context: Additional context string
        """
        self._custom_context.append(context)
    
    def clear_custom_context(self) -> None:
        """Clear all custom context."""
        self._custom_context.clear()
    
    def build_system_prompt(self, include_env: bool = True) -> str:
        """
        Build the complete system prompt with context.
        
        Args:
            include_env: Whether to include environmental context
            
        Returns:
            Complete system prompt
        """
        # Gather context components
        context_parts = []
        
        # Add environmental context if requested
        if include_env:
            env_context = self._get_environmental_context()
            if env_context:
                context_parts.append("Environmental Context:")
                context_parts.append(env_context)
                context_parts.append("")
        
        # Add custom context
        if self._custom_context:
            context_parts.append("Additional Context:")
            context_parts.extend(self._custom_context)
            context_parts.append("")
        
        # Add workspace context
        workspace_context = self._get_workspace_context()
        if workspace_context:
            context_parts.append("Workspace Information:")
            context_parts.append(workspace_context)
            context_parts.append("")
        
        # Format the system prompt
        context_str = "\n".join(context_parts)
        system_prompt = self._system_prompt_template.format(
            context=context_str,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            workspace=str(self.workspace_path)
        )
        
        return system_prompt.strip()
    
    def prepare_messages(
        self,
        user_input: str,
        conversation_history: Optional[List[Message]] = None,
        include_system: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Prepare messages for the ChatService.
        
        Args:
            user_input: Current user input
            conversation_history: Optional conversation history
            include_system: Whether to include system prompt
            
        Returns:
            List of message dictionaries
        """
        messages = []
        
        # Add system prompt if requested
        if include_system:
            system_prompt = self.build_system_prompt()
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                messages.append(msg.to_dict())
        
        # Add current user input
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        return messages
    
    def _get_environmental_context(self) -> str:
        """
        Gather environmental information.
        
        Returns:
            Environmental context string
        """
        env_info = []
        
        # Operating system info
        env_info.append(f"OS: {platform.system()} {platform.release()}")
        env_info.append(f"Python: {platform.python_version()}")
        
        # Current working directory
        env_info.append(f"Working Directory: {os.getcwd()}")
        
        # Current time
        env_info.append(f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        return "\n".join(env_info)
    
    def _get_workspace_context(self) -> str:
        """
        Gather workspace information.
        
        Returns:
            Workspace context string
        """
        if not self.workspace_path.exists():
            return ""
        
        context_parts = []
        
        # Basic workspace info
        context_parts.append(f"Path: {self.workspace_path}")
        
        # Check for project files
        project_files = []
        for pattern in ["*.md", "*.txt", "*.json", "*.yaml", "*.yml"]:
            project_files.extend(self.workspace_path.glob(pattern))
        
        if project_files:
            context_parts.append("Project files found:")
            for file in sorted(project_files)[:10]:  # Limit to first 10
                context_parts.append(f"  - {file.name}")
        
        # Check for CONTEXT.md (future long-term memory)
        context_file = self.workspace_path / "CONTEXT.md"
        if context_file.exists():
            context_parts.append("\nLong-term memory available (CONTEXT.md)")
            # In the future, we'll read and include this content
        
        return "\n".join(context_parts)
    
    def _get_default_system_prompt(self) -> str:
        """
        Get the default system prompt template.
        
        Returns:
            Default system prompt template
        """
        return """You are TranscribeTalk, an AI assistant with voice interaction capabilities.

You can help users through natural conversation, and you have access to tools that allow you to interact with their local environment when needed.

{context}

Current session started at: {timestamp}
Working from: {workspace}

Guidelines:
1. Be conversational and natural in your responses
2. When using tools, explain what you're doing
3. Ask for clarification when needed
4. Provide helpful and accurate information
5. Respect user privacy and security

How can I help you today?"""
    
    def load_long_term_memory(self, context_file: Optional[Path] = None) -> Optional[str]:
        """
        Load long-term memory from CONTEXT.md.
        
        Args:
            context_file: Optional path to context file
            
        Returns:
            Context content if available
        """
        if context_file is None:
            context_file = self.workspace_path / "CONTEXT.md"
        
        if not context_file.exists():
            return None
        
        try:
            content = context_file.read_text(encoding="utf-8")
            logger.info(f"Loaded long-term memory from {context_file}")
            return content
        except Exception as e:
            logger.error(f"Failed to load long-term memory: {e}")
            return None
    
    def get_file_tree(self, max_depth: int = 2) -> str:
        """
        Get a simple file tree of the workspace.
        
        Args:
            max_depth: Maximum depth to traverse
            
        Returns:
            File tree as string
        """
        def _build_tree(path: Path, prefix: str = "", depth: int = 0) -> List[str]:
            if depth >= max_depth:
                return []
            
            items = []
            try:
                entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
                for i, entry in enumerate(entries):
                    is_last = i == len(entries) - 1
                    current_prefix = "└── " if is_last else "├── "
                    next_prefix = "    " if is_last else "│   "
                    
                    if entry.is_dir():
                        items.append(f"{prefix}{current_prefix}{entry.name}/")
                        items.extend(_build_tree(
                            entry, 
                            prefix + next_prefix,
                            depth + 1
                        ))
                    else:
                        items.append(f"{prefix}{current_prefix}{entry.name}")
            except PermissionError:
                items.append(f"{prefix}[Permission Denied]")
            
            return items
        
        tree_lines = [f"{self.workspace_path}/"]
        tree_lines.extend(_build_tree(self.workspace_path))
        
        return "\n".join(tree_lines)