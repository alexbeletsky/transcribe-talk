"""
Memory management tools for TranscribeTalk.

This module provides tools for managing long-term memory:
- save_memory: Save information to CONTEXT.md
- (future) search_memory: Search through saved memories
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from .tool_registry import register_tool, ToolMetadata, ToolCategory

logger = logging.getLogger(__name__)


@register_tool(
    metadata=ToolMetadata(
        name="save_memory",
        description="Save important information to long-term memory (CONTEXT.md)",
        category=ToolCategory.MEMORY,
        requires_confirmation=True,  # Requires confirmation as it modifies memory
        timeout_seconds=10.0
    ),
    parameter_descriptions={
        "content": "The information to save to memory",
        "category": "Category for the memory (e.g., 'user_preference', 'learned_fact', 'context')",
        "tags": "Comma-separated tags for easier retrieval",
        "mode": "How to add the memory: 'append' (default) or 'replace'"
    }
)
def save_memory(
    content: str,
    category: str = "general",
    tags: str = "",
    mode: str = "append"
) -> str:
    """
    Save information to long-term memory (CONTEXT.md).
    
    Args:
        content: The information to save
        category: Category for organization
        tags: Comma-separated tags
        mode: 'append' to add to existing memory, 'replace' to overwrite
        
    Returns:
        Success message or error
    """
    try:
        # Validate mode
        if mode not in ["append", "replace"]:
            return "Error: mode must be 'append' or 'replace'"
        
        # Get CONTEXT.md path
        context_path = Path.cwd() / "CONTEXT.md"
        
        # Prepare memory entry
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        memory_entry = []
        
        if mode == "replace":
            # Start fresh
            memory_entry.append("# TranscribeTalk Long-Term Memory\n")
            memory_entry.append("This file contains important context and memories saved during conversations.\n")
        
        # Format the new memory
        memory_entry.append(f"\n## [{category}] {timestamp}")
        
        if tags:
            memory_entry.append(f"**Tags:** {tags}")
        
        memory_entry.append("")
        memory_entry.append(content)
        memory_entry.append("")
        memory_entry.append("---")
        
        memory_text = '\n'.join(memory_entry)
        
        # Write to file
        try:
            if mode == "append" and context_path.exists():
                # Append to existing content
                with open(context_path, 'a', encoding='utf-8') as f:
                    f.write('\n' + memory_text)
                action = "Added to"
            else:
                # Write new file or replace
                with open(context_path, 'w', encoding='utf-8') as f:
                    f.write(memory_text)
                action = "Created" if not context_path.exists() else "Replaced"
            
            # Count total memories
            if context_path.exists():
                with open(context_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    memory_count = content.count('\n## [')
            else:
                memory_count = 1
            
            return (
                f"{action} memory in CONTEXT.md\n"
                f"Category: {category}\n"
                f"Tags: {tags or 'none'}\n"
                f"Total memories: {memory_count}"
            )
            
        except Exception as e:
            return f"Error writing to CONTEXT.md: {str(e)}"
            
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
        return f"Error: {str(e)}"


@register_tool(
    metadata=ToolMetadata(
        name="read_memory",
        description="Read the current long-term memory from CONTEXT.md",
        category=ToolCategory.MEMORY,
        requires_confirmation=False,  # Safe read-only operation
        timeout_seconds=10.0
    ),
    parameter_descriptions={
        "category_filter": "Optional category to filter memories",
        "recent_only": "If True, only show the 5 most recent memories"
    }
)
def read_memory(
    category_filter: Optional[str] = None,
    recent_only: bool = False
) -> str:
    """
    Read the current long-term memory.
    
    Args:
        category_filter: Optional category to filter by
        recent_only: Only show recent memories
        
    Returns:
        Memory content or message
    """
    try:
        context_path = Path.cwd() / "CONTEXT.md"
        
        if not context_path.exists():
            return "No long-term memory found. Use 'save_memory' to create one."
        
        with open(context_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            return "Long-term memory is empty."
        
        # Apply filters if requested
        if category_filter or recent_only:
            lines = content.split('\n')
            filtered_lines = []
            current_memory = []
            memory_count = 0
            
            for line in lines:
                if line.startswith('## ['):
                    # New memory entry
                    if current_memory and (not category_filter or f"[{category_filter}]" in current_memory[0]):
                        memory_count += 1
                        if not recent_only or memory_count <= 5:
                            filtered_lines.extend(current_memory)
                            filtered_lines.append('')
                    current_memory = [line]
                elif current_memory:
                    current_memory.append(line)
            
            # Don't forget the last memory
            if current_memory and (not category_filter or f"[{category_filter}]" in current_memory[0]):
                memory_count += 1
                if not recent_only or memory_count <= 5:
                    filtered_lines.extend(current_memory)
            
            if filtered_lines:
                filter_desc = []
                if category_filter:
                    filter_desc.append(f"category='{category_filter}'")
                if recent_only:
                    filter_desc.append("recent only")
                header = f"# Long-term Memory ({', '.join(filter_desc)})\n\n"
                return header + '\n'.join(filtered_lines)
            else:
                return f"No memories found matching the filter."
        else:
            return content
            
    except Exception as e:
        logger.error(f"Error reading memory: {e}")
        return f"Error reading CONTEXT.md: {str(e)}"


# Register this module's tools when imported
logger.info("Memory tools registered")