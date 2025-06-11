#!/usr/bin/env python3
# pyright: reportAny=false
"""
Model management utility for GGUF, MLX, LMStudio, and Ollama models.
Handles downloading, importing, configuration, and serving of AI models.
"""

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

import requests


@dataclass
class ModelConfig:
    """Configuration for a model from CSV."""

    name: str
    draft: str = ""
    context: str = ""
    temp: str = ""
    topk: str = ""
    topp: str = ""
    aliases: str = ""
    args: str = ""


class ModelManager:
    """Manages AI/ML models across different platforms."""

    server: str
    home: Path

    # Define model directories
    xdg_local: Path
    gguf_models: Path
    mlx_models: Path
    lmstudio_models: Path
    ollama_models: Path

    def __init__(self):
        """Initialize paths and configuration."""
        self.server = "192.168.50.5"
        self.home = Path.home()

        # Define model directories
        self.xdg_local = self.home / ".local" / "share"
        self.gguf_models = self.home / "Models"
        self.mlx_models = self.home / ".cache" / "huggingface" / "hub"
        self.lmstudio_models = self.xdg_local / "lmstudio" / "models"
        self.ollama_models = self.xdg_local / "ollama" / "models"

    def lookup_csv(
        self, csv_file: Path, search_key: str, key_column: int = 0
    ) -> ModelConfig | None:
        """
        Look up a value in a CSV file.

        Args:
            csv_file: Path to CSV file
            search_key: Key to search for
            key_column: Column index to search (0-based, default 0)

        Returns:
            ModelConfig object if found, None otherwise
        """
        if not csv_file.exists():
            return None

        with open(csv_file, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) > key_column and row[key_column] == search_key:
                    # Map CSV columns to ModelConfig
                    config = ModelConfig(
                        name=row[0] if len(row) > 0 else "",
                        draft=row[1] if len(row) > 1 else "",
                        context=row[2] if len(row) > 2 else "",
                        temp=row[3] if len(row) > 3 else "",
                        topk=row[4] if len(row) > 4 else "",
                        topp=row[5] if len(row) > 5 else "",
                        aliases=row[6] if len(row) > 6 else "",
                        args=row[7] if len(row) > 7 else "",
                    )
                    return config
        return None

    def find_model(self, base_path: Path, pattern: str) -> Path | None:
        """
        Find a GGUF model file matching a pattern.

        Args:
            base_path: Directory to search
            pattern: Regex pattern to match

        Returns:
            Path to first matching file, or None
        """
        pattern_re = re.compile(pattern)

        # Find all GGUF files > 100MB
        gguf_files: list[Path] = []
        for file in base_path.rglob("*.gguf"):
            if file.is_file() and file.stat().st_size > 100 * 1024 * 1024:
                gguf_files.append(file)

        # Sort and find first match
        gguf_files.sort()
        for file in gguf_files:
            if pattern_re.search(str(file)):
                return file
        return None

    def list_remote_only(
        self, host: str, local_path: Path, remote_path: str
    ) -> list[str]:
        """
        list files that exist on remote but not locally.

        Args:
            host: Remote hostname
            local_path: Local directory path
            remote_path: Remote directory path

        Returns:
            list of remote-only files
        """
        # Get local files
        local_files: set[str] = set()
        if local_path.exists():
            local_files = {f.name for f in local_path.iterdir() if f.is_file()}

        # Get remote files via SSH
        try:
            result = subprocess.run(
                ["ssh", host, f"ls -1 {remote_path}"],
                capture_output=True,
                text=True,
                check=True,
            )
            remote_files = set(result.stdout.strip().split("\n"))
        except subprocess.CalledProcessError:
            return []

        # Return difference
        return sorted(list(remote_files - local_files))

    def download(self, entries: list[str]) -> None:
        """Download models from HuggingFace."""
        for entry in entries:
            # Extract model name (first two parts of path)
            parts = entry.split("/")
            model = "/".join(parts[:2]) if len(parts) >= 2 else entry
            name = model.replace("/", "_")

            # Create directory and clone
            Path(name).mkdir(exist_ok=True)
            _ = subprocess.run(["git", "clone", f"hf.co:{model}", name], check=True)

    def download_cd(self, entry: str) -> None:
        """Download a model and change to its directory."""
        self.download([entry])
        model = "/".join(entry.split("/")[:2])
        name = model.replace("/", "_")
        os.chdir(name)

    def checkout(self, models: list[str]) -> None:
        """Checkout models using Git LFS."""
        for model in models:
            model_path = Path(model)
            if model_path.is_file():
                dir_path = model_path.parent
                base_name = model_path.name

                # Git LFS operations
                _ = subprocess.run(
                    ["git", "lfs", "fetch", "--include", base_name],
                    cwd=dir_path,
                    check=True,
                )
                _ = subprocess.run(
                    ["git", "lfs", "checkout", base_name], cwd=dir_path, check=True
                )
                _ = subprocess.run(["git", "lfs", "dedup"], cwd=dir_path, check=True)

    def import_lmstudio(self, models: list[str]) -> None:
        """Import models to LMStudio."""
        for model in models:
            model_path = Path(model)
            if model_path.is_file():
                file_path = model_path.resolve()
                base = str(file_path).replace(str(self.gguf_models) + "/", "")
                name = base.replace("_", "/")
                target = self.lmstudio_models / name

                # Create directory and link
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    target.unlink()
                target.hardlink_to(file_path)

    def import_ollama(self, models: list[str]) -> None:
        """Import models to Ollama."""
        for model in models:
            model_path = Path(model)
            if model_path.is_file():
                dir_path = model_path.parent
                base_name = model_path.name
                file_path = model_path.resolve()

                # Create modelfile
                modelfile_name = base_name.replace(".gguf", ".modelfile")
                with open(modelfile_name, "w") as f:
                    _ = f.write(f"FROM {file_path}\n")

                # Create Ollama model
                model_name = base_name.replace(".gguf", "")
                _ = subprocess.run(
                    ["ollama", "create", model_name, "-f", modelfile_name], check=True
                )

                # Cleanup
                Path(modelfile_name).unlink()

                # Link duplicates
                _ = subprocess.run(
                    [
                        "linkdups",
                        "-v",
                        str(self.ollama_models / "blobs"),
                        str(dir_path),
                    ],
                    check=True,
                )

    def get_gguf(self, model: str) -> Path | None:
        """
        Find the best GGUF file for a model.

        Searches in priority order: fp32, fp16, f16, q8, q6, q5, q4xl, q4
        """
        model_path = Path(model)

        # Priority patterns to search
        patterns = [
            ("fp32", r"fp32[_-]"),
            ("fp16", r"fp16[_-]"),
            ("f16", r"f16"),
            ("q8", r"[Qq]8_"),
            ("q6", r"[Qq]6_"),
            ("q5", r"[Qq]5_"),
            ("q4xl", r"[Qq]4_.*XL"),
            ("q4", r"[Qq]4_"),
        ]

        # Search for each pattern
        for _name, pattern in patterns:
            found = self.find_model(model_path, pattern)
            if found and found.exists():
                return found

        return None

    def show(self, model: str) -> None:
        """Show model details using gguf-tools."""
        gguf = self.get_gguf(model)
        if gguf:
            _ = subprocess.run(["gguf-tools", "show", str(gguf)], check=True)

    def get_ctx_size(self, model: str) -> int | None:
        """Get the context size of a model."""
        gguf = self.get_gguf(model)
        if not gguf:
            return None

        try:
            result = subprocess.run(
                ["gguf-tools", "show", str(gguf)],
                capture_output=True,
                text=True,
                check=True,
            )

            # Extract context length
            for line in result.stdout.split("\n"):
                if ".context_length" in line:
                    match = re.search(r"\[uint32\] ([0-9]+)", line)
                    if match:
                        return int(match.group(1))
        except subprocess.CalledProcessError:
            pass

        return None

    def generate_json(
        self, model: str
    ) -> dict[str, str | int | bool | list[str]] | None:
        """Generate JSON configuration for a model."""
        model_path = Path(model)
        gguf = self.get_gguf(model)

        if not (model_path.is_dir() and gguf):
            return None

        # Extract model name
        name = re.sub(r".*_", "", model).replace("-GGUF", "")

        # Look up configuration
        config = self.lookup_csv(self.gguf_models / "models.csv", name, 0)

        context = config.context if config else None
        if not context:
            ctx_size = self.get_ctx_size(model)
            context = str(ctx_size) if ctx_size else "4096"

        return {
            "title": f"Hera → {name}",
            "description": "",
            "iconUrl": "",
            "endpoint": f"https://{self.server}:8443/v1/chat/completions",
            "modelID": name,
            "apiType": "openai",
            "contextLength": int(context),
            "headerRows": [],
            "bodyRows": [],
            "skipAPIKey": True,
            "pluginSupported": False,  # tooluse from CSV if available
            "visionSupported": False,
            "systemMessageSupported": True,  # sysprompt from CSV if available
            "streamOutputSupported": True,  # streaming from CSV if available
        }

    def generate_model_config(self, models: list[str]) -> str:
        """Generate model configuration for llama-swap."""
        configs: list[str] = []

        for model in models:
            model_path = Path(model)
            gguf = self.get_gguf(model)

            if not (model_path.is_dir() and gguf):
                continue

            # Extract model name
            name = re.sub(r".*_", "", model).replace("-GGUF", "").replace("-gguf", "")

            # Look up configuration
            config = self.lookup_csv(self.gguf_models / "models.csv", name, 0)

            # Build arguments
            args: list[str] = []
            if config:
                if config.draft:
                    draft_gguf = self.get_model_gguf(config.draft)
                    if draft_gguf:
                        args.append(f"--model-draft {draft_gguf}")
                if config.context:
                    args.append(f"--ctx-size {config.context}")
                elif ctx_size := self.get_ctx_size(model):
                    args.append(f"--ctx-size {ctx_size}")
                if config.temp:
                    args.append(f"--temp {config.temp}")
                if config.topk:
                    args.append(f"--top-k {config.topk}")
                if config.topp:
                    args.append(f"--top-p {config.topp}")
                if config.args:
                    args.append(config.args.strip())

            # Find llama-server executable
            llama_server = subprocess.run(
                ["which", "llama-server"], capture_output=True, text=True
            ).stdout.strip()

            # Build YAML config
            yaml_config = f"""  "{name}":
    proxy: "http://127.0.0.1:${{PORT}}"
    cmd: >
      {llama_server}
        --threads 24
        --jinja
        --port ${{PORT}}
        --model {gguf} {' '.join(args)}
    checkEndpoint: /health"""

            if config and config.aliases:
                yaml_config += f"""
    aliases:
      - {config.aliases}"""

            configs.append(yaml_config)

        return "\n".join(configs)

    def print_yaml(self, f: TextIO = sys.stdout) -> None:
        _ = f.write(
            """healthCheckTimeout: 7200
startPort: 9200

models:
"""
        )

        # Add GGUF models
        gguf_dirs = [str(d) for d in self.gguf_models.iterdir() if d.is_dir()]
        config = self.generate_model_config(gguf_dirs)
        _ = f.write(config + "\n")

        # Add HuggingFace models
        hf_models = self.get_huggingface_models()
        for model in hf_models:
            config = self.lookup_csv(self.gguf_models / "models.csv", model, 0)

            args: list[str] = []
            if config:
                if config.draft:
                    args.append(f"--draft-model {config.draft}")
                if config.temp:
                    args.append(f"--temp {config.temp}")
                if config.topk:
                    args.append(f"--top-k {config.topk}")
                if config.topp:
                    args.append(f"--top-p {config.topp}")
                if config.args:
                    args.append(config.args.strip())

            mlx_lm = subprocess.run(
                ["which", "mlx-lm"], capture_output=True, text=True
            ).stdout.strip()

            _ = f.write(
                f"""  "{model}":
    proxy: "http://127.0.0.1:${{PORT}}"
    cmd: >
      {mlx_lm} server
        --host 127.0.0.1 --port ${{PORT}}
        --max-tokens 8192
        --model {model} {' '.join(args)}
    checkEndpoint: /health
"""
            )

            if config and config.aliases:
                _ = f.write(
                    f"""    aliases:
      - {config.aliases}
"""
                )

        # Append extra configuration if exists
        extra_yaml = self.gguf_models / "llama-swap-extra.yaml"
        if extra_yaml.exists():
            _ = f.write(extra_yaml.read_text())

    def build_yaml(self) -> None:
        """Build the complete llama-swap.yaml configuration file."""
        yaml_path = self.gguf_models / "llama-swap.yaml"

        # Start YAML
        with open(yaml_path, "w") as f:
            self.print_yaml(f)

        # Kill existing llama-swap
        _ = subprocess.run(["killall", "llama-swap"], stderr=subprocess.DEVNULL)

    def run_llama_swap(self) -> None:
        """Start llama-swap with the generated config."""
        config_path = self.gguf_models / "llama-swap.yaml"
        _ = subprocess.run(["llama-swap", "--config", str(config_path)], check=True)

    def get_models(self) -> list[str]:
        """Get list of available models from the server."""
        try:
            response = requests.get(f"http://{self.server}:8080/v1/models")
            data = response.json()
            models: list[str] = [item["id"] for item in data.get("data", [])]
            return sorted(models)
        except Exception as e:
            print(f"Error fetching models: {e}", file=sys.stderr)
            return []

    def get_huggingface_models(self) -> list[str]:
        """Get list of HuggingFace models."""
        try:
            result = subprocess.run(
                ["huggingface-cli", "scan-cache"],
                capture_output=True,
                text=True,
                check=True,
            )
            models: list[str] = []
            for line in result.stdout.split("\n"):
                if "model" in line:
                    parts = line.split()
                    if parts:
                        models.append(parts[0])
            return models
        except subprocess.CalledProcessError:
            return []

    def get_model_files(self) -> list[Path]:
        """Get all GGUF model files."""
        files: list[Path] = []
        for model_dir in self.gguf_models.iterdir():
            if model_dir.is_dir():
                gguf = self.get_gguf(str(model_dir))
                if gguf:
                    files.append(gguf)
        return files

    def get_model_gguf(self, model: str) -> Path | None:
        """Get GGUF file for a given model name."""
        for model_dir in self.gguf_models.iterdir():
            if model_dir.is_dir() and re.search(model, str(model_dir)):
                gguf = self.get_gguf(str(model_dir))
                return gguf
        return None

    def generate_gptel_config(self) -> str:
        """Generate GPTel Emacs configuration."""
        models = self.get_models()
        model_list = "\n".join([f'                "{model}"' for model in models])

        return f"""    (gptel-make-openai "llama-swap"
      :host "{self.server}:8080"
      :protocol "http"
      ;; :stream t
      :models '(
{model_list}
                ))"""

    def get_status(self) -> None:
        """Get llama-swap status."""
        try:
            response = requests.get(f"http://{self.server}:8080/running")
            print(json.dumps(response.json(), indent=2))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)

    def unload(self) -> None:
        """Unload current model."""
        try:
            _ = requests.get(f"http://{self.server}:8080/unload")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)

    def stream_logs(self) -> None:
        """Stream llama-swap logs."""
        try:
            response = requests.get(
                f"http://{self.server}:8080/logs/stream", stream=True
            )
            for line in response.iter_lines():
                if line:
                    print(line.decode("utf-8"))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)

    def git_status_all(self) -> None:
        """Show git status for all model directories."""
        for model_dir in self.gguf_models.iterdir():
            if model_dir.is_dir() and (model_dir / ".git").exists():
                print(f"\n=== {model_dir.name} ===")
                _ = subprocess.run(["git", "status"], cwd=model_dir)

    def git_pull_all(self) -> None:
        """Pull updates for all model directories."""
        for model_dir in self.gguf_models.iterdir():
            if model_dir.is_dir() and (model_dir / ".git").exists():
                print(f"\n=== Pulling {model_dir.name} ===")
                _ = subprocess.run(["git", "pull"], cwd=model_dir)

    def show_sizes(self) -> None:
        """Show sizes of all models."""
        os.chdir(self.gguf_models)
        _ = subprocess.run(["sizes", "-a", "-x", ".git"])

    def show_all_sizes(self) -> None:
        """Show sizes across all model directories."""
        dirs = [
            str(self.ollama_models),
            str(self.lmstudio_models),
            str(self.mlx_models),
            str(self.gguf_models),
        ]
        _ = subprocess.run(["sizes", "-a", "-x", ".git"] + dirs)

    def show_pending(self) -> None:
        """Show pending actions for all models."""
        for model_dir in self.gguf_models.iterdir():
            if not model_dir.is_dir() or model_dir.name == ".git":
                continue

            # Find GGUF file
            gguf = None
            for pattern in [r"([Qq][8654]_|fp?(16|32))"]:
                files = list(model_dir.rglob("*.gguf"))
                files = [f for f in files if f.stat().st_size > 100 * 1024 * 1024]
                for f in sorted(files):
                    if re.search(pattern, f.name):
                        gguf = f
                        break
                if gguf:
                    break

            if gguf:
                # Check for split files
                split_patterns = ["*.part1of*", "*-00001-of-*", "*split*"]
                split_file = None
                for pattern in split_patterns:
                    splits = list(model_dir.rglob(pattern))
                    splits = [f for f in splits if f.stat().st_size > 100 * 1024 * 1024]
                    if splits:
                        split_file = splits[0]
                        break

                if not split_file:
                    # Check if file is hard linked
                    if gguf.stat().st_nlink < 2:
                        print(f"LINK {model_dir} {gguf}")
            else:
                # No GGUF, check for splits to merge
                split_patterns = ["*.part1of*", "*-00001-of-*", "*split*"]
                split_file = None
                for pattern in split_patterns:
                    splits = list(model_dir.rglob(pattern))
                    splits = [f for f in splits if f.stat().st_size > 100 * 1024 * 1024]
                    if splits:
                        split_file = splits[0]
                        break

                if split_file:
                    print(f"MERGE {model_dir} {split_file}")
                else:
                    print(f"FETCH {model_dir}")

    def list_files(self) -> None:
        """List all directories and large files in GGUF models directory."""
        os.chdir(self.gguf_models)

        # Get all directories at depth 1
        dirs = ["."] + [
            str(d.relative_to(".")) for d in Path(".").iterdir() if d.is_dir()
        ]

        # Get all files > 100MB, excluding .git
        large_files: list[Path] = []
        for file in Path(".").rglob("*"):
            if file.is_file() and not ".git" in file.parts:
                if file.stat().st_size > 100 * 1024 * 1024:
                    large_files.append(file.relative_to("."))

        # Combine and sort
        all_items = sorted(set(dirs + large_files))
        for item in all_items:
            print(item)

    def show_remote_only(self) -> None:
        """Show files that exist on remote but not locally."""
        print("==== GGUF ====")
        remote_gguf = self.list_remote_only("vulcan", self.gguf_models, "/tank/Models")
        for item in remote_gguf:
            print(item)

        print("==== MLX ====")
        remote_mlx = self.list_remote_only(
            "vulcan", self.mlx_models, "/tank/HuggingFace"
        )
        for item in remote_mlx:
            print(item)

    def list_all_models(self) -> list[str]:
        """List all models from MLX and GGUF directories."""
        models: list[str] = []

        # Process both directories
        for base_dir in [self.mlx_models, self.gguf_models]:
            if base_dir.exists():
                for item in base_dir.iterdir():
                    # Skip .locks directory
                    if item.name == ".locks":
                        continue

                    if item.is_dir():
                        # Transform MLX model names
                        name = item.name
                        if name.startswith("models--"):
                            name = name[8:]  # Remove 'models--' prefix
                        name = name.replace("--", "_")  # Replace -- with _
                        models.append(name)

        return sorted(models)

    def show_all_models(self) -> None:
        """Print all models."""
        for model in self.list_all_models():
            print(model)

    def show_duplicates(self) -> None:
        """Show duplicate models across MLX and GGUF."""
        from collections import Counter

        models = self.list_all_models()
        counts = Counter(models)

        # Show only duplicates (count > 1)
        for model, count in sorted(counts.items()):
            if count > 1:
                print(f"   {count} {model}")

    def add_submodules(self, directories: list[str]) -> None:
        """Add git submodules for the given directories."""
        for directory in directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                print(f"Error: {directory} does not exist", file=sys.stderr)
                continue

            git_dir = dir_path / ".git"
            if not git_dir.exists():
                print(f"Error: {directory} is not a git repository", file=sys.stderr)
                continue

            try:
                # Get the remote origin URL
                result = subprocess.run(
                    ["git", f"--git-dir={git_dir}", "remote", "get-url", "origin"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                origin_url = result.stdout.strip()

                # Add as submodule
                _ = subprocess.run(
                    ["git", "submodule", "add", origin_url, f"./{directory}"],
                    check=True,
                )
                print(f"Added submodule: {directory}")
            except subprocess.CalledProcessError as e:
                print(f"Error adding submodule {directory}: {e}", file=sys.stderr)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Model management utility for GGUF, MLX, LMStudio, and Ollama models."
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Define all subcommands
    _ = subparsers.add_parser(
        "download", help="Download models from HuggingFace"
    ).add_argument("entries", nargs="+", help="Model entries to download")

    _ = subparsers.add_parser(
        "download-cd", help="Download and change directory"
    ).add_argument("entry", help="Model entry to download")

    _ = subparsers.add_parser(
        "checkout", help="Checkout models using Git LFS"
    ).add_argument("models", nargs="+", help="Model files to checkout")

    _ = subparsers.add_parser(
        "import-lmstudio", help="Import models to LMStudio"
    ).add_argument("models", nargs="+", help="Model files to import")

    _ = subparsers.add_parser(
        "import-ollama", help="Import models to Ollama"
    ).add_argument("models", nargs="+", help="Model files to import")

    _ = subparsers.add_parser(
        "gguf", help="Get GGUF file path for a model"
    ).add_argument("model", help="Model directory")

    _ = subparsers.add_parser("show", help="Show model details").add_argument(
        "model", help="Model directory"
    )

    _ = subparsers.add_parser(
        "ctx-size", help="Get context size of a model"
    ).add_argument("model", help="Model directory")

    _ = subparsers.add_parser(
        "json", help="Generate JSON config for a model"
    ).add_argument("model", help="Model directory")

    _ = subparsers.add_parser(
        "model-config", help="Generate model config"
    ).add_argument("models", nargs="+", help="Model directories")

    _ = subparsers.add_parser("print-yaml", help="Print llama-swap.yaml config file")
    _ = subparsers.add_parser("build-yaml", help="Build llama-swap.yaml config file")
    _ = subparsers.add_parser(
        "llama-swap", help="Start llama-swap with generated config"
    )
    _ = subparsers.add_parser("models", help="list available models")
    _ = subparsers.add_parser("huggingface-models", help="list HuggingFace models")
    _ = subparsers.add_parser("model-files", help="list all GGUF model files")
    _ = subparsers.add_parser("gptel", help="Generate GPTel configuration")
    _ = subparsers.add_parser("status", help="Check llama-swap status")
    _ = subparsers.add_parser("unload", help="Unload current model")
    _ = subparsers.add_parser("logs", help="Stream llama-swap logs")
    _ = subparsers.add_parser("pull", help="Pull updates for all models")
    _ = subparsers.add_parser("sizes", help="Show sizes of all models")
    _ = subparsers.add_parser("all-sizes", help="Show sizes across all directories")
    _ = subparsers.add_parser("pending", help="Show pending actions for models")
    _ = subparsers.add_parser("files", help="List all files and directories")
    _ = subparsers.add_parser("remote-only", help="Show files existing only on remote")
    _ = subparsers.add_parser("all-models", help="List all models from MLX and GGUF")
    _ = subparsers.add_parser("duplicates", help="Show duplicate models")
    _ = subparsers.add_parser("add-submodules", help="Add git submodules").add_argument(
        "directories", nargs="+", help="Directories to add as submodules"
    )
    _ = subparsers.add_parser("help", help="Show help message")

    args = parser.parse_args()

    # Initialize manager
    manager = ModelManager()

    command: str = args.command

    # Handle commands
    if command == "download":
        manager.download(args.entries)
    elif command == "download-cd":
        manager.download_cd(args.entry)
    elif command == "checkout":
        manager.checkout(args.models)
    elif command == "import-lmstudio":
        manager.import_lmstudio(args.models)
    elif command == "import-ollama":
        manager.import_ollama(args.models)
    elif command == "gguf":
        gguf = manager.get_gguf(args.model)
        if gguf:
            print(gguf)
    elif command == "show":
        manager.show(args.model)
    elif command == "ctx-size":
        size = manager.get_ctx_size(args.model)
        if size:
            print(size)
    elif command == "json":
        config = manager.generate_json(args.model)
        if config:
            print(json.dumps(config, indent=2))
    elif command == "model-config":
        print(manager.generate_model_config(args.models))
    elif command == "build-yaml":
        manager.build_yaml()
    elif command == "print-yaml":
        manager.print_yaml()
    elif command == "llama-swap":
        manager.run_llama_swap()
    elif command == "models":
        for model in manager.get_models():
            print(model)
    elif command == "huggingface-models":
        for model in manager.get_huggingface_models():
            print(model)
    elif command == "model-files":
        for file in manager.get_model_files():
            print(file)
    elif command == "gptel":
        print(manager.generate_gptel_config())
    elif command == "status":
        manager.get_status()
    elif command == "unload":
        manager.unload()
    elif command == "logs":
        manager.stream_logs()
    elif command == "pull":
        manager.git_pull_all()
    elif command == "sizes":
        manager.show_sizes()
    elif command == "all-sizes":
        manager.show_all_sizes()
    elif command == "pending":
        manager.show_pending()
    elif command == "files":
        manager.list_files()
    elif command == "remote-only":
        manager.show_remote_only()
    elif command == "all-models":
        manager.show_all_models()
    elif command == "duplicates":
        manager.show_duplicates()
    elif command == "add-submodules":
        manager.add_submodules(args.directories)
    elif command in ["help", None]:
        parser.print_help()
    else:
        # Note: The bash script has duplicate 'status' commands
        # I've kept git_status_all separate but it's not exposed in argparse
        # You could add it as 'git-status' if needed
        parser.print_help()


if __name__ == "__main__":
    main()
