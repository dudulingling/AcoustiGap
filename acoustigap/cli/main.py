"""
AcoustiGap - Command Line Interface
Provides full command-line tools for transmitting, receiving, inspecting audio devices,
measuring noise floor, and running diagnostics.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from ..core.dsp import DspEngine, ProtocolId
from ..hardware.audio_stream import AudioReceiverStream, play_audio_samples
from ..hardware.devices import (
    get_default_input_device,
    get_default_output_device,
    list_input_devices,
    list_output_devices,
)
from ..hardware.noise_meter import measure_noise_floor
from ..protocol.chunker import FileChunker
from ..protocol.session import TransferSessionReceiver, TransferSessionSender

console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose debug logging.")
def cli(ctx: click.Context, verbose: bool):
    """AcoustiGap: Secure Acoustic Air-Gap Data Transmission System."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    if ctx.invoked_subcommand is None:
        from ..gui.app import launch_gui
        launch_gui()


@cli.command()
def devices():
    """List all audio input (microphones) and output (speakers) devices."""
    table_in = Table(title="🎙️ Input Devices (Microphones)", title_style="bold cyan")
    table_in.add_column("Index", justify="right", style="cyan", no_wrap=True)
    table_in.add_column("Name", style="white")
    table_in.add_column("API", style="magenta")
    table_in.add_column("Channels", justify="center", style="green")
    table_in.add_column("Sample Rate", justify="right", style="yellow")

    default_in = get_default_input_device()
    for d in list_input_devices():
        is_def = "⭐ " if (default_in and d.index == default_in.index) else ""
        table_in.add_row(
            f"{is_def}{d.index}",
            d.name,
            d.hostapi_name,
            str(d.max_input_channels),
            f"{int(d.default_samplerate)} Hz",
        )

    table_out = Table(title="🔊 Output Devices (Speakers)", title_style="bold green")
    table_out.add_column("Index", justify="right", style="cyan", no_wrap=True)
    table_out.add_column("Name", style="white")
    table_out.add_column("API", style="magenta")
    table_out.add_column("Channels", justify="center", style="green")
    table_out.add_column("Sample Rate", justify="right", style="yellow")

    default_out = get_default_output_device()
    for d in list_output_devices():
        is_def = "⭐ " if (default_out and d.index == default_out.index) else ""
        table_out.add_row(
            f"{is_def}{d.index}",
            d.name,
            d.hostapi_name,
            str(d.max_output_channels),
            f"{int(d.default_samplerate)} Hz",
        )

    console.print(table_in)
    console.print()
    console.print(table_out)


@cli.command()
@click.option("--device", "-d", type=int, default=None, help="Input device index.")
@click.option("--duration", "-t", type=float, default=2.0, help="Measurement duration in seconds.")
def noise_floor(device: Optional[int], duration: float):
    """Measure ambient background noise level and frequency spectrum."""
    with console.status(f"[bold yellow]Sampling ambient noise for {duration}s..."):
        prof = measure_noise_floor(device_index=device, duration_seconds=duration)

    console.print(Panel(prof.summary(), title="[bold cyan]Noise Floor Assessment[/bold cyan]", border_style="cyan"))


@cli.command()
@click.argument("text")
@click.option("--protocol", "-p", type=click.Choice([e.name for e in ProtocolId]), default="FAST")
@click.option("--volume", "-vol", type=int, default=50, help="Volume percentage (0-100).")
@click.option("--device", "-d", type=int, default=None, help="Output speaker index.")
def send_text(text: str, protocol: str, volume: int, device: Optional[int]):
    """Transmit a single text string via acoustic modulation."""
    proto_enum = ProtocolId[protocol]
    console.print(f"[bold cyan]Modulating text:[/bold cyan] '{text}' via protocol [bold green]{protocol}[/bold green]...")
    with DspEngine() as dsp:
        samples = dsp.encode(text, protocol=proto_enum, volume=volume)
        duration_s = len(samples) / dsp.sample_rate
        console.print(f"[bold yellow]Broadcasting {duration_s:.2f}s acoustic waveform...[/bold yellow]")
        play_audio_samples(samples, device_index=device, sample_rate=dsp.sample_rate, blocking=True)
    console.print("[bold green]✔ Transmission finished.[/bold green]")


@cli.command()
@click.option("--device", "-d", type=int, default=None, help="Input microphone index.")
def listen_text(device: Optional[int]):
    """Listen continuously on microphone and print received text in real time."""
    console.print(Panel("Listening on microphone for acoustic transmissions... Press Ctrl+C to stop.", style="bold cyan"))
    dsp = DspEngine()
    stream = AudioReceiverStream(device_index=device)

    try:
        stream.start()
        while True:
            chunk = stream.read_chunk(timeout=0.1)
            if chunk is not None:
                decoded = dsp.decode_samples(chunk)
                if decoded:
                    console.print(f"[bold green]▶ Decoded:[/bold green] [bold white]{decoded}[/bold white]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping listener...[/yellow]")
    finally:
        stream.stop()
        dsp.close()


@cli.command()
@click.argument("filepath", type=click.Path(exists=True))
@click.option("--protocol", "-p", type=click.Choice([e.name for e in ProtocolId]), default="FAST")
@click.option("--volume", "-vol", type=int, default=50, help="Volume percentage (0-100).")
@click.option("--chunk-size", "-c", type=int, default=48, help="Bytes per packet payload.")
@click.option("--device", "-d", type=int, default=None, help="Output speaker index.")
def send_file(filepath: str, protocol: str, volume: int, chunk_size: int, device: Optional[int]):
    """Transmit a complete file over acoustic air-gap with chunking and CRC32."""
    proto_enum = ProtocolId[protocol]
    filename = os.path.basename(filepath)

    with open(filepath, "rb") as f:
        file_bytes = f.read()

    console.print(f"[bold cyan]Preparing file:[/bold cyan] {filename} ({len(file_bytes)} bytes)")
    chunked = FileChunker.chunk_data(
        file_bytes,
        filename=filename,
        chunk_size=chunk_size,
        compress=True,
    )
    total_packets = len(chunked.packets)
    console.print(f"Compressed: [bold green]{chunked.metadata.compressed}[/bold green], Total packets: [bold yellow]{total_packets}[/bold yellow]")

    dsp = DspEngine()
    sender = TransferSessionSender(dsp, protocol=proto_enum, volume=volume)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"Sending {filename}...", total=total_packets)

        def on_progress(current, total):
            progress.update(task, completed=current)

        sender.send_chunked_file(chunked, output_device_index=device, progress_callback=on_progress)

    console.print(f"[bold green]✔ File '{filename}' successfully transmitted over air-gap![/bold green]")


@cli.command()
@click.option("--output-dir", "-o", default="./received_files", help="Directory to save received file.")
@click.option("--device", "-d", type=int, default=None, help="Input microphone index.")
def receive_file(output_dir: str, device: Optional[int]):
    """Listen on microphone, receive chunks, verify CRC32/SHA-256, and save file."""
    os.makedirs(output_dir, exist_ok=True)
    console.print(Panel(f"Waiting for incoming file transmission... Target dir: '{output_dir}'. Press Ctrl+C to cancel.", style="bold cyan"))

    dsp = DspEngine()
    stream = AudioReceiverStream(device_index=device)
    receiver = TransferSessionReceiver()

    try:
        stream.start()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("Awaiting Start Packet...", total=100)

            while not receiver.is_complete:
                chunk = stream.read_chunk(timeout=0.1)
                if chunk is not None:
                    decoded = dsp.decode_samples(chunk)
                    if decoded is not None and isinstance(decoded, (bytes, bytearray)):
                        pkt = receiver.feed_packet_data(decoded)
                        if pkt:
                            desc = f"Receiving: {receiver.metadata.filename if receiver.metadata else 'Unknown'} ({len(receiver.received_chunks)}/{receiver.metadata.total_chunks if receiver.metadata else '?'})"
                            progress.update(task, description=desc, completed=receiver.progress_percent)

        # Finished and verified!
        out_path = os.path.join(output_dir, receiver.metadata.filename)
        with open(out_path, "wb") as f:
            f.write(receiver.assembled_data)

        console.print(f"[bold green]✔ File received & verified: {out_path} ({len(receiver.assembled_data)} bytes, SHA-256 MATCH!)[/bold green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Aborted file reception.[/yellow]")
    finally:
        stream.stop()
        dsp.close()


@cli.command()
def test_loopback():
    """Run automated DSP loopback benchmark across multiple protocols."""
    console.print(Panel("Running Automated Acoustic Loopback Benchmark", style="bold cyan"))
    protocols = [
        ProtocolId.NORMAL,
        ProtocolId.FAST,
        ProtocolId.FASTEST,
        ProtocolId.ULTRASOUND_FAST,
    ]
    test_payload = b"AcoustiGap Air-Gap DSP Benchmark 2026! 1234567890"

    table = Table(title="DSP Loopback Benchmark Results", title_style="bold green")
    table.add_column("Protocol", style="cyan")
    table.add_column("Modulated Samples", justify="right", style="yellow")
    table.add_column("Air Duration", justify="right", style="magenta")
    table.add_column("Effective Rate", justify="right", style="green")
    table.add_column("Status", justify="center", style="bold white")

    dsp = DspEngine()
    for proto in protocols:
        start_t = time.perf_counter()
        waveform = dsp.encode(test_payload, protocol=proto, volume=50)
        decoded = dsp.decode_samples(waveform)
        air_duration = len(waveform) / dsp.sample_rate
        byte_rate = len(test_payload) / air_duration
        is_ok = (decoded == test_payload)

        status_text = "[green]PASS[/green]" if is_ok else "[red]FAIL[/red]"
        table.add_row(
            proto.name,
            f"{len(waveform):,}",
            f"{air_duration:.2f} s",
            f"{byte_rate:.1f} B/s",
            status_text,
        )

    console.print(table)


@cli.command()
def gui():
    """Launch the modern AcoustiGap Desktop GUI with Waterfall Spectrogram."""
    from ..gui.app import launch_gui
    launch_gui()


if __name__ == "__main__":
    cli()

