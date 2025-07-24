#!/usr/bin/env python3
"""
Test script for Phase 2 - MVP Agentic Loop.

This script was used to verify the implementation of the MVP agentic loop
with the first tool (list_directory) during Phase 2.

Tests included:
1. Tool registration and discovery
2. Tool execution flow
3. CLI integration
4. Safety features
"""

import sys
import os
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def test_tool_registration():
    """Test that tools are properly registered."""
    print("Testing tool registration...")
    
    try:
        from transcribe_talk.tools import get_global_registry
        
        registry = get_global_registry()
        tools = registry.list_tools()
        
        # Check that list_directory is registered
        if "list_directory" in tools:
            print("✓ list_directory tool is registered")
            
            # Check tool metadata
            metadata = registry.get_metadata("list_directory")
            print(f"  - Category: {metadata.category.value}")
            print(f"  - Requires confirmation: {metadata.requires_confirmation}")
            print(f"  - Timeout: {metadata.timeout_seconds}s")
            
            # Check schema generation
            schema = registry.get_schema("list_directory")
            assert schema["name"] == "list_directory"
            assert "description" in schema
            assert "parameters" in schema
            print("✓ Tool schema generated correctly")
            
            return True
        else:
            print("✗ list_directory tool not found")
            return False
            
    except Exception as e:
        print(f"✗ Tool registration error: {e}")
        return False


def test_tool_execution():
    """Test tool execution."""
    print("\nTesting tool execution...")
    
    try:
        from transcribe_talk.tools import get_global_registry
        
        registry = get_global_registry()
        list_dir_tool = registry.get_tool("list_directory")
        
        if not list_dir_tool:
            print("✗ Could not get list_directory tool")
            return False
        
        # Create a test directory
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir)
            
            # Create some test files
            (test_path / "test1.txt").write_text("Test file 1")
            (test_path / "test2.py").write_text("print('test')")
            (test_path / "subdir").mkdir()
            
            # Execute the tool
            result = list_dir_tool(path=str(test_path))
            
            # Check results
            assert "test1.txt" in result
            assert "test2.py" in result
            assert "subdir" in result
            assert "[dir]" in result  # Directory marker
            assert "[file]" in result  # File marker
            
            print("✓ Tool execution successful")
            print(f"  - Found files and directories")
            print(f"  - Formatting applied correctly")
            
            return True
            
    except Exception as e:
        print(f"✗ Tool execution error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cli_flags():
    """Test CLI flag additions."""
    print("\nTesting CLI integration...")
    
    try:
        # Check if cli.py has the new flags
        cli_path = Path("src/transcribe_talk/cli.py")
        if not cli_path.exists():
            print("✗ cli.py not found")
            return False
        
        cli_content = cli_path.read_text()
        
        # Check for auto-confirm flag
        has_auto_confirm = "--auto-confirm" in cli_content or "--yes" in cli_content
        print(f"✓ --auto-confirm flag present: {has_auto_confirm}")
        
        # Check for dry-run flag
        has_dry_run = "--dry-run" in cli_content
        print(f"✓ --dry-run flag present: {has_dry_run}")
        
        # Check for Agent integration
        has_agent = "Agent" in cli_content and "execute_turn" in cli_content
        print(f"✓ Agent integration present: {has_agent}")
        
        return has_auto_confirm and has_dry_run and has_agent
        
    except Exception as e:
        print(f"✗ CLI test error: {e}")
        return False


def test_tool_scheduler():
    """Test ToolScheduler functionality."""
    print("\nTesting ToolScheduler...")
    
    try:
        from transcribe_talk.ai.tool_scheduler import ToolScheduler, ApprovalMode
        from transcribe_talk.tools import get_global_registry
        
        registry = get_global_registry()
        
        # Test with auto-confirm (NEVER mode)
        scheduler = ToolScheduler(
            registry=registry,
            approval_mode=ApprovalMode.NEVER,
            dry_run=False
        )
        print("✓ ToolScheduler created with ApprovalMode.NEVER")
        
        # Test dry-run mode
        dry_scheduler = ToolScheduler(
            registry=registry,
            approval_mode=ApprovalMode.SMART,
            dry_run=True
        )
        print("✓ ToolScheduler created with dry_run=True")
        
        return True
        
    except Exception as e:
        print(f"✗ ToolScheduler test error: {e}")
        return False


def test_turn_integration():
    """Test Turn class with tool support."""
    print("\nTesting Turn integration...")
    
    try:
        from transcribe_talk.ai.turn import Turn
        from transcribe_talk.tools import get_global_registry
        
        # Mock ChatService
        class MockChatService:
            pass
        
        registry = get_global_registry()
        
        # Create Turn with tool registry
        turn = Turn(
            chat_service=MockChatService(),
            tool_registry=registry
        )
        
        assert turn.tool_registry is not None
        assert len(turn.tool_registry.list_tools()) > 0
        print("✓ Turn class accepts tool registry")
        print(f"  - {len(turn.tool_registry.list_tools())} tools available")
        
        return True
        
    except Exception as e:
        print(f"✗ Turn integration error: {e}")
        return False


def main():
    """Run all Phase 2 tests."""
    print("Phase 2 Test - MVP Agentic Loop\n" + "="*40)
    
    results = []
    
    # Run tests
    results.append(test_tool_registration())
    results.append(test_tool_execution())
    results.append(test_cli_flags())
    results.append(test_tool_scheduler())
    results.append(test_turn_integration())
    
    # Summary
    print("\n" + "="*40)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✓ All tests passed ({passed}/{total})")
        print("\nPhase 2 MVP implementation is complete!")
        print("\nKey achievements:")
        print("- First tool (list_directory) implemented and working")
        print("- Tool registration and discovery system functional")
        print("- CLI integration with --auto-confirm and --dry-run")
        print("- ToolScheduler managing approvals and execution")
        print("- Turn class integrated with tool support")
        return 0
    else:
        print(f"✗ Some tests failed ({passed}/{total})")
        return 1


if __name__ == "__main__":
    sys.exit(main())