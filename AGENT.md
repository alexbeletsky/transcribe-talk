# Agentic Features: Technical Vision & Development Plan (v4)

This document outlines the technical vision and phased development plan for evolving TranscribeTalk from a voice-to-voice application into a conversational AI agent, inspired by the architecture of `gemini-cli`.

## 1. High-Level Goal

To enhance TranscribeTalk with agentic capabilities, allowing it to interact with the user's local environment through tools, manage complex tasks, and maintain a more sophisticated memory, while preserving the existing, polished voice-to-voice user experience.

## 2. Core Architectural Vision

The new architecture is built around a central **`Agent`** class that orchestrates the entire process. For each user prompt, the `Agent` creates a **`Turn`** object, which manages the state of that specific exchange until a final answer is produced. This separation of concerns is critical for a robust agent.

### Architectural Diagram

```
+--------------------------+      +-------------------------+      +---------------------+
|   InteractiveSession     |      |      Agent (Agent)      |      |    ToolRegistry     |
|       (cli.py)           |      |     (Orchestrator)      |      | (tool_registry.py)  |
+--------------------------+      +-------------------------+      +---------------------+
           |                             | Creates                      |
           | 1. User Prompt              |                              |
           +---------------------------> |-->+----------------------+   |
                                         |   |   Turn (Turn)        |   |
                                         |   | (State for one op)   |   |
                                         |   +----------------------+   |
                                         |   | - Manages its own    |   |
                                         |   |   history snippet    |   |
                                         |   | - Executes API calls |   |
                                         |   | - Processes tool_calls |   |
                                         |   +----------------------+   |
                                         |             |              |
                                         | 2. API Call |              |
                                         +---------------------------> | OpenAI API
                                         |             |              |
                                         | 3. Response |              |
                                         <---------------------------+
                                         |             |
                                         | 4. Tool? -> | User Confirm
                                         |             |
                                         | 5. Execute  |--> Look up -->|
                                         |             |              |
                                         | 6. Loop...  |              |
                                         |             |              |
           | 7. Final Text Response      |             |              |
           <--------------------------- | <-----------+              |
           |                             |                              |
+--------------------------+             +------------------------------+
|   Text-to-Speech (TTS)   |
+--------------------------+
           ^
           | 8. Speak the final answer
           +
```

### Core Component Designs

#### A. Agent (Orchestrator)

- **Location:** `src/transcribe_talk/ai/agent.py`
- **Responsibilities:**
  - Initialize and manage core components: `PromptEngine`, `ChatService`, `Turn`, `ToolScheduler`, and `ConversationHistory`.
  - Capture and transcribe user voice input via `src/transcribe_talk/audio/recorder.py` and `src/transcribe_talk/ai/transcriber.py`.
  - Orchestrate the agentic loop:
    1. Assemble context via `PromptEngine`.
    2. Invoke `Turn` to stream LLM events from `ChatService`.
    3. Dispatch `ContentEvent`s to the CLI for text feedback and to TTS (via `src/transcribe_talk/ai/tts.py`) for audio playback.
    4. Collect `ToolCallRequestEvent`s and hand off to `ToolScheduler`.
    5. Append `FunctionResponseEvent` results to `ConversationHistory`.
    6. Repeat until a final `FinishedEvent` yields no further tool calls.
  - Enforce max-turn and max-tool-call safeguards.

#### B. PromptEngine (Context Assembler)

- **Location:** `src/transcribe_talk/ai/prompt_engine.py`
- **Responsibilities:**
  - Gather system prompt, long-term memory (`CONTEXT.md`), and environmental context (OS, working directory, file tree).
  - Produce a structured list of messages ready for `ChatService`.

#### C. ChatService (LLM Manager)

- **Location:** `src/transcribe_talk/ai/chat_service.py`
- **Responsibilities:**
  - Interact with the OpenAI chat completions API.
  - Support streaming responses, retry logic for transient errors, and telemetry (token usage, error rates).
  - Expose an async `send_stream(messages, functions_schema) -> AsyncIterator<RawChunk>`.

#### D. Turn (Event Generator)

- **Location:** `src/transcribe_talk/ai/turn.py`
- **Responsibilities:**
  - Use `ChatService` to send prompts and available `functions_schema` (from `ToolRegistry`).
  - Process streamed `RawChunk`s and yield high-level events:
    - `ContentEvent`: text segments for user display.
    - `ThoughtEvent`: model reasoning logs.
    - `ToolCallRequestEvent`: encapsulating tool name and arguments.
    - `FinishedEvent` / `ErrorEvent`.
  - **NOTE:** Does **not** execute tools.

#### E. ToolScheduler (Tool Execution Manager)

- **Location:** `src/transcribe_talk/ai/tool_scheduler.py`
- **Responsibilities:**
  - Validate and execute `ToolCallRequestEvent`s against `ToolRegistry`.
  - Handle interactive confirmations or auto-confirm (`--auto-confirm`).
  - Enforce per-tool timeouts and retry/abort policies.
  - Emit `FunctionResponseEvent`s containing tool execution results.

#### F. ToolRegistry (Tool Discovery)

- **Location:** `src/transcribe_talk/tools/tool_registry.py`
- **Responsibilities:**
  - Register and retrieve tool implementations by name.
  - Generate OpenAI `functions` schema dynamically from Python function signatures.

#### G. ConversationHistory (History Manager)

- **Location:** `src/transcribe_talk/ai/history.py`
- **Responsibilities:**
  - Maintain an ordered list of messages across system, user, assistant, and tool roles.
  - Format messages for `ChatService`, including injected function call results.
  - Support context summarization for token management and future chat compression.

## 3. Phased Development Plan

### Phase 1: Foundational Architecture (✅ COMPLETED)

_Goal: Scaffold the Agent/Turn architecture, clean up legacy AI modules, and prepare for tool integration._

1.  **✅ Clean up legacy code**: Moved existing `chat.py`, `transcriber.py`, and `tts.py` into a `src/transcribe_talk/ai/ai_legacy/` folder, while preserving `src/transcribe_talk/audio/recorder.py`, `src/transcribe_talk/audio/player.py`, and the TTS pipeline in `src/transcribe_talk/ai/tts.py` intact for voice I/O.
2.  **✅ Create `ToolRegistry`** in `src/transcribe_talk/tools/tool_registry.py`.
3.  **✅ Create `ConversationHistory`** in `src/transcribe_talk/ai/history.py`.
4.  **✅ Create `Turn` class** in `src/transcribe_talk/ai/turn.py`.
5.  **✅ Create `Agent` class** in `src/transcribe_talk/ai/agent.py`.
6.  **✅ Refactor `cli.py`** to call `Agent.execute_turn()` instead of legacy chat logic.
7.  **✅ Validate** no regressions against existing voice-to-voice flows.

### Phase 2: MVP Agentic Loop (✅ COMPLETED)

_First Tool (MVP):_ `list_directory` – enables the agent to list directory contents.

_Goal: Deliver a minimal, robust agentic loop with tool integration, safe defaults, and end-to-end testing._

1.  **✅ Define CLI scaffold**:
    - Added `--auto-confirm` (`--yes`) for unattended mode
    - Added `--dry-run` for simulation
2.  **✅ Implement `list_directory` tool**:
    - Created `src/transcribe_talk/tools/file_system.py` with `list_directory`
    - Registered in `ToolRegistry` and wired up in `cli.py`
3.  **✅ Implement core `Turn.run()` loop as `async def`**:
    - Supports both interactive (rich prompt) and unattended modes
    - Executes OpenAI function calls and handles responses
4.  **✅ Introduce safety guardrails**:
    - Enforced max tool-call depth (5) and per-turn call count
    - Per-tool timeout (30s) with retry or abort logic
5.  **✅ Add logging & telemetry**:
    - Instrumented each `Turn` with timestamps, token usage, and tool calls
    - Output logs to console and optionally to file
6.  **✅ Build unit & integration tests**:
    - Created test scripts for tool registration and execution
    - Verified end-to-end flow with dry-run mode
7.  **✅ Validate MVP end-to-end**:
    - Demonstrated `transcribe-talk --auto-confirm "What files are here?"` works correctly

### Phase 3: Expanding Capabilities (Pending)

_Goal: Make the agent more powerful and intelligent._

1.  **Add More Tools:** Implement `read_file` and `write_file` (with robust confirmation).
2.  **Implement Long-Term Memory:** Add support for `CONTEXT.md` to the `PromptEngine`.
3.  **Implement `save_memory` Tool:** Create a tool that allows the agent to write to `CONTEXT.md`.

### Phase 4: Advanced Hardening (Pending)

_Goal: Make the agent more robust and efficient, like `gemini-cli`._

1.  **Implement Loop Detection:** Create a simple service that tracks tool calls within a single `Turn`. If the same tool is called with the same arguments multiple times, break the loop and report an error.
2.  **(Stretch Goal) Implement Chat Compression:** For very long conversations, implement a mechanism in the `Agent` class to summarize the `ConversationHistory`, similar to `gemini-cli`'s `tryCompressChat`.

## Implementation Details

### Key Architectural Improvements Implemented

1. **Event-Driven Architecture**: The new Turn class yields structured events (ContentEvent, ToolCallRequestEvent, etc.) for better separation of concerns.

2. **Async/Await Support**: All core components support asynchronous operations for better performance and responsiveness.

3. **Type Safety**: Comprehensive type hints and Pydantic models for configuration validation.

4. **Modular Design**: Clear separation between:
   - Voice I/O (audio module)
   - AI Services (chat_service, prompt_engine, turn)
   - Tool Management (tool_registry, tool_scheduler)
   - Conversation State (history, agent)

### Current Project Structure

```
transcribe-talk/
├── src/transcribe_talk/
│   ├── ai/
│   │   ├── ai_legacy/        # Legacy AI modules (preserved)
│   │   │   ├── chat.py
│   │   │   └── transcriber.py
│   │   ├── agent.py          # New Agent orchestrator
│   │   ├── chat_service.py   # New ChatService for OpenAI API
│   │   ├── events.py         # Event definitions
│   │   ├── history.py        # ConversationHistory manager
│   │   ├── prompt_engine.py  # PromptEngine for context assembly
│   │   ├── tool_scheduler.py # ToolScheduler for tool execution
│   │   ├── transcriber.py    # Refactored Whisper transcriber
│   │   ├── tts.py           # Preserved ElevenLabs TTS
│   │   └── turn.py          # Turn event generator
│   ├── audio/               # Audio I/O (preserved)
│   │   ├── player.py
│   │   └── recorder.py
│   ├── tools/               # Tool infrastructure
│   │   └── tool_registry.py
│   ├── config/              # Configuration management
│   │   └── settings.py
│   ├── utils/               # Utilities
│   │   └── helpers.py
│   └── cli.py              # Refactored CLI with Agent integration
```

### Migration Notes

1. **Backward Compatibility**: The existing voice-to-voice functionality is fully preserved while adding the new agentic capabilities.

2. **Legacy Code**: Original AI modules are preserved in `ai_legacy/` for reference and potential rollback.

3. **Configuration**: The existing configuration system (Settings) is extended to support new agent-related settings.

4. **Testing**: The project maintains executable state throughout the migration with no breaking changes to existing functionality.

## Next Steps

1. Continue with Phase 2 implementation for the MVP agentic loop
2. Add comprehensive unit and integration tests
3. Implement the first tool (`list_directory`) and validate end-to-end
4. Add documentation for the new architecture and API
