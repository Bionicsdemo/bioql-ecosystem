# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Upload checkpoint-2000 to Modal Volume
"""
import modal

app = modal.App("upload-checkpoint")

volume = modal.Volume.from_name("bioql-checkpoint", create_if_missing=True)

@app.function(
    volumes={"/checkpoint": volume},
    timeout=600
)
def upload_checkpoint():
    """Upload checkpoint files to Modal volume"""
    import os
    import shutil
    from pathlib import Path

    # Local checkpoint path
    local_path = Path("/Users/heinzjungbluth/Desktop/bioql/bioql/llm/trained_model")
    remote_path = Path("/checkpoint")

    print(f"📦 Uploading checkpoint from {local_path} to Modal volume...")

    # Copy all files
    for file in local_path.glob("*"):
        if file.is_file():
            dest = remote_path / file.name
            print(f"  Copying {file.name}...")
            shutil.copy2(file, dest)

    # Commit volume
    volume.commit()

    # List files
    print("\n✅ Files uploaded:")
    for file in remote_path.glob("*"):
        size = file.stat().st_size / (1024 * 1024)  # MB
        print(f"  {file.name}: {size:.2f} MB")

    print("\n🎉 Checkpoint uploaded successfully!")


@app.local_entrypoint()
def main():
    upload_checkpoint.remote()
