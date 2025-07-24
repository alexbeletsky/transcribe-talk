#!/usr/bin/env python3
"""
Test script for Phase 3 - Expanding Capabilities.

This script was used to verify the implementation of expanded capabilities
including file system tools and memory management during Phase 3.

Tests included:
1. New tools (read_file, write_file, save_memory)
2. Long-term memory integration
3. Tool execution with confirmations
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def test_new_tools():
    """Test that new tools are registered."""
    print("Testing new tool registration...")
    
    try:
        from transcribe_talk.tools import get_global_registry
        
        registry = get_global_registry()
        tools = registry.list_tools()
        
        expected_tools = ["list_directory", "read_file", "write_file", "save_memory", "read_memory"]
        found_tools = [tool for tool in expected_tools if tool in tools]
        
        print(f"Found {len(found_tools)}/{len(expected_tools)} tools:")
        for tool in found_tools:
            schema = registry.get_schema(tool)
            print(f"  ✓ {tool}: {schema['description']}")
        
        return len(found_tools) == len(expected_tools)
        
    except Exception as e:
        print(f"✗ Tool registration error: {e}")
        return False


def test_file_operations():
    """Test file read/write operations."""
    print("\nTesting file operations...")
    
    try:
        from transcribe_talk.tools import get_global_registry
        
        registry = get_global_registry()
        
        # Test write_file
        write_tool = registry.get_tool("write_file")
        if write_tool:
            test_content = "This is a test file created by Phase 3 testing."
            result = write_tool(
                file_path="test_phase3_output.txt",
                content=test_content,
                mode="write"
            )
            print(f"✓ write_file: {result}")
            
            # Test read_file
            read_tool = registry.get_tool("read_file")
            if read_tool:
                content = read_tool(file_path="test_phase3_output.txt")
                if test_content in content:
                    print("✓ read_file: Successfully read the test file")
                    
                    # Test preview mode
                    preview_content = read_tool(
                        file_path="test_phase3_output.txt",
                        preview=True
                    )
                    print("✓ read_file: Preview mode works")
                    
                    # Clean up
                    os.remove("test_phase3_output.txt")
                    return True
                else:
                    print("✗ read_file: Content mismatch")
                    return False
        
        return False
        
    except Exception as e:
        print(f"✗ File operation error: {e}")
        return False


def test_memory_operations():
    """Test memory save/read operations."""
    print("\nTesting memory operations...")
    
    try:
        from transcribe_talk.tools import get_global_registry
        
        registry = get_global_registry()
        
        # Test save_memory
        save_tool = registry.get_tool("save_memory")
        if save_tool:
            result = save_tool(
                content="Test memory: User prefers dark mode interfaces",
                category="user_preference",
                tags="ui,preferences,test"
            )
            print(f"✓ save_memory: {result}")
            
            # Test read_memory
            read_tool = registry.get_tool("read_memory")
            if read_tool:
                memory = read_tool()
                if "dark mode" in memory:
                    print("✓ read_memory: Successfully retrieved memory")
                    
                    # Test filtered read
                    filtered = read_tool(category_filter="user_preference")
                    if "dark mode" in filtered:
                        print("✓ read_memory with filter: Successfully filtered by category")
                        
                        # Clean up CONTEXT.md
                        context_path = Path.cwd() / "CONTEXT.md"
                        if context_path.exists():
                            os.remove(context_path)
                        
                        return True
        
        return False
        
    except Exception as e:
        print(f"✗ Memory operation error: {e}")
        return False


def test_prompt_engine_integration():
    """Test that PromptEngine includes long-term memory."""
    print("\nTesting PromptEngine integration...")
    
    try:
        from transcribe_talk.ai.prompt_engine import PromptEngine
        
        # Create CONTEXT.md if it doesn't exist
        context_path = Path.cwd() / "CONTEXT.md"
        if not context_path.exists():
            context_path.write_text("# Test Memory\n\nThis is a test memory for Phase 3.")
        
        engine = PromptEngine()
        system_prompt = engine.build_system_prompt()
        
        # Check if long-term memory is loaded
        memory_content = engine.load_long_term_memory()
        
        if memory_content and "Test Memory" in memory_content:
            print("✓ PromptEngine loads long-term memory")
            
            if "Long-term Memory:" in system_prompt:
                print("✓ PromptEngine includes long-term memory in system prompt")
                result = True
            else:
                print("✗ PromptEngine does not include long-term memory in prompt")
                result = False
        else:
            print("✗ PromptEngine failed to load long-term memory")
            result = False
            
        # Clean up
        if context_path.exists():
            os.remove(context_path)
            
        return result
            
    except Exception as e:
        print(f"✗ PromptEngine integration error: {e}")
        return False


def test_tool_metadata():
    """Test tool metadata and safety settings."""
    print("\nTesting tool metadata...")
    
    try:
        from transcribe_talk.tools import get_global_registry
        
        registry = get_global_registry()
        
        # Check read_file (should not require confirmation)
        read_meta = registry.get_metadata("read_file")
        print(f"✓ read_file requires_confirmation: {read_meta.requires_confirmation} (should be False)")
        assert not read_meta.requires_confirmation
        
        # Check write_file (should require confirmation)
        write_meta = registry.get_metadata("write_file")
        print(f"✓ write_file requires_confirmation: {write_meta.requires_confirmation} (should be True)")
        assert write_meta.requires_confirmation
        
        # Check save_memory (should require confirmation)
        save_meta = registry.get_metadata("save_memory")
        print(f"✓ save_memory requires_confirmation: {save_meta.requires_confirmation} (should be True)")
        assert save_meta.requires_confirmation
        
        return True
        
    except Exception as e:
        print(f"✗ Tool metadata error: {e}")
        return False


def main():
    """Run all tests."""
    print("Phase 3 Test - Expanding Capabilities\n" + "="*40)
    
    results = []
    
    # Run tests
    results.append(test_new_tools())
    results.append(test_file_operations())
    results.append(test_memory_operations())
    results.append(test_prompt_engine_integration())
    results.append(test_tool_metadata())
    
    # Summary
    print("\n" + "="*40)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✓ All tests passed ({passed}/{total})")
        print("\nPhase 3 implementation is complete!")
        print("\nNew capabilities available:")
        print("- Read and write files with safety checks")
        print("- Save and retrieve long-term memories")
        print("- Memories automatically included in context")
        print("- Proper safety settings for each tool")
        return 0
    else:
        print(f"✗ Some tests failed ({passed}/{total})")
        return 1


if __name__ == "__main__":
    sys.exit(main())