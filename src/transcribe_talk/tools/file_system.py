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


@register_tool(
    metadata=ToolMetadata(
        name="read_file",
        description="Read the contents of a text file",
        category=ToolCategory.FILE_SYSTEM,
        requires_confirmation=False,  # Safe read-only operation
        timeout_seconds=10.0
    ),
    parameter_descriptions={
        "file_path": "Path to the file to read",
        "encoding": "File encoding (default: utf-8)",
        "max_lines": "Maximum number of lines to read (default: all)",
        "preview": "If True, only show first and last 10 lines for large files"
    }
)
def read_file(
    file_path: str,
    encoding: str = "utf-8",
    max_lines: Optional[int] = None,
    preview: bool = True
) -> str:
    """
    Read the contents of a text file.
    
    Args:
        file_path: Path to the file to read
        encoding: File encoding (default: utf-8)
        max_lines: Maximum number of lines to read (None for all)
        preview: For large files, show preview instead of full content
        
    Returns:
        File contents or error message
    """
    try:
        # Resolve path
        file_path_obj = Path(file_path).resolve()
        
        # Security check
        cwd = Path.cwd()
        try:
            file_path_obj.relative_to(cwd)
        except ValueError:
            logger.warning(f"Reading file outside workspace: {file_path_obj}")
        
        # Check file exists and is a file
        if not file_path_obj.exists():
            return f"Error: File '{file_path}' does not exist"
        
        if not file_path_obj.is_file():
            return f"Error: '{file_path}' is not a file"
        
        # Check file size
        file_size = file_path_obj.stat().st_size
        
        # Prevent reading very large files
        max_size_mb = 10
        if file_size > max_size_mb * 1024 * 1024:
            return (
                f"Error: File too large ({file_size / (1024*1024):.1f} MB). "
                f"Maximum allowed: {max_size_mb} MB"
            )
        
        # Read file
        try:
            with open(file_path_obj, 'r', encoding=encoding) as f:
                if max_lines:
                    lines = [f.readline() for _ in range(max_lines)]
                    lines = [line for line in lines if line]  # Remove empty lines at end
                else:
                    lines = f.readlines()
            
            total_lines = len(lines)
            
            # Handle preview mode for large files
            if preview and total_lines > 50:
                preview_lines = []
                preview_lines.append(f"File: {file_path_obj}")
                preview_lines.append(f"Total lines: {total_lines}")
                preview_lines.append(f"Size: {_format_size(file_size)}")
                preview_lines.append("\n--- First 10 lines ---")
                preview_lines.extend(lines[:10])
                preview_lines.append("\n--- ... ---\n")
                preview_lines.append("--- Last 10 lines ---")
                preview_lines.extend(lines[-10:])
                preview_lines.append(f"\n(Use preview=False to see full content)")
                return '\n'.join(preview_lines)
            else:
                # Return full content
                content = ''.join(lines)
                if total_lines > 20:
                    header = f"File: {file_path_obj} ({total_lines} lines, {_format_size(file_size)})\n\n"
                    return header + content
                else:
                    return content
                
        except UnicodeDecodeError:
            return f"Error: Unable to read file with encoding '{encoding}'. Try a different encoding."
        except Exception as e:
            return f"Error reading file: {str(e)}"
            
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return f"Error: {str(e)}"


@register_tool(
    metadata=ToolMetadata(
        name="write_file", 
        description="Write or create a text file",
        category=ToolCategory.FILE_SYSTEM,
        requires_confirmation=True,  # Requires confirmation for safety
        timeout_seconds=10.0
    ),
    parameter_descriptions={
        "file_path": "Path where to write the file",
        "content": "Content to write to the file",
        "encoding": "File encoding (default: utf-8)",
        "mode": "Write mode: 'write' (overwrite) or 'append' (add to end)",
        "create_dirs": "Create parent directories if they don't exist"
    }
)
def write_file(
    file_path: str,
    content: str,
    encoding: str = "utf-8",
    mode: str = "write",
    create_dirs: bool = False
) -> str:
    """
    Write content to a file.
    
    Args:
        file_path: Path where to write the file
        content: Content to write
        encoding: File encoding (default: utf-8)
        mode: 'write' to overwrite, 'append' to add to end
        create_dirs: Create parent directories if needed
        
    Returns:
        Success message or error
    """
    try:
        # Validate mode
        if mode not in ["write", "append"]:
            return "Error: mode must be 'write' or 'append'"
        
        # Resolve path
        file_path_obj = Path(file_path).resolve()
        
        # Security check - ensure we're not writing outside workspace
        cwd = Path.cwd()
        try:
            file_path_obj.relative_to(cwd)
        except ValueError:
            return f"Error: Cannot write files outside the workspace"
        
        # Create parent directories if requested
        if create_dirs:
            file_path_obj.parent.mkdir(parents=True, exist_ok=True)
        elif not file_path_obj.parent.exists():
            return f"Error: Directory '{file_path_obj.parent}' does not exist. Use create_dirs=True to create it."
        
        # Check if file exists for appropriate warnings
        file_exists = file_path_obj.exists()
        
        # Determine file mode
        file_mode = 'w' if mode == "write" else 'a'
        
        # Write file
        try:
            with open(file_path_obj, file_mode, encoding=encoding) as f:
                f.write(content)
            
            # Prepare success message
            action = "Overwrote" if mode == "write" and file_exists else "Created" if not file_exists else "Appended to"
            size = len(content.encode(encoding))
            
            return f"{action} file: {file_path_obj} ({_format_size(size)} written)"
            
        except Exception as e:
            return f"Error writing file: {str(e)}"
            
    except Exception as e:
        logger.error(f"Error writing file {file_path}: {e}")
        return f"Error: {str(e)}"


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