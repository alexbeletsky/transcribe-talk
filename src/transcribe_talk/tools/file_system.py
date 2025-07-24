"""
File system tools for TranscribeTalk.

This module provides tools for interacting with the file system:
- list_directory: List contents of a directory
- (future) read_file: Read file contents
- (future) write_file: Write to a file
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .tool_registry import register_tool, ToolMetadata, ToolCategory

logger = logging.getLogger(__name__)


@register_tool(
    metadata=ToolMetadata(
        name="list_directory",
        description="List the contents of a directory, including files and subdirectories",
        category=ToolCategory.FILE_SYSTEM,
        requires_confirmation=False,  # Safe read-only operation
        timeout_seconds=10.0
    ),
    parameter_descriptions={
        "path": "The directory path to list. Use '.' for current directory.",
        "show_hidden": "Whether to include hidden files (starting with .)",
        "sort_by": "How to sort results: 'name', 'size', 'modified', or 'type'"
    }
)
def list_directory(
    path: str = ".",
    show_hidden: bool = False,
    sort_by: str = "name"
) -> str:
    """
    List the contents of a directory.
    
    Args:
        path: Directory path to list (default: current directory)
        show_hidden: Include hidden files/directories
        sort_by: Sort order ('name', 'size', 'modified', 'type')
        
    Returns:
        Formatted directory listing
    """
    try:
        # Resolve path
        dir_path = Path(path).resolve()
        
        # Security check - ensure we're not going outside workspace
        cwd = Path.cwd()
        try:
            dir_path.relative_to(cwd)
        except ValueError:
            # Allow reading from parent directories but log it
            logger.warning(f"Listing directory outside workspace: {dir_path}")
        
        if not dir_path.exists():
            return f"Error: Directory '{path}' does not exist"
        
        if not dir_path.is_dir():
            return f"Error: '{path}' is not a directory"
        
        # Get directory contents
        items = []
        try:
            for item in dir_path.iterdir():
                # Skip hidden files if not requested
                if not show_hidden and item.name.startswith('.'):
                    continue
                
                # Get item info
                try:
                    stat = item.stat()
                    item_info = {
                        'name': item.name,
                        'type': 'dir' if item.is_dir() else 'file',
                        'size': stat.st_size if not item.is_dir() else None,
                        'modified': stat.st_mtime
                    }
                    items.append(item_info)
                except (OSError, PermissionError) as e:
                    logger.warning(f"Cannot stat {item}: {e}")
                    items.append({
                        'name': item.name,
                        'type': 'unknown',
                        'size': None,
                        'modified': 0
                    })
                    
        except PermissionError:
            return f"Error: Permission denied accessing '{path}'"
        
        # Sort items
        if sort_by == 'size':
            items.sort(key=lambda x: x['size'] or 0, reverse=True)
        elif sort_by == 'modified':
            items.sort(key=lambda x: x['modified'], reverse=True)
        elif sort_by == 'type':
            items.sort(key=lambda x: (x['type'] != 'dir', x['name'].lower()))
        else:  # default: name
            items.sort(key=lambda x: x['name'].lower())
        
        # Format output
        output = [f"Directory: {dir_path}\n"]
        
        if not items:
            output.append("(empty directory)")
        else:
            # Separate directories and files
            dirs = [item for item in items if item['type'] == 'dir']
            files = [item for item in items if item['type'] == 'file']
            
            if dirs:
                output.append(f"\nDirectories ({len(dirs)}):")
                for item in dirs:
                    output.append(f"  📁 {item['name']}/")
            
            if files:
                output.append(f"\nFiles ({len(files)}):")
                for item in files:
                    size_str = _format_size(item['size']) if item['size'] is not None else 'unknown'
                    output.append(f"  📄 {item['name']} ({size_str})")
            
            # Summary
            output.append(f"\nTotal: {len(dirs)} directories, {len(files)} files")
        
        return '\n'.join(output)
        
    except Exception as e:
        logger.error(f"Error listing directory {path}: {e}")
        return f"Error listing directory: {str(e)}"


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


# Register this module's tools when imported
logger.info("File system tools registered")