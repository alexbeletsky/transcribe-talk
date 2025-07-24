"""
TranscribeTalk CLI - Main entry point.

This module provides the command-line interface for TranscribeTalk,
handling argument parsing, logging setup, and error handling.
"""

import logging
import signal
import sys
import threading
import time
import warnings
from functools import wraps
from pathlib import Path
from typing import Optional
import asyncio

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.text import Text

from .audio.player import AudioPlayer
from .audio.recorder import AudioRecorder
from .ai.agent import Agent, AgentConfig
from .ai.transcriber import WhisperTranscriber
from .ai.tts import ElevenLabsTTS
from .ai.events import EventType, ContentEvent, ErrorEvent, FunctionResponseEvent
from .tools import get_global_registry
from .config.settings import get_settings, Settings
from .utils.helpers import format_duration, truncate_text

# Rich console for beautiful output
console = Console()


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Set up logging configuration and suppress common warnings.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
    """
    # Suppress common warnings that don't affect functionality
    warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")
    warnings.filterwarnings("ignore", category=UserWarning, module="whisper")
    warnings.filterwarnings("ignore", message=".*torch.load.*")
    warnings.filterwarnings("ignore", category=FutureWarning, module="torch")
    
    # Configure logging format for better readability
    log_format = "%(asctime)s %(levelname)s %(message)s"
    date_format = "%H:%M:%S"
    
    # Set up rich handler for console output with improved formatting
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
        show_level=True,
    )
    
    # Custom formatter for cleaner output
    class CleanFormatter(logging.Formatter):
        def format(self, record):
            # Remove module name from log messages for cleaner output
            if hasattr(record, 'name') and record.name != 'root':
                record.msg = f"[dim]{record.name}[/dim] {record.msg}"
            return super().format(record)
    
    rich_handler.setFormatter(CleanFormatter(log_format, date_format))
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[rich_handler],
    )
    
    # Add file handler if specified with full details
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        logging.getLogger().addHandler(file_handler)
    
    # Set specific logger levels for better control
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def handle_exceptions(func):
    """Decorator to handle exceptions gracefully."""
    @wraps(func)
    def _exception_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                console.print_exception()
            sys.exit(1)
    return _exception_wrapper


class InteractiveSession:
    """Manages an interactive voice conversation session."""
    
    def __init__(self, settings: Settings):
        """Initialize the interactive session with all components."""
        self.settings = settings
        self.running = False
        
        # Initialize components
        self.recorder = AudioRecorder(settings.audio)
        self.player = AudioPlayer(settings.audio)
        self.transcriber = WhisperTranscriber(settings.whisper, settings.audio)
        self.tts = ElevenLabsTTS(settings.elevenlabs)
        
        # Initialize Agent with tool registry
        agent_config = AgentConfig(
            max_turns=20,
            max_tool_calls_per_turn=5,
            auto_confirm=False,
            debug=False
        )
        self.agent = Agent(
            settings=settings,
            tool_registry=get_global_registry(),
            config=agent_config
        )
        
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        
        console.print("[green]✓[/green] All components initialized successfully")
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signal."""
        self.running = False
        console.print("\n[yellow]Stopping conversation...[/yellow]")
    
    def start(self):
        """Start the interactive conversation session."""
        self.running = True
        
        # Welcome message
        welcome_panel = Panel.fit(
            "[bold blue]Welcome to TranscribeTalk![/bold blue]\n\n"
            "[white]Press [bold]ENTER[/bold] to start/stop recording.\n"
            "Press [bold]Ctrl+C[/bold] to exit.\n"
            "Type 'help' for more commands.[/white]",
            title="Interactive Mode",
            border_style="blue"
        )
        console.print(welcome_panel)
        
        conversation_count = 0
        self.agent.start_conversation()
        
        try:
            while self.running:
                conversation_count += 1
                console.print(f"\n[dim]--- Turn {conversation_count} ---[/dim]")
                
                # Get user input method choice
                choice = self._get_input_choice()
                
                if choice == "voice":
                    user_text = self._record_and_transcribe()
                elif choice == "text":
                    user_text = self._get_text_input()
                elif choice == "quit":
                    break
                elif choice == "help":
                    self._show_help()
                    continue
                elif choice == "clear":
                    self.agent.start_conversation()  # Reset conversation
                    console.print("[green]✓[/green] Conversation history cleared")
                    conversation_count = 0
                    continue
                else:
                    continue
                
                if not user_text or not user_text.strip():
                    console.print("[yellow]No input received. Try again.[/yellow]")
                    continue
                
                # Process with Agent
                self._process_with_agent(user_text)
                    
        except Exception as e:
            console.print(f"[red]Session error: {e}[/red]")
        finally:
            self._cleanup()
    
    def _get_input_choice(self) -> str:
        """Get user's choice for input method."""
        console.print("\n[cyan]🎯 Choose input method:[/cyan]")
        console.print("  [bold]v[/bold] - 🎤 Voice recording")
        console.print("  [bold]t[/bold] - ✏️  Text input") 
        console.print("  [bold]h[/bold] - ❓ Help")
        console.print("  [bold]c[/bold] - 🗑️  Clear conversation")
        console.print("  [bold]q[/bold] - 🚪 Quit")
        
        choice = console.input("\n[cyan]Your choice[/cyan] [dim](v/t/h/c/q)[/dim]: ").strip().lower()
        
        choice_map = {
            "v": "voice", "voice": "voice",
            "t": "text", "text": "text",
            "h": "help", "help": "help",
            "c": "clear", "clear": "clear",
            "q": "quit", "quit": "quit", "exit": "quit"
        }
        
        return choice_map.get(choice, "unknown")
    
    def _record_and_transcribe(self) -> Optional[str]:
        """Record audio and transcribe to text."""
        try:
            console.print("[green]🔴 Recording... Press Enter to stop[/green]")
            
            # Start recording in background
            self.recorder.start_recording()
            
            # Wait for user to stop with styled prompt
            console.input("[dim]⏹️  Stop recording[/dim]")
            
            # Stop recording and get audio data
            audio_data = self.recorder.stop_recording()
            
            if len(audio_data) == 0:
                console.print("[yellow]No audio recorded.[/yellow]")
                return None
            
            duration = len(audio_data) / self.settings.audio.sample_rate
            console.print(f"[green]✓[/green] Recorded {format_duration(duration)} of audio")
            
            # Transcribe audio - replace spinner with simple message
            console.print("[cyan]🔄 Transcribing audio...[/cyan]")
            result = self.transcriber.transcribe_array(audio_data)
            console.print("[green]✓[/green] Transcription completed")
            
            user_text = result["text"].strip()
            if not user_text:
                console.print("[yellow]No speech detected in recording.[/yellow]")
                return None
            
            console.print(f"[blue]You said:[/blue] {user_text}")
            return user_text
            
        except Exception as e:
            console.print(f"[red]Recording error: {e}[/red]")
            return None
    
    def _get_text_input(self) -> Optional[str]:
        """Get text input from user."""
        text = console.input("\n[cyan]Enter your message:[/cyan] ").strip()
        return text if text else None
    
    def _process_with_agent(self, user_text: str) -> None:
        """Process user input with the Agent and handle the response."""
        try:
            console.print("\n[cyan]🤖 Processing...[/cyan]")
            
            # Run agent turn asynchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            accumulated_response = ""
            
            async def process_turn():
                nonlocal accumulated_response
                
                async for event in self.agent.execute_turn(user_text):
                    if event.type == EventType.CONTENT:
                        # Print content as it streams
                        console.print(event.content, end="")
                        accumulated_response += event.content
                    
                    elif event.type == EventType.ERROR:
                        console.print(f"\n[red]Error: {event.error_message}[/red]")
                        if not event.recoverable:
                            return
                    
                    elif event.type == EventType.FUNCTION_RESPONSE:
                        # Show tool execution results
                        if event.success:
                            console.print(f"\n[green]Tool executed successfully[/green]")
                        else:
                            console.print(f"\n[red]Tool error: {event.error_message}[/red]")
                    
                    elif event.type == EventType.DEBUG and self.agent.config.debug:
                        console.print(f"\n[dim]Debug: {event.message}[/dim]")
            
            try:
                loop.run_until_complete(process_turn())
            finally:
                loop.close()
            
            # Print newline after streaming content
            if accumulated_response:
                console.print()  # New line after response
                
                # Synthesize and play the response
                self._synthesize_and_play(accumulated_response)
            
        except Exception as e:
            console.print(f"[red]Processing error: {e}[/red]")
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                console.print_exception()
    
    def _synthesize_and_play(self, text: str) -> None:
        """Synthesize text to speech and play it."""
        try:
            console.print("[cyan]🔊 Speaking...[/cyan]")
            
            # Synthesize speech
            audio_data = self.tts.synthesize(text)
            
            if audio_data:
                # Play the audio
                self.player.play(audio_data)
                console.print("[green]✓[/green] Response played")
            else:
                console.print("[yellow]No audio generated[/yellow]")
                
        except Exception as e:
            console.print(f"[red]TTS error: {e}[/red]")
    
    def _show_help(self) -> None:
        """Show help information."""
        help_text = """
[bold cyan]TranscribeTalk Help[/bold cyan]

[bold]Commands:[/bold]
  v/voice  - Record voice input
  t/text   - Type text input
  c/clear  - Clear conversation history
  h/help   - Show this help
  q/quit   - Exit the application

[bold]Features:[/bold]
  • Voice-to-voice AI conversations
  • Tool-augmented responses (when available)
  • Real-time transcription
  • Natural text-to-speech

[bold]Tips:[/bold]
  • Speak clearly when recording
  • Keep responses concise for better TTS
  • Use 'clear' to start fresh conversations
"""
        console.print(Panel(help_text, title="Help", border_style="cyan"))
    
    def _cleanup(self) -> None:
        """Clean up resources."""
        try:
            # End conversation and show summary
            summary = self.agent.end_conversation()
            
            console.print("\n[bold]Session Summary:[/bold]")
            console.print(f"  Turns: {summary['turn_count']}")
            console.print(f"  Total tokens: {summary['chat_telemetry']['total_tokens_used']}")
            console.print(f"  Estimated cost: ${summary['chat_telemetry']['total_cost']}")
            
            if 'tool_summary' in summary and summary['tool_summary']['total_calls'] > 0:
                console.print(f"  Tool calls: {summary['tool_summary']['total_calls']}")
            
            console.print("\n[green]Session ended successfully[/green]")
            
        except Exception as e:
            console.print(f"[yellow]Cleanup warning: {e}[/yellow]")


# Make interactive mode available as both a command and the default
def start_interactive_mode(ctx: click.Context, model: str, voice: Optional[str], tokens: int) -> None:
    """Start interactive voice conversation mode."""
    console.print("[bold blue]TranscribeTalk Interactive Mode[/bold blue]")
    console.print("[dim]Loading components...[/dim]\n")
    
    # Load settings
    try:
        settings = get_settings()
        ctx.obj['settings'] = settings
    except Exception as e:
        console.print(f"[red]Configuration error: {str(e)}[/red]")
        console.print("\n[dim]Please check your .env file or environment variables.[/dim]")
        sys.exit(1)
    
    # Update settings with command line options
    settings.whisper.model = model
    if voice:
        settings.elevenlabs.voice_id = voice
    settings.openai.max_tokens = tokens
    
    console.print(f"[green]✓[/green] Using Whisper model: {model}")
    console.print(f"[green]✓[/green] Using TTS voice: {settings.elevenlabs.voice_id}")
    console.print(f"[green]✓[/green] Max tokens: {tokens}")
    console.print()
    
    # Start interactive session
    session = InteractiveSession(settings)
    session.start()


@click.group(invoke_without_command=True)
@click.version_option(version="0.1.0", prog_name="transcribe-talk")
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    help="Set logging level"
)
@click.option(
    "--log-file",
    type=click.Path(),
    help="Log file path"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug mode"
)
@click.option(
    "--model",
    default="base",
    type=click.Choice(["tiny", "base", "small", "medium", "large"]),
    help="Whisper model to use for transcription"
)
@click.option(
    "--voice",
    help="ElevenLabs voice ID for TTS"
)
@click.option(
    "--tokens",
    default=200,
    type=int,
    help="Maximum tokens in AI response"
)
@click.pass_context
@handle_exceptions
def cli(ctx: click.Context, log_level: str, log_file: Optional[str], debug: bool, 
        model: str, voice: Optional[str], tokens: int) -> None:
    """
    TranscribeTalk - Voice-to-Voice AI Conversations
    
    A CLI application for voice-to-voice AI conversations using speech-to-text,
    AI processing, and text-to-speech.
    
    Examples:
        transcribe-talk                    # Interactive mode (default)
        transcribe-talk once              # One-shot mode
        transcribe-talk config            # Configuration management
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Set up logging and warning suppression
    setup_logging(log_level, log_file)
    
    # Load settings (will be loaded when needed)
    ctx.obj['settings'] = None
    logging.info("CLI initialized successfully")
    
    # Set debug mode
    if debug:
        ctx.obj['debug'] = True
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Debug mode enabled")
    
    # If no command is specified, run interactive mode
    if ctx.invoked_subcommand is None:
        start_interactive_mode(ctx, model, voice, tokens)


@cli.command()
@click.option(
    "--model",
    default="base",
    type=click.Choice(["tiny", "base", "small", "medium", "large"]),
    help="Whisper model to use for transcription"
)
@click.option(
    "--voice",
    help="ElevenLabs voice ID for TTS"
)
@click.option(
    "--tokens",
    default=200,
    type=int,
    help="Maximum tokens in AI response"
)
@click.pass_context
@handle_exceptions
def interactive(ctx: click.Context, model: str, voice: Optional[str], tokens: int) -> None:
    """
    Start interactive voice conversation mode.
    
    This allows you to have a continuous voice conversation with the AI assistant.
    """
    start_interactive_mode(ctx, model, voice, tokens)


@cli.command()
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True),
    help="Input audio file path"
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path"
)
@click.option(
    "--format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format"
)
@click.option(
    "--no-tts",
    is_flag=True,
    help="Skip text-to-speech synthesis"
)
@click.pass_context
@handle_exceptions
def once(ctx: click.Context, input: Optional[str], output: Optional[str], format: str, no_tts: bool) -> None:
    """
    Process a single audio file or recording.
    
    This mode processes one audio input and outputs the result.
    Useful for automation and batch processing.
    """
    console.print("[bold blue]TranscribeTalk One-Shot Mode[/bold blue]\n")
    
    # Load settings
    try:
        settings = get_settings()
        ctx.obj['settings'] = settings
    except Exception as e:
        console.print(f"[red]Configuration error: {str(e)}[/red]")
        console.print("\n[dim]Please check your .env file or environment variables.[/dim]")
        sys.exit(1)
    
    # Initialize components
    recorder = AudioRecorder(settings.audio)
    transcriber = WhisperTranscriber(settings.whisper, settings.audio)
    tts = ElevenLabsTTS(settings.elevenlabs)
    player = AudioPlayer(settings.audio)
    
    # Initialize Agent for one-shot processing
    agent_config = AgentConfig(
        max_turns=1,
        max_tool_calls_per_turn=5,
        auto_confirm=True,  # Auto-confirm for non-interactive mode
        debug=False
    )
    agent = Agent(
        settings=settings,
        tool_registry=get_global_registry(),
        config=agent_config
    )
    
    try:
        # Get audio data
        if input:
            console.print(f"[green]✓[/green] Input file: {input}")
            console.print("[cyan]🔄 Processing audio file...[/cyan]")
            result = transcriber.transcribe_file(input)
            console.print("[green]✓[/green] Audio file processed")
            audio_data = None
        else:
            console.print("[yellow]Recording from microphone...[/yellow]")
            console.print("Press ENTER to start recording...")
            input()
            
            console.print("[green]🔴 Recording... Press ENTER to stop[/green]")
            recorder.start_recording()
            input()
            
            audio_data = recorder.stop_recording()
            duration = len(audio_data) / settings.audio.sample_rate
            console.print(f"[green]✓[/green] Recorded {format_duration(duration)} of audio")
            
            console.print("[cyan]🔄 Transcribing audio...[/cyan]")
            result = transcriber.transcribe_array(audio_data)
            console.print("[green]✓[/green] Transcription completed")
        
        user_text = result["text"].strip()
        if not user_text:
            console.print("[yellow]No speech detected.[/yellow]")
            return
        
        console.print(f"[blue]Transcribed:[/blue] {user_text}")
        
        # Process with AI
        console.print("[cyan]🤔 Processing with AI...[/cyan]")
        
        # Start conversation and execute turn
        agent.start_conversation()
        
        # Run agent turn and collect response
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        ai_response = ""
        
        async def process_once():
            nonlocal ai_response
            async for event in agent.execute_turn(user_text):
                if event.type == EventType.CONTENT:
                    ai_response += event.content
                elif event.type == EventType.ERROR:
                    console.print(f"[red]Error: {event.error_message}[/red]")
                    if not event.recoverable:
                        raise Exception(event.error_message)
        
        try:
            loop.run_until_complete(process_once())
        finally:
            loop.close()
        
        console.print("[green]✓[/green] AI response generated")
        
        console.print(f"[magenta]AI Response:[/magenta] {ai_response}")
        
        # Output result
        if output:
            output_path = Path(output)
            if format == "json":
                import json
                result_data = {
                    "transcription": user_text,
                    "ai_response": ai_response,
                    "metadata": {
                        "whisper_model": settings.whisper.model,
                        "openai_model": settings.openai.model,
                        "language": result.get("language", "unknown")
                    }
                }
                output_path.write_text(json.dumps(result_data, indent=2))
            else:
                output_path.write_text(f"User: {user_text}\n\nAI: {ai_response}\n")
            
            console.print(f"[green]✓[/green] Result saved to: {output}")
        
        # Text-to-speech (unless disabled)
        if not no_tts:
            console.print("[cyan]🎵 Generating speech...[/cyan]")
            audio_bytes = tts.synthesize(ai_response)
            console.print("[green]✓[/green] Speech generated")
            
            console.print("[green]🔊 Playing AI response...[/green]")
            player.play(audio_bytes)
        
    except Exception as e:
        console.print(f"[red]Error in one-shot mode: {e}[/red]")
    finally:
        if recorder:
            recorder.cleanup()


@cli.group()
def config() -> None:
    """Manage TranscribeTalk configuration."""
    pass


@config.command()
@click.pass_context
def show(ctx: click.Context) -> None:
    """Show current configuration."""
    # Load settings
    try:
        settings = get_settings()
        ctx.obj['settings'] = settings
    except Exception as e:
        console.print(f"[red]Configuration error: {str(e)}[/red]")
        console.print("\n[dim]Please check your .env file or environment variables.[/dim]")
        sys.exit(1)
    
    console.print("[bold blue]TranscribeTalk Configuration[/bold blue]\n")
    
    # Audio settings
    console.print("[bold]Audio Settings:[/bold]")
    console.print(f"  Sample Rate: {settings.audio.sample_rate} Hz")
    console.print(f"  Channels: {settings.audio.channels}")
    console.print(f"  Frame Size: {settings.audio.frame_ms} ms")
    console.print()
    
    # Whisper settings
    console.print("[bold]Whisper Settings:[/bold]")
    console.print(f"  Model: {settings.whisper.model}")
    console.print()
    
    # OpenAI settings
    console.print("[bold]OpenAI Settings:[/bold]")
    console.print(f"  Model: {settings.openai.model}")
    console.print(f"  Max Tokens: {settings.openai.max_tokens}")
    console.print(f"  Temperature: {settings.openai.temperature}")
    console.print(f"  API Key: {'✓' if settings.openai.api_key else '✗'}")
    console.print()
    
    # ElevenLabs settings
    console.print("[bold]ElevenLabs Settings:[/bold]")
    console.print(f"  Voice ID: {settings.elevenlabs.voice_id}")
    console.print(f"  Model ID: {settings.elevenlabs.model_id}")
    console.print(f"  Output Format: {settings.elevenlabs.output_format}")
    console.print(f"  API Key: {'✓' if settings.elevenlabs.api_key else '✗'}")
    console.print()
    
    # Logging settings
    console.print("[bold]Logging Settings:[/bold]")
    console.print(f"  Level: {settings.logging.level}")
    console.print(f"  File: {settings.logging.file or 'Console only'}")
    console.print()


@config.command()
@click.pass_context
def validate(ctx: click.Context) -> None:
    """Validate current configuration."""
    # Load settings
    try:
        settings = get_settings()
        ctx.obj['settings'] = settings
    except Exception as e:
        console.print(f"[red]Configuration error: {str(e)}[/red]")
        console.print("\n[dim]Please check your .env file or environment variables.[/dim]")
        sys.exit(1)
    
    console.print("[bold blue]Validating Configuration[/bold blue]\n")
    
    errors = []
    warnings = []
    
    # Check API keys
    if not settings.openai.api_key or settings.openai.api_key == "your_openai_api_key_here":
        errors.append("OpenAI API key is not configured")
    elif not settings.openai.api_key.startswith("sk-"):
        errors.append("OpenAI API key format is invalid")
    
    if not settings.elevenlabs.api_key or settings.elevenlabs.api_key == "your_elevenlabs_api_key_here":
        errors.append("ElevenLabs API key is not configured")
    elif not settings.elevenlabs.api_key.startswith("sk_"):
        errors.append("ElevenLabs API key format is invalid")
    
    # Check .env file
    env_file = Path('.env')
    if not env_file.exists():
        warnings.append(".env file not found - using environment variables")
    
    # Display results
    if errors:
        console.print("[red]❌ Configuration Errors:[/red]")
        for error in errors:
            console.print(f"  • {error}")
        console.print()
    
    if warnings:
        console.print("[yellow]⚠️  Configuration Warnings:[/yellow]")
        for warning in warnings:
            console.print(f"  • {warning}")
        console.print()
    
    if not errors and not warnings:
        console.print("[green]✅ Configuration is valid![/green]")
    elif not errors:
        console.print("[green]✅ Configuration is valid (with warnings)[/green]")
    else:
        console.print("[red]❌ Configuration has errors[/red]")
        sys.exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main() 