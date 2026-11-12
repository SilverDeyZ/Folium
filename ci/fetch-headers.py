"""Download checksum-locked headers; runs on Windows or macOS with Python 3.12+."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request


ROOT = Path(__file__).resolve().parents[1]


def prepare_destination(root):
    """Keep downloaded sources outside Xcode's synchronized project folders."""
    root = root.resolve()
    destination = root / "build/headers"
    legacy = root / "Dependencies/CIHeaders"
    for path in (destination, legacy):
        if not path.resolve().is_relative_to(root):
            raise ValueError(f"Header directory resolves outside this checkout: {path}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if legacy.exists():
        if destination.exists():
            raise ValueError(
                f"Both {legacy} and {destination} exist. Move {legacy} outside "
                "Dependencies before building; Xcode scans it into project header maps."
            )
        legacy.rename(destination)
        print(f"Moved existing native headers to {destination}", flush=True)
    destination.mkdir(parents=True, exist_ok=True)
    return destination


def tree_digest(directory):
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(directory).as_posix().encode() + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def main():
    destination = prepare_destination(ROOT)
    sources = json.loads((ROOT / "ci/headers.lock.json").read_text())["sources"]
    for source in sources:
        target = destination / source["name"]
        with tempfile.TemporaryDirectory(dir=destination) as temporary:
            temporary = Path(temporary)
            archive = temporary / "source.tar.gz"
            print(f"Fetching {source['name']} at {source['revision']}", flush=True)
            with urllib.request.urlopen(source["url"], timeout=120) as response:
                with archive.open("wb") as output:
                    shutil.copyfileobj(response, output)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            if digest != source["sha256"]:
                raise SystemExit(f"Checksum mismatch for {source['name']}: {digest}")
            unpacked = temporary / "unpacked"
            with tarfile.open(archive) as contents:
                contents.extractall(unpacked, filter="data")
            roots = list(unpacked.iterdir())
            if len(roots) != 1 or not roots[0].is_dir():
                raise SystemExit(f"Unexpected archive layout: {source['name']}")
            if target.exists():
                if tree_digest(target) != tree_digest(roots[0]):
                    raise SystemExit(f"Modified header tree: {target}; move it aside before fetching.")
                print(f"Verified existing {source['name']} headers.")
            else:
                roots[0].rename(target)
    required = [
        "spirv-headers/include/spirv/unified1/spirv.hpp11",
        "spirv-headers/include/spirv/unified1/GLSL.std.450.h",
        "vulkan-headers/include/vulkan/vulkan.h",
        "vulkan-hpp/vulkan/vulkan.hpp",
        "glslang/glslang/Public/ShaderLang.h",
        "glslang/SPIRV/GlslangToSpv.h",
        "vma/include/vk_mem_alloc.h",
    ]
    for header in required:
        if not (destination / header).is_file():
            raise SystemExit(f"Missing header: {header}")
    print("Pinned native headers are ready.")


if __name__ == "__main__":
    main()
