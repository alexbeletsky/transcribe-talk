"""
TranscribeTalk CLI - Main entry point.

This module provides the command-line interface for TranscribeTalk,
handling argument parsing, logging setup, and error handling.
"""

import logging
import sys
from functools import wraps
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.logging import RichHandler

from .config.settings import get_settings, Settings

# Rich console for beautiful output
console = Console()


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Set up logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
    """
    # Configure logging format
    log_format = "%(message)s"
    date_format = "%H:%M:%S"
    
    # Set up rich handler for console output
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    rich_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[rich_handler],
    )
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        logging.getLogger().addHandler(file_handler)


def handle_exceptions(func):
    """Decorator to handle exceptions gracefully."""
    @wraps(func)
    def _exception_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user.[/yellow]")
            sys.exit(1)
        except Exception as e:
            console.print(f"\n[red]Error: {str(e)}[/red]")
            if console.is_terminal:
                console.print("\n[dim]For help, run: transcribe-talk --help[/dim]")
            sys.exit(1)
    return _exception_wrapper


@click.group()
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
@click.pass_context
def cli(ctx: click.Context, log_level: str, log_file: Optional[str], debug: bool) -> None:
    """
    TranscribeTalk - Voice-to-Voice AI Conversations
    
    A CLI application for voice-to-voice AI conversations using speech-to-text,
    AI processing, and text-to-speech.
    
    Examples:
        transcribe-talk                    # Interactive mode
        transcribe-talk --once            # One-shot mode
        transcribe-talk config            # Configuration management
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Set up logging
    setup_logging(log_level, log_file)
    
    # Load settings (will be loaded when needed)
    ctx.obj['settings'] = None
    logging.info("CLI initialized successfully")
    
    # Set debug mode
    if debug:
        ctx.obj['settings'].debug = True
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Debug mode enabled")


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
@click.option(
    "--output",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format for one-shot mode"
)
@click.pass_context
@handle_exceptions
def interactive(ctx: click.Context, model: str, voice: Optional[str], tokens: int, output: str) -> None:
    """
    Start interactive voice conversation mode.
    
    This is the default mode that allows you to have a continuous
    voice conversation with the AI assistant.
    """
    console.print("[bold blue]TranscribeTalk Interactive Mode[/bold blue]")
    console.print("[dim]Press Ctrl+C to exit[/dim]\n")
    
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
    
    # TODO: Implement interactive mode in Phase 2
    console.print("[yellow]Interactive mode will be implemented in Phase 2[/yellow]")
    console.print("[dim]This will include audio recording, transcription, AI processing, and TTS playback.[/dim]")


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
@click.pass_context
@handle_exceptions
def once(ctx: click.Context, input: Optional[str], output: Optional[str], format: str) -> None:
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
    
    if input:
        console.print(f"[green]✓[/green] Input file: {input}")
    else:
        console.print("[yellow]No input file specified - will record from microphone[/yellow]")
    
    if output:
        console.print(f"[green]✓[/green] Output file: {output}")
    
    console.print(f"[green]✓[/green] Output format: {format}")
    console.print()
    
    # TODO: Implement one-shot mode in Phase 2
    console.print("[yellow]One-shot mode will be implemented in Phase 2[/yellow]")
    console.print("[dim]This will include audio processing and result output.[/dim]")


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