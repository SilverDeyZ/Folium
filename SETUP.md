# Folium diagnostic IPA setup — iPhone, iOS 27.2

Prepared on 2026-11-12 in `C:\Users\Dragon\Documents\Projects\Folium-IPA\Folium`.

Three hosted builds have been attempted on the fork. The third successfully built MesenCE, then stopped in Cytrus because the Sirit dependency requires SPIR-V headers. A successful IPA build, Sideloadly installation, and physical iPhone test remain pending.

## Prepared locally

- Upstream: https://github.com/folium-app/Folium
- Baseline: `4dbc9e8e8450eef350109fe0e816554dcfaee7e5`.
- Branch: `codex/folium-diagnostic-ipa`.
- All ten core submodules are initialized recursively at the committed revisions. Cytrus is `d421219acdcb0ad5494ab68777a52a87465fd8ae`.
- The five Swift package revisions in the upstream `Package.resolved` are preserved. Xcode resolves their sources and checksum-protected binary downloads on macOS.
- All ten tracked XCFrameworks have an arm64 iOS device slice with a real binary. On Windows, this verifies metadata, file presence, and SHA-256; the runner additionally checks with `file`, `lipo`, and `otool`.
- SPIR-V headers, Vulkan C headers, Vulkan-Hpp, glslang headers, and VMA sources are downloaded under ignored `build/headers/`, outside Xcode's synchronized source folders. Commit URLs and archive SHA-256 values are in `ci/headers.lock.json`.
- Cytrus's Debug and Release system header search paths use those repository-relative directories and preserve inherited paths.
- `ci/iphone.xcconfig` selects iPhone and disables developer signing for the diagnostic build. It keeps upstream's minimum OS version; **iOS 27.2 is the physical test OS**, not an assumed installed SDK version.
- `.github/workflows/folium-ipa.yml` supplies a manual macOS build, IPA/provenance artifact, and separate logs on success or failure.

The upstream README contains an app description but no build instructions. [The adapted plan](docs/folium-plan.md) supplies the build approach. The header versions match the upstream Vulkan SDK search version where possible; their compatibility with the prebuilt glslang libraries still needs the first clean macOS build.

Local verification covers source/XCFramework preflight, pinned archive checksums and header-tree revalidation, accessibility of all five locked package commits, seven regression tests, Python compilation, Bash syntax, Git whitespace checks, and actionlint 1.7.12. Actionlint was configured to recognize the documented `xcode-27` label; ShellCheck was unavailable. Both build and packaging commands were also checked to reject Windows execution without producing an IPA.

## Validate or refresh on Windows

Run from this repository in PowerShell, with Git and Python 3.12 or newer installed:

```powershell
git submodule update --init --recursive
python ci/preflight.py
python ci/fetch-headers.py
git submodule status --recursive
```

The fetcher verifies archive checksums before extraction. Rerunning it also checks existing header contents against the verified sources and refuses to replace modified files. Existing downloads in `Dependencies/CIHeaders/` are moved to `build/headers/` without deleting them. If both locations exist, move the legacy tree outside `Dependencies` before rerunning. `build/source-manifest.json` records source, core, package, and tracked binary revisions/checksums. `build/` and downloaded header sources are ignored by Git.

## First hosted run and correction

[Run #1](https://github.com/SilverDeyZ/Folium/actions/runs/43258503264) used Xcode 27.1 with the iPhoneOS 27.1 SDK and resolved all five packages at their locked revisions. It stopped while preflight tried to open `__MACOSX/._SDL3.xcframework/Info.plist`: that matching filename is AppleDouble metadata, not a framework directory. The Node.js deprecation warning was separate from the failure.

Framework discovery now selects directories and excludes `__MACOSX` and `._*` metadata entries. Real malformed frameworks and simulator-only slices still fail validation. Four regression tests pass and run before preflight in CI. The checkout and artifact actions are also updated to SHA-pinned Node.js 24 releases.

## MesenCE compilation failure and correction

[Run #2](https://github.com/SilverDeyZ/Folium/actions/runs/43263613629) passed all four regression tests and validated 26 arm64 iOS XCFrameworks, then failed while compiling `MesenCE/mesence.cpp`. The include trace shows `Emulator.h` resolving `#include "pch.h"` to `Dependencies/CIHeaders/glslang/glslang/HLSL/pch.h`, producing missing `string`, `thread`, `__forceinline`, and `__noinline` definitions. The file was present; Xcode selected a foreign header with the same name.

The local correction moves the downloaded sources outside the synchronized `Dependencies` folder, updates Cytrus's Debug/Release search paths to `build/headers`, and explicitly includes `System/Core/pch.h` at the start of `MesenCE/mesence.h`. Seven local regression tests now cover archive discovery and migration of existing header downloads. The next hosted build must establish whether compilation completes; this correction is not yet an IPA build result.

## Cytrus SPIR-V header failure and correction

[Run #3](https://github.com/SilverDeyZ/Folium/actions/runs/43272418341) confirmed the MesenCE correction: `libMesenCE.a` was built successfully. Cytrus then failed compiling `vk_shader_disk_cache.cpp` because Sirit's `sirit.h` includes `spirv/unified1/spirv.hpp11`, which was not supplied by the previous four header downloads.

The local correction adds Khronos SPIRV-Headers at SDK tag `vulkan-sdk-1.4.363.0`, commit `496543121ce6419f23d6fa5d7194ba66c36212d2`, with archive SHA-256 `a9bb9c48713245eacf97cc539b6f1d45405a92d8813f8b82e635f0a085ee9898`. Cytrus's Debug and Release search paths now include `build/headers/spirv-headers/include`, and the fetcher verifies `spirv.hpp11` and `GLSL.std.450.h` before compilation. Package and core revisions are unchanged. This correction has not yet been tested by a hosted build.

## Push the correction and start a new run

`origin` points to [SilverDeyZ/Folium](https://github.com/SilverDeyZ/Folium), and `upstream` points to `folium-app/Folium`. The workflow already exists on the fork's default branch. The correction is currently local and uncommitted.

1. Commit and push the correction from this repository:

   ```powershell
   git add Folium.xcodeproj/project.pbxproj ci/headers.lock.json ci/fetch-headers.py SETUP.md docs/folium-plan.md
   git commit -m "Add pinned SPIR-V headers for Cytrus"
   git push origin codex/folium-diagnostic-ipa
   ```

2. In the fork's **Actions** tab, select **Folium diagnostic IPA**, select **Run workflow**, choose **codex/folium-diagnostic-ipa**, and start the new run. Rerunning the old failed job uses its old commit and will not include this correction.
3. Download `Folium-iPhone-iOS-27.2-<commit>` after a successful run. It contains the `.ipa`, `.sha256`, `build-manifest.json`, package/header locks, toolchain information, and source patch/status. Failed runs retain a separate `Folium-logs-...` artifact when logs are available.

The workflow uses the documented [`xcode-27` arm64 runner](https://docs.github.com/en/actions/reference/runners/github-hosted-runners). Its installed Xcode and iPhoneOS SDK versions are recorded in each run; they are not silently pinned by the label. Checkout and upload actions are pinned to release commit SHAs. The checked-in dependencies contain actual binaries, so LFS is not enabled.

On a Mac with Xcode and Python 3.12+, the same path is:

```bash
bash ci/build-folium-ipa.sh
```

Every invocation creates fresh `build/diagnostic.XXXXXX/DerivedData` and staging directories. A failed build stops before packaging. The packager reads `TARGET_BUILD_DIR` and `WRAPPER_NAME` from resolved settings, validates arm64/iOS Mach-O binaries and runtime dependencies, signs the bundle ad hoc, and packages `Payload/Folium.app`. Sideloadly supplies the final provisioning and device-installable signature locally.

## Install and test on iPhone running iOS 27.2

1. Back up existing Folium app data. If retaining another installation, choose a separate bundle identifier in Sideloadly and record it.
2. Check the downloaded IPA against its `.sha256` file, then use Sideloadly on Windows to sign and install it on the connected iPhone. Follow the device trust/Developer Mode prompts required by that installation.
3. Check launch, permissions, library UI, and import with personally supplied homebrew or a game and system files you are entitled to use. Keep these files outside the repository and workflow artifacts.
4. In Cytrus settings, first disable **CPU JIT** (`cytrus.cpuJIT`) and **Shader JIT** (`cytrus.shaderJIT`). Confirm that settings reach the core before launching a title. Assess the fast-interpreter option separately if needed; it is not proof of usable JIT.
5. Check graphics, both 3DS screens, touch/controller input, audio, save/load, and relaunch after terminating the app. Collect crash/emulator logs for failures.
6. Investigate JIT separately after the interpreter baseline runs. Activation and performance on iOS 27.2 are unverified; no Henge entitlements, helper, RAM changes, or JIT patches are included.

The local correction is ready for another macOS build. Successful compilation, dependency ABI compatibility, installation, and physical-device behavior remain to be established. The plan's final completion criterion still requires a working 3DS test on the physical iPhone.
