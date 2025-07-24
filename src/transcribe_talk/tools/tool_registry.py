"""
Tool Registry - Manages tool discovery and registration.

This module provides the ToolRegistry class which is responsible for:
- Registering and retrieving tool implementations by name
- Generating OpenAI functions schema dynamically from Python function signatures
- Managing tool metadata and configurations
"""

import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, get_type_hints
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Categories for organizing tools."""
    FILE_SYSTEM = "file_system"
    MEMORY = "memory"
    WEB = "web"
    SYSTEM = "system"
    UTILITY = "utility"


@dataclass
class ToolMetadata:
    """Metadata for a registered tool."""
    name: str
    description: str
    category: ToolCategory
    requires_confirmation: bool = True
    timeout_seconds: float = 30.0
    retry_count: int = 3


@dataclass
class ToolParameter:
    """Parameter definition for a tool."""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


class ToolRegistry:
    """
    Central registry for managing tool implementations.
    
    This class is responsible for:
    - Registering tools with their metadata
    - Generating OpenAI function schemas
    - Retrieving tool implementations by name
    - Managing tool lifecycles
    """
    
    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, Callable] = {}
        self._metadata: Dict[str, ToolMetadata] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}
        
        logger.info("ToolRegistry initialized")
    
    def register(
        self,
        func: Callable,
        metadata: ToolMetadata,
        parameter_descriptions: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Register a tool with the registry.
        
        Args:
            func: The tool function to register
            metadata: Tool metadata including name, description, etc.
            parameter_descriptions: Optional descriptions for function parameters
        """
        tool_name = metadata.name
        
        if tool_name in self._tools:
            logger.warning(f"Tool '{tool_name}' already registered, overwriting")
        
        self._tools[tool_name] = func
        self._metadata[tool_name] = metadata
        
        # Generate OpenAI function schema
        schema = self._generate_function_schema(func, metadata, parameter_descriptions)
        self._schemas[tool_name] = schema
        
        logger.info(f"Registered tool: {tool_name} ({metadata.category.value})")
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """
        Retrieve a tool implementation by name.
        
        Args:
            name: The name of the tool
            
        Returns:
            The tool function if found, None otherwise
        """
        return self._tools.get(name)
    
    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        """
        Retrieve tool metadata by name.
        
        Args:
            name: The name of the tool
            
        Returns:
            The tool metadata if found, None otherwise
        """
        return self._metadata.get(name)
    
    def get_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the OpenAI function schema for a tool.
        
        Args:
            name: The name of the tool
            
        Returns:
            The function schema if found, None otherwise
        """
        return self._schemas.get(name)
    
    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """
        Get all registered function schemas for OpenAI API.
        
        Returns:
            List of all function schemas
        """
        return list(self._schemas.values())
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[str]:
        """
        List all registered tool names, optionally filtered by category.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of tool names
        """
        if category is None:
            return list(self._tools.keys())
        
        return [
            name for name, metadata in self._metadata.items()
            if metadata.category == category
        ]
    
    def _generate_function_schema(
        self,
        func: Callable,
        metadata: ToolMetadata,
        parameter_descriptions: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Generate OpenAI function schema from a Python function.
        
        Args:
            func: The function to generate schema for
            metadata: Tool metadata
            parameter_descriptions: Optional parameter descriptions
            
        Returns:
            OpenAI function schema dictionary
        """
        # Get function signature
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        
        # Build parameters schema
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param_name, param in sig.parameters.items():
            # Skip self parameter for methods
            if param_name == "self":
                continue
                
            # Get type information
            param_type = type_hints.get(param_name, Any)
            json_type = self._python_type_to_json_type(param_type)
            
            # Build parameter schema
            param_schema = {"type": json_type}
            
            # Add description if provided
            if parameter_descriptions and param_name in parameter_descriptions:
                param_schema["description"] = parameter_descriptions[param_name]
            
            parameters["properties"][param_name] = param_schema
            
            # Check if parameter is required
            if param.default == inspect.Parameter.empty:
                parameters["required"].append(param_name)
        
        # Build complete function schema
        schema = {
            "name": metadata.name,
            "description": metadata.description,
            "parameters": parameters
        }
        
        return schema
    
    def _python_type_to_json_type(self, python_type: type) -> str:
        """
        Convert Python type to JSON Schema type.
        
        Args:
            python_type: Python type
            
        Returns:
            JSON Schema type string
        """
        type_mapping = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
            type(None): "null"
        }
        
        # Handle Optional types
        if hasattr(python_type, "__origin__"):
            if python_type.__origin__ is type(Optional):
                # Get the actual type from Optional[T]
                actual_type = python_type.__args__[0]
                return self._python_type_to_json_type(actual_type)
        
        return type_mapping.get(python_type, "string")
    
    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._metadata.clear()
        self._schemas.clear()
        logger.info("ToolRegistry cleared")


# Global registry instance
_global_registry = ToolRegistry()


def get_global_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    return _global_registry


def register_tool(
    metadata: ToolMetadata,
    parameter_descriptions: Optional[Dict[str, str]] = None
) -> Callable:
    """
    Decorator for registering tools with the global registry.
    
    Args:
        metadata: Tool metadata
        parameter_descriptions: Optional parameter descriptions
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        get_global_registry().register(func, metadata, parameter_descriptions)
        return func
    
    return decorator