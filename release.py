# -*- coding: utf-8 -*-

"""Automated release pipeline for the Random project.

Pipeline (8 steps):

    1. Enter the project virtual environment
    2. Run the PyInstaller packaging commands
    3. Merge dist/RandomMain, dist/RandomSetting, dist/RandomLauncher
       into release/Random_v<version>
    4. Copy the Font and Doc folders into release/Random_v<version>
    5. Clean up the build folder, the dist folder and every *.spec file
    6. Generate installer.nsi inside release/Random_v<version> by walking
       the staging directory
    7. Build the installer with NSIS
    8. Remove the release/Random_v<version> staging directory

The product version is imported from RandomConfig.

Usage:
    python release.py                 # full pipeline
    python release.py --keep-staging  # keep release/Random_v<version>
    python release.py --makensis "C:\\Program Files (x86)\\NSIS\\makensis.exe"

Every step prints a start banner and an end status.
"""

from __future__ import annotations

import argparse
import filecmp
import os
import re
import shutil
import string
import subprocess
import sys
import time
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent

VENV_DIR_NAMES = (".venv", "venv", "env")
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
RELEASE_DIR = PROJECT_ROOT / "release"
FONT_DIR = PROJECT_ROOT / "Font"
DOC_DIR = PROJECT_ROOT / "Doc"

EXTRA_ROOT_FILES = ("LICENSE",)

PACKAGING_COMMANDS = (
    "pyinstaller -w -i icon.ico -y RandomMain.py --hidden-import=pkg_resources.extern",
    "pyinstaller -w -i icon.ico -y RandomSetting.py --hidden-import=pkg_resources.extern",
    "pyinstaller -w -i icon.ico -y RandomLauncher.py --hidden-import=pkg_resources.extern",
)

DIST_SUBDIRS = ("RandomMain", "RandomSetting", "RandomLauncher")

GUARDED_EXECUTABLES = ("RandomLauncher.exe", "RandomMain.exe", "RandomSetting.exe")

PRODUCT_NAME = "Random"
PRODUCT_PUBLISHER = "Studio SEVENTEEN"
LAUNCHER_EXE = "RandomLauncher.exe"
MAIN_EXE = "RandomMain.exe"
STARTUP_SHORTCUT = "RandomMain.lnk"

MAKENSIS_COMMON_PATHS = (
    r"C:\Program Files (x86)\NSIS\makensis.exe",
    r"C:\Program Files\NSIS\makensis.exe",
    r"%LOCALAPPDATA%\Programs\NSIS\makensis.exe",
    r"%ProgramFiles(x86)%\NSIS\makensis.exe",
    r"%ProgramFiles%\NSIS\makensis.exe",
)

NSIS_REGISTRY_KEY = r"SOFTWARE\NSIS"

TOTAL_STEPS = 8
LINE_WIDTH = 78


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------


class Logger:
    """Tiny console logger: every step gets a start banner and an end status."""

    def __init__(self) -> None:
        self._step_started_at = 0.0

    def banner(self, lines) -> None:
        print("=" * LINE_WIDTH)
        for line in lines:
            print(line)
        print("=" * LINE_WIDTH)
        print()

    def step_start(self, index: int, title: str) -> None:
        self._step_started_at = time.time()
        print("-" * LINE_WIDTH)
        print("[{}/{}] START  - {}".format(index, TOTAL_STEPS, title))

    def info(self, message: str) -> None:
        print("             {}".format(message))

    def command(self, message: str) -> None:
        print("           > {}".format(message))

    def step_end(self, status: str = "OK", message: str = "") -> None:
        elapsed = time.time() - self._step_started_at
        suffix = " - {}".format(message) if message else ""
        print("             END    - {} ({:.1f}s){}".format(status, elapsed, suffix))
        print()

    def fatal(self, message: str) -> None:
        print("             END    - FAILED")
        print()
        print("=" * LINE_WIDTH)
        print("RELEASE FAILED: {}".format(message))
        print("=" * LINE_WIDTH)


LOG = Logger()


class ReleaseError(RuntimeError):
    """Raised when a pipeline step cannot be completed."""


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def sort_key(name: str) -> str:
    """Case-insensitive, stable ordering used for file and folder listings."""

    return name.lower()


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024.0 or unit == "GB":
            return "{:.1f} {}".format(size, unit)
        size /= 1024.0
    return "{:.1f} GB".format(size)


def count_files(root: Path) -> int:
    return sum(len(filenames) for _, _, filenames in os.walk(root))


def find_venv_dir() -> Path:
    for name in VENV_DIR_NAMES:
        candidate = PROJECT_ROOT / name
        if (candidate / "Scripts" / "python.exe").is_file():
            return candidate
    raise ReleaseError(
        "No project virtual environment found in {}. Expected one of: {}".format(
            PROJECT_ROOT, ", ".join(VENV_DIR_NAMES)
        )
    )


def read_version() -> str:
    """Import VERSION from RandomConfig (fallback: parse the source file)."""

    try:
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        import RandomConfig  # type: ignore[import-not-found]

        version = str(RandomConfig.VERSION).strip()
        if version:
            return version
        LOG.info("RandomConfig.VERSION is empty, falling back to source parsing.")
    except Exception as exc:  # depends on the environment, e.g. missing Qt
        LOG.info(
            "Could not import RandomConfig ({}: {}); falling back to source parsing.".format(
                exc.__class__.__name__, exc
            )
        )

    source = (PROJECT_ROOT / "RandomConfig.py").read_text(
        encoding="utf-8", errors="replace"
    )
    match = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', source, re.MULTILINE)
    if not match:
        raise ReleaseError("VERSION could not be found in RandomConfig.py")
    return match.group(1).strip()


def locate_makensis(explicit: str | None) -> Path:
    """Find makensis.exe via CLI argument, environment, PATH, registry, drives."""

    candidates = []

    if explicit:
        candidates.append(Path(explicit))

    for var in ("MAKENSIS", "MAKENSIS_EXE", "NSIS_HOME", "NSISDIR"):
        value = os.environ.get(var)
        if value:
            path = Path(value)
            candidates.append(
                path if path.suffix.lower() == ".exe" else path / "makensis.exe"
            )

    which = shutil.which("makensis")
    if which:
        candidates.append(Path(which))

    candidates.extend(Path(os.path.expandvars(p)) for p in MAKENSIS_COMMON_PATHS)

    try:
        import winreg

        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                try:
                    with winreg.OpenKey(
                        hive, NSIS_REGISTRY_KEY, 0, winreg.KEY_READ | view
                    ) as key:
                        install_dir = winreg.QueryValueEx(key, "")[0]
                except OSError:
                    continue
                if install_dir:
                    candidates.append(Path(install_dir) / "makensis.exe")
    except ImportError:
        pass

    for letter in string.ascii_uppercase:
        root = "{}:\\".format(letter)
        if os.path.exists(root):
            candidates.append(Path(root) / "NSIS" / "makensis.exe")

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    raise ReleaseError(
        "makensis.exe (NSIS) was not found. Install NSIS or pass --makensis <path>."
    )


def remove_tree(path: Path, what: str) -> bool:
    if not path.exists():
        LOG.info("{} does not exist, nothing to remove: {}".format(what, path))
        return False
    shutil.rmtree(path)
    LOG.info("Removed {}: {}".format(what, path))
    return True


def same_content(left: Path, right: Path) -> bool:
    try:
        return filecmp.cmp(str(left), str(right), shallow=False)
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Step 1 - virtual environment
# ---------------------------------------------------------------------------


def step_enter_venv(args) -> Path:
    """Make sure this script runs inside the project virtual environment."""

    LOG.step_start(1, "Enter the project virtual environment")

    venv_dir = find_venv_dir()
    venv_python = (venv_dir / "Scripts" / "python.exe").resolve()
    current_python = Path(sys.executable).resolve()

    LOG.info("Virtual environment : {}".format(venv_dir))
    LOG.info("Current interpreter : {}".format(current_python))

    if current_python != venv_python:
        LOG.info("Interpreter differs, re-launching release.py with the venv python.")
        LOG.command('"{}" "{}" {}'.format(venv_python, Path(__file__).resolve(),
                                          " ".join(args.original_argv)))

        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(venv_dir)
        env["PATH"] = str(venv_dir / "Scripts") + os.pathsep + env.get("PATH", "")
        env["PYTHONUTF8"] = "1"
        env.pop("PYTHONHOME", None)

        completed = subprocess.run(
            [str(venv_python), str(Path(__file__).resolve())] + list(args.original_argv),
            cwd=str(PROJECT_ROOT),
            env=env,
        )
        LOG.step_end(
            "OK" if completed.returncode == 0 else "FAILED",
            "pipeline finished inside the venv, exit code {}".format(
                completed.returncode
            ),
        )
        sys.exit(completed.returncode)

    LOG.info("Already running inside the project virtual environment.")
    LOG.step_end("OK", "interpreter {}".format(current_python))
    return venv_dir


# ---------------------------------------------------------------------------
# Step 2 - packaging commands
# ---------------------------------------------------------------------------


def step_run_packaging(venv_dir: Path) -> None:
    LOG.step_start(2, "Run the hard-coded PyInstaller packaging commands")

    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(venv_dir)
    env["PATH"] = str(venv_dir / "Scripts") + os.pathsep + env.get("PATH", "")
    env["PYTHONUTF8"] = "1"
    env.pop("PYTHONHOME", None)

    pyinstaller = shutil.which("pyinstaller", path=env["PATH"])
    if not pyinstaller:
        raise ReleaseError(
            "pyinstaller was not found inside the virtual environment ({})".format(
                venv_dir
            )
        )
    LOG.info("Using PyInstaller : {}".format(pyinstaller))

    for index, command in enumerate(PACKAGING_COMMANDS, start=1):
        LOG.command("[{}/{}] {}".format(index, len(PACKAGING_COMMANDS), command))
        completed = subprocess.run(command, cwd=str(PROJECT_ROOT), env=env, shell=True)
        if completed.returncode != 0:
            raise ReleaseError(
                "packaging command #{} failed with exit code {}: {}".format(
                    index, completed.returncode, command
                )
            )
        LOG.info("Command #{} finished successfully.".format(index))

    LOG.step_end("OK", "{} commands executed".format(len(PACKAGING_COMMANDS)))


# ---------------------------------------------------------------------------
# Step 3 - merge the dist folders
# ---------------------------------------------------------------------------


def step_merge_dist(staging_dir: Path) -> dict:
    LOG.step_start(
        3, "Merge the dist outputs into {}".format(staging_dir.relative_to(PROJECT_ROOT))
    )

    for name in DIST_SUBDIRS:
        source = DIST_DIR / name
        if not source.is_dir():
            raise ReleaseError(
                "expected PyInstaller output folder is missing: {}".format(source)
            )

    if staging_dir.exists():
        LOG.info("Removing stale staging directory: {}".format(staging_dir))
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    identical = 0
    conflicts = []

    for name in DIST_SUBDIRS:
        source = DIST_DIR / name
        LOG.info("Merging {} ...".format(source))
        for dirpath, dirnames, filenames in os.walk(source):
            dirnames.sort(key=sort_key)
            relative = Path(dirpath).relative_to(source)
            target_dir = staging_dir / relative
            target_dir.mkdir(parents=True, exist_ok=True)
            for filename in sorted(filenames, key=sort_key):
                src_file = Path(dirpath) / filename
                dst_file = target_dir / filename
                if dst_file.exists():
                    if src_file.stat().st_size == dst_file.stat().st_size and same_content(
                        src_file, dst_file
                    ):
                        identical += 1
                    else:
                        conflicts.append(str(dst_file.relative_to(staging_dir)))
                shutil.copy2(src_file, dst_file)
                copied += 1
        LOG.info("Merged {} file(s) after {}".format(copied, name))

    if conflicts:
        LOG.info(
            "{} file(s) came from more than one dist folder; the last copy won:".format(
                len(conflicts)
            )
        )
        for relative in conflicts:
            LOG.info("  conflict: {}".format(relative))
    LOG.info(
        "{} file(s) copied, {} duplicate file(s) were identical.".format(copied, identical)
    )

    LOG.step_end(
        "OK", "{} file(s) in the staging directory".format(count_files(staging_dir))
    )
    return {"copied": copied, "identical": identical, "conflicts": len(conflicts)}


# ---------------------------------------------------------------------------
# Step 4 - copy the resource folders
# ---------------------------------------------------------------------------


def step_copy_assets(staging_dir: Path) -> None:
    LOG.step_start(4, "Copy the Font and Doc folders into the staging directory")

    for source in (FONT_DIR, DOC_DIR):
        if not source.is_dir():
            raise ReleaseError("resource folder is missing: {}".format(source))
        target = staging_dir / source.name
        shutil.copytree(source, target, dirs_exist_ok=True)
        LOG.info("{} -> {} ({} file(s))".format(source, target, count_files(target)))

    for filename in EXTRA_ROOT_FILES:
        source = PROJECT_ROOT / filename
        if not source.is_file():
            LOG.info("Optional root file not present, skipped: {}".format(filename))
            continue
        shutil.copy2(source, staging_dir / filename)
        LOG.info("{} -> {} (root file)".format(source, staging_dir / filename))

    LOG.step_end(
        "OK", "{} file(s) in the staging directory".format(count_files(staging_dir))
    )


# ---------------------------------------------------------------------------
# Step 5 - clean up the build artefacts
# ---------------------------------------------------------------------------


def step_clean_workspace() -> None:
    LOG.step_start(5, "Clean the build folder, the dist folder and all spec files")

    remove_tree(BUILD_DIR, "build folder")
    remove_tree(DIST_DIR, "dist folder")

    spec_files = sorted(PROJECT_ROOT.glob("*.spec"), key=lambda p: sort_key(p.name))
    if not spec_files:
        LOG.info("No .spec file found in {}".format(PROJECT_ROOT))
    for spec_file in spec_files:
        try:
            spec_file.unlink()
        except OSError as exc:
            raise ReleaseError("could not delete {}: {}".format(spec_file, exc)) from exc
        LOG.info("Removed spec file: {}".format(spec_file.name))

    LOG.step_end("OK", "{} spec file(s) removed".format(len(spec_files)))


# ---------------------------------------------------------------------------
# Step 6 - generate installer.nsi from the staging directory
# ---------------------------------------------------------------------------


def iter_installer_entries(staging_dir: Path):
    """Yield ("relative\\dir" or "", [file names]) for every populated folder."""

    root_files = sorted(
        (p.name for p in staging_dir.iterdir() if p.is_file()), key=sort_key
    )
    if root_files:
        yield "", root_files

    for dirpath, dirnames, filenames in os.walk(staging_dir):
        dirnames.sort(key=sort_key)
        relative = Path(dirpath).relative_to(staging_dir)
        if relative == Path("."):
            continue
        files = sorted(filenames, key=sort_key)
        if files:
            yield str(relative), files


def build_installer_script(staging_dir: Path, version: str, output_exe: Path) -> tuple:
    """Render the NSIS script text and count the files it references."""

    executable_checks = "\n".join(
        '    !insertmacro CheckProcessRunning "{}"'.format(name)
        for name in GUARDED_EXECUTABLES
    )

    groups = []
    file_count = 0

    for relative_dir, filenames in iter_installer_entries(staging_dir):
        out_path = "$INSTDIR" if not relative_dir else "$INSTDIR\\{}".format(relative_dir)
        lines = ['    SetOutPath "{}"'.format(out_path), ""]
        for filename in filenames:
            if relative_dir:
                lines.append('    File "{}\\{}"'.format(relative_dir, filename))
            else:
                lines.append('    File "{}"'.format(filename))
            file_count += 1
        groups.append("\n".join(lines))

    body_text = "\n\n".join(groups)

    script = """\
; ---------------------------------------------------------------------------
; Auto-generated by release.py on {generated_at} - do not edit by hand.
; All File entries below were discovered by walking the staging directory, so
; the installer ships exactly the files staged for this release.
; Product version   : {version}
; Staged file count : {file_count}
; ---------------------------------------------------------------------------

!define PRODUCT_NAME "{product_name}"
!define PRODUCT_VERSION "{version}"
!define PRODUCT_PUBLISHER "{publisher}"

!include "MUI2.nsh"
!include "LogicLib.nsh"

!macro CheckProcessRunning exe_name
    nsExec::ExecToStack 'cmd /c "tasklist /FI "IMAGENAME eq ${{exe_name}}" /NH 2>nul | findstr /C:"${{exe_name}}" >nul"'
    Pop $0
    ${{If}} $0 = 0
        ${{If}} ${{Silent}}
            Quit
        ${{Else}}
            MessageBox MB_OK|MB_ICONSTOP "${{exe_name}} is still running. Please close all Random programs before continuing."
            Quit
        ${{EndIf}}
    ${{EndIf}}
!macroend

Name "${{PRODUCT_NAME}} ${{PRODUCT_VERSION}}"
OutFile "{output_exe}"
InstallDir "$LOCALAPPDATA\\${{PRODUCT_NAME}}"
InstallDirRegKey HKCU "Software\\${{PRODUCT_NAME}}" "InstallDir"
RequestExecutionLevel user

SetCompressor /SOLID lzma
SetCompressorDictSize 64

!define MUI_PAGE_CUSTOMFUNCTION_LEAVE LaunchRandomMain
!insertmacro MUI_PAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"

Function LaunchRandomMain
    SetOutPath "$INSTDIR"
    Exec '"$INSTDIR\{main_exe}"'
FunctionEnd

Section ""

{executable_checks}

{body}

    WriteRegStr HKCU "Software\\${{PRODUCT_NAME}}" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{PRODUCT_NAME}}" \\
                     "DisplayName" "${{PRODUCT_NAME}}"
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{PRODUCT_NAME}}" \\
                     "UninstallString" '"$INSTDIR\\uninstall.exe"'
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{PRODUCT_NAME}}" \\
                     "DisplayVersion" "${{PRODUCT_VERSION}}"
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{PRODUCT_NAME}}" \\
                     "Publisher" "${{PRODUCT_PUBLISHER}}"
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{PRODUCT_NAME}}" \\
                     "DisplayIcon" "$INSTDIR\\{launcher_exe}"


    WriteUninstaller "$INSTDIR\\uninstall.exe"

    SetOutPath "$INSTDIR"
    CreateShortCut "$SMPROGRAMS\\{product_name}.lnk" "$INSTDIR\\{launcher_exe}"
    CreateShortCut "$DESKTOP\\{product_name}.lnk" "$INSTDIR\\{launcher_exe}"
    ; auto run: shortcut in the Startup folder of the current user (shell:startup),
    ; its working directory is the $OUTDIR set above
    CreateShortCut "$SMSTARTUP\\{startup_shortcut}" "$INSTDIR\\{main_exe}" "" "$INSTDIR\\{main_exe}" 0

SectionEnd

Section "Uninstall"

{executable_checks}

    Delete "$SMPROGRAMS\\{product_name}.lnk"
    Delete "$DESKTOP\\{product_name}.lnk"
    Delete "$SMSTARTUP\\{startup_shortcut}"
    RMDir "$SMPROGRAMS"

    RMDir /r /REBOOTOK "$INSTDIR"

    DeleteRegKey HKCU "Software\\${{PRODUCT_NAME}}"
    DeleteRegKey HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{PRODUCT_NAME}}"

SectionEnd
""".format(
        generated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        version=version,
        product_name=PRODUCT_NAME,
        publisher=PRODUCT_PUBLISHER,
        launcher_exe=LAUNCHER_EXE,
        main_exe=MAIN_EXE,
        startup_shortcut=STARTUP_SHORTCUT,
        output_exe=output_exe,
        executable_checks=executable_checks,
        file_count=file_count,
        body=body_text,
    )

    return script, file_count


def step_write_installer_script(staging_dir: Path, version: str, output_exe: Path) -> Path:
    LOG.step_start(6, "Create installer.nsi from the staged files")

    staged_files = count_files(staging_dir)
    script, file_count = build_installer_script(staging_dir, version, output_exe)
    nsi_path = staging_dir / "installer.nsi"
    nsi_path.write_text(script, encoding="utf-8", newline="\r\n")

    LOG.info("Installer script : {}".format(nsi_path))
    LOG.info("Product version  : {}".format(version))
    LOG.info("Output installer : {}".format(output_exe))
    LOG.info(
        "{} staged file(s) referenced by the generated script.".format(file_count)
    )
    if file_count != staged_files:
        raise ReleaseError(
            "file count mismatch: walked {} file(s), script lists {}".format(
                staged_files, file_count
            )
        )

    LOG.step_end("OK", "installer.nsi written ({} files)".format(file_count))
    return nsi_path


# ---------------------------------------------------------------------------
# Step 7 - build the installer
# ---------------------------------------------------------------------------


def step_build_installer(nsi_path: Path, makensis_arg, output_exe: Path) -> None:
    LOG.step_start(7, "Build the installer with NSIS (makensis)")

    makensis = locate_makensis(makensis_arg)
    LOG.info("makensis : {}".format(makensis))
    LOG.info("Script   : {}".format(nsi_path))

    LOG.command('"{}" "{}"'.format(makensis, nsi_path))
    completed = subprocess.run(
        [str(makensis), "/V2", str(nsi_path)],
        cwd=str(nsi_path.parent),
    )
    if completed.returncode != 0:
        raise ReleaseError(
            "makensis failed with exit code {}".format(completed.returncode)
        )
    if not output_exe.is_file():
        raise ReleaseError(
            "makensis reported success but {} was not created".format(output_exe)
        )

    LOG.info(
        "Installer : {} ({})".format(output_exe, human_size(output_exe.stat().st_size))
    )
    LOG.step_end("OK", output_exe.name)


# ---------------------------------------------------------------------------
# Step 8 - remove the staging directory
# ---------------------------------------------------------------------------


def step_cleanup_staging(staging_dir: Path, keep: bool) -> None:
    LOG.step_start(8, "Clean the {} staging directory".format(staging_dir.name))

    if keep:
        LOG.info("--keep-staging was given, the staging directory is kept as is.")
        LOG.step_end("OK", "skipped on request")
        return

    if not staging_dir.exists():
        LOG.info("Staging directory is already gone: {}".format(staging_dir))
    else:
        shutil.rmtree(staging_dir)
        LOG.info("Removed staging directory: {}".format(staging_dir))

    LOG.step_end("OK", "staging directory removed")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Build the Random installer with PyInstaller and NSIS.",
    )
    parser.add_argument(
        "--keep-staging",
        action="store_true",
        help="do not delete release/Random_v<version> after the build",
    )
    parser.add_argument(
        "--makensis",
        metavar="PATH",
        default=None,
        help="explicit path to makensis.exe",
    )
    return parser.parse_args(argv)


def main(argv) -> int:
    args = parse_args(argv)
    args.original_argv = list(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    LOG.banner(
        [
            "Random - automated release pipeline",
            "Project root : {}".format(PROJECT_ROOT),
            "Started at   : {}".format(time.strftime("%Y-%m-%d %H:%M:%S")),
        ]
    )

    started_at = time.time()

    try:
        # Step 1 - makes sure the remaining steps run with the venv interpreter.
        venv_dir = step_enter_venv(args)

        version = read_version()
        version_number = version[1:] if version.lower().startswith("v") else version
        staging_dir = RELEASE_DIR / "{}_{}".format(PRODUCT_NAME, version)
        output_exe = RELEASE_DIR / "{}_v{}.exe".format(PRODUCT_NAME, version_number)

        LOG.banner(
            [
                "Configuration",
                "Version     : {} (installer version {})".format(version, version_number),
                "Virtual env : {}".format(venv_dir),
                "Staging dir : {}".format(staging_dir),
                "Setup file  : {}".format(output_exe),
            ]
        )

        RELEASE_DIR.mkdir(parents=True, exist_ok=True)

        # Steps 2 - 8
        step_run_packaging(venv_dir)
        step_merge_dist(staging_dir)
        step_copy_assets(staging_dir)
        step_clean_workspace()
        nsi_path = step_write_installer_script(staging_dir, version_number, output_exe)
        step_build_installer(nsi_path, args.makensis, output_exe)
        step_cleanup_staging(staging_dir, args.keep_staging)

    except ReleaseError as exc:
        LOG.fatal(str(exc))
        return 1
    except subprocess.CalledProcessError as exc:
        LOG.fatal("command failed ({}): {}".format(exc.returncode, exc.cmd))
        return 1
    except KeyboardInterrupt:
        LOG.fatal("interrupted by the user")
        return 130
    except Exception as exc:
        traceback.print_exc()
        LOG.fatal("{}: {}".format(exc.__class__.__name__, exc))
        return 1

    LOG.banner(
        [
            "RELEASE COMPLETED",
            "Version   : {}".format(version),
            "Installer : {}".format(output_exe),
            "Size      : {}".format(human_size(output_exe.stat().st_size)),
            "Duration  : {:.1f}s".format(time.time() - started_at),
        ]
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
