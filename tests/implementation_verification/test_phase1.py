#!/usr/bin/env python3
"""
Test script for Phase 1 - Foundational Architecture.

This script was used to verify the implementation of the core agentic components
during Phase 1 of the TranscribeTalk transformation.

Tests included:
1. Core module imports
2. Event system functionality
3. Component initialization
4. Basic integration
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def test_core_imports():
    """Test that all core modules can be imported."""
    print("Testing core imports...")
    
    try:
        # Test AI module imports
        from transcribe_talk.ai import (
            Agent, AgentConfig, ChatService, ConversationHistory,
            PromptEngine, ToolScheduler, Turn, TurnEvent
        )
        print("✓ All core AI modules imported successfully")
        
        # Test events
        from transcribe_talk.ai.events import (
            ContentEvent, ToolCallRequestEvent, FinishedEvent, ErrorEvent
        )
        print("✓ Event types imported successfully")
        
        # Test tools module
        from transcribe_talk.tools import ToolRegistry, ToolMetadata
        print("✓ Tools module imported successfully")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_event_creation():
    """Test event creation and attributes."""
    print("\nTesting event system...")
    
    try:
        from transcribe_talk.ai.events import (
            ContentEvent, ToolCallRequestEvent, FinishedEvent, ErrorEvent
        )
        
        # Test ContentEvent
        content_event = ContentEvent(content="Hello, world!")
        assert content_event.content == "Hello, world!"
        assert content_event.event_type.value == "content"
        print("✓ ContentEvent creation works")
        
        # Test ToolCallRequestEvent
        tool_event = ToolCallRequestEvent(
            tool_call_id="123",
            function_name="test_function", 
            arguments='{"arg": "value"}'
        )
        assert tool_event.function_name == "test_function"
        print("✓ ToolCallRequestEvent creation works")
        
        # Test FinishedEvent
        finished_event = FinishedEvent(
            finish_reason="stop",
            usage={"total_tokens": 100}
        )
        assert finished_event.finish_reason == "stop"
        print("✓ FinishedEvent creation works")
        
        return True
    except Exception as e:
        print(f"✗ Event test error: {e}")
        return False


def test_component_initialization():
    """Test that core components can be initialized."""
    print("\nTesting component initialization...")
    
    try:
        from transcribe_talk.ai.history import ConversationHistory, MessageRole
        from transcribe_talk.ai.prompt_engine import PromptEngine
        from transcribe_talk.tools import ToolRegistry
        from pathlib import Path
        
        # Test ConversationHistory
        history = ConversationHistory(max_messages=50, max_tokens=4000)
        history.add_user_message("Test message")
        assert len(history.messages) == 1
        assert history.messages[0].role == MessageRole.USER
        print("✓ ConversationHistory initialized and working")
        
        # Test PromptEngine
        engine = PromptEngine(workspace_path=Path.cwd())
        system_prompt = engine.build_system_prompt(include_env=False)
        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 0
        print("✓ PromptEngine initialized and working")
        
        # Test ToolRegistry
        registry = ToolRegistry()
        assert isinstance(registry.list_tools(), list)
        print("✓ ToolRegistry initialized and working")
        
        return True
    except Exception as e:
        print(f"✗ Component initialization error: {e}")
        return False


def test_legacy_preservation():
    """Test that legacy modules are preserved."""
    print("\nTesting legacy code preservation...")
    
    legacy_path = Path("src/transcribe_talk/ai/ai_legacy")
    
    if legacy_path.exists():
        legacy_files = list(legacy_path.glob("*.py"))
        print(f"✓ Legacy directory exists with {len(legacy_files)} files")
        
        expected_files = ["__init__.py", "chat.py", "transcriber.py"]
        found_files = [f.name for f in legacy_files]
        
        for expected in expected_files:
            if expected in found_files:
                print(f"  ✓ {expected} preserved")
            else:
                print(f"  ✗ {expected} missing")
        
        return len(set(expected_files) & set(found_files)) >= 2
    else:
        print("✗ Legacy directory not found")
        return False


def main():
    """Run all Phase 1 tests."""
    print("Phase 1 Test - Foundational Architecture\n" + "="*40)
    
    results = []
    
    # Run tests
    results.append(test_core_imports())
    results.append(test_event_creation())
    results.append(test_component_initialization())
    results.append(test_legacy_preservation())
    
    # Summary
    print("\n" + "="*40)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✓ All tests passed ({passed}/{total})")
        print("\nPhase 1 foundational architecture is properly implemented!")
        return 0
    else:
        print(f"✗ Some tests failed ({passed}/{total})")
        return 1


if __name__ == "__main__":
    sys.exit(main())