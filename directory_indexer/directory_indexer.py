#!/usr/bin/env python3
"""
Directory Structure Archiver - Refactored Version

Generates an interactive HTML file showing all files in a directory tree
with names, full paths, sizes, and extensions.

This is the refactored entry point that uses the modular architecture from src/.
"""

import sys
import argparse
from pathlib import Path

# Import refactored components
from src.config.settings import DatabaseConfig
from src.core.scanner import DirectoryScanner
from src.core.database import DatabaseManager
from src.core.tree_builder import DirectoryTreeBuilder
from src.utils.formatting import SizeFormatter
from src.utils.path_resolver import OutputPathResolver
from src.generators.json_generator import JsonGenerator
from src.generators.db_generator import DbGenerator
from src.generators.script_generators import (
    generate_server_script,
    generate_launcher_scripts
)


def run_json_mode(scan_result, root_path: str, output_file: str, force_json: bool = False):
    """
    Generate HTML file with embedded JSON data.

    Args:
        scan_result: ScanResult object from directory scan
        root_path: Root directory that was scanned
        output_file: Path where HTML file will be written
        force_json: Whether JSON mode was explicitly requested
    """
    from src.models import FileInfo

    file_count = scan_result.file_count

    print("\n" + "=" * 60)
    print("JSON MODE")
    print("=" * 60)
    print(f"  Files to archive: {file_count:,}")
    print(f"  Mode: Embedded JSON in HTML")
    print("=" * 60)

    # Warn about large datasets in JSON mode
    if file_count > DatabaseConfig.FILE_COUNT_THRESHOLD and force_json:
        print("\n" + "!" * 60)
        print("WARNING: Large dataset in JSON mode!")
        print("\n  The HTML file will be very large and browsers may")
        print("  struggle to load it due to memory constraints.")
        print("\n  Recommendation:")
        print("  - Remove --json flag to use database mode automatically")
        print("  - Or use --extdb flag explicitly")
        print("!" * 60)

        response = input("\nContinue anyway? (y/n): ").strip().lower()
        if response != 'y':
            print("Aborted.")
            sys.exit(0)

    # Convert FileInfo objects to dicts for tree_builder
    files_as_dicts = [f.to_dict() if isinstance(f, FileInfo) else f for f in scan_result.files_data]

    # Build directory tree for browse mode
    print(f"\nBuilding directory tree...")
    tree_builder = DirectoryTreeBuilder(Path(root_path))
    directory_tree = tree_builder.build_tree(files_as_dicts)

    # Generate HTML with embedded JSON (generator handles both FileInfo and dicts)
    print(f"Generating HTML archive...")
    generator = JsonGenerator()
    generator.generate(
        scan_result.files_data,
        root_path,
        scan_result.total_size,
        scan_result.extension_stats,
        output_file,
        directory_tree=directory_tree
    )

    print(f"\n{'=' * 60}")
    print(f"Summary:")
    print(f"  Files archived: {file_count:,}")
    print(f"  Total size: {SizeFormatter.format_size(scan_result.total_size)}")
    print(f"  Output file: {output_file}")
    print(f"{'=' * 60}\n")


def run_database_mode(scan_result, root_path: str, output_file: str, forced: bool = False):
    """
    Generate HTML viewer with external SQLite database.

    Args:
        scan_result: ScanResult object from directory scan
        root_path: Root directory that was scanned
        output_file: Path where HTML file will be written
        forced: Whether database mode was explicitly requested
    """
    from src.models import FileInfo

    file_count = scan_result.file_count

    print("\n" + "=" * 60)
    print("DATABASE MODE")
    print("=" * 60)
    print(f"  Files to archive: {file_count:,}")
    print(f"  Mode: External SQLite database")
    reason = "--extdb flag specified" if forced else f"File count ({file_count:,}) > 200,000"
    print(f"  Reason: {reason}")
    print("=" * 60)

    # Create folder structure
    output_path_obj = Path(output_file)
    base_output_dir = output_path_obj.parent / output_path_obj.stem

    # Create subdirectories
    data_dir = base_output_dir / 'data'
    macos_dir = base_output_dir / 'macOS'
    windows_dir = base_output_dir / 'Windows'
    linux_dir = base_output_dir / 'Linux'

    data_dir.mkdir(parents=True, exist_ok=True)
    macos_dir.mkdir(parents=True, exist_ok=True)
    windows_dir.mkdir(parents=True, exist_ok=True)
    linux_dir.mkdir(parents=True, exist_ok=True)

    # Update file paths to use data directory
    html_basename = output_path_obj.name
    html_file = data_dir / html_basename
    db_filename = str(data_dir / (output_path_obj.stem + '.db'))

    # Convert FileInfo objects to dicts for database_manager
    files_as_dicts = [f.to_dict() if isinstance(f, FileInfo) else f for f in scan_result.files_data]

    # Create database using DatabaseManager
    db_manager = DatabaseManager(db_filename)
    db_size = db_manager.create_database(
        files_as_dicts,
        scan_result.total_size,
        scan_result.extension_stats,
        Path(root_path)
    )

    # Generate HTML viewer
    print(f"\nGenerating HTML viewer...")
    generator = DbGenerator()
    generator.generate(
        Path(db_filename).name,
        root_path,
        scan_result.total_size,
        scan_result.extension_stats,
        files_as_dicts,
        str(html_file),
        db_size
    )

    # Generate server script (in data folder)
    server_script = generate_server_script(str(data_dir), html_basename)
    print(f"✓ Server script created: {server_script}")

    # Generate launcher scripts (in platform folders)
    macos_launcher, windows_launcher, linux_launcher = generate_launcher_scripts(
        str(macos_dir), str(windows_dir), str(linux_dir), html_basename
    )
    print(f"✓ macOS launcher created: {macos_launcher}")
    print(f"✓ Windows launcher created: {windows_launcher}")
    print(f"✓ Linux launcher created: {linux_launcher}")

    print(f"\n{'=' * 60}")
    print(f"Summary:")
    print(f"  Files archived: {file_count:,}")
    print(f"  Total size: {SizeFormatter.format_size(scan_result.total_size)}")
    print(f"  Output folder: {base_output_dir}")
    print(f"    data/")
    print(f"      {html_basename}")
    print(f"      {Path(db_filename).name} ({SizeFormatter.format_size(db_size)})")
    print(f"      serve.py")
    print(f"      lib/")
    print(f"        sql-wasm.js")
    print(f"        sql-wasm.wasm")
    print(f"    macOS/")
    print(f"      start-viewer.command")
    print(f"    Windows/")
    print(f"      start-viewer.bat")
    print(f"    Linux/")
    print(f"      start-viewer.sh")
    print(f"\nQuick start:")
    print(f"  macOS:   Double-click macOS/start-viewer.command")
    print(f"  Windows: Double-click Windows/start-viewer.bat")
    print(f"  Linux:   bash Linux/start-viewer.sh")
    print(f"  Manual:  cd data && python serve.py")
    print(f"{'=' * 60}\n")


def main():
    """Main entry point for the directory indexer."""
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Directory Structure Archiver - Generate interactive HTML archives of directory contents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python directory_indexer.py /Volumes/MyDrive
    → Creates /Volumes/MyDrive/index_MyDrive_YYYYMMDD_HHMMSS/...

  python directory_indexer.py /Volumes/MyDrive archive.html
    → Creates /Volumes/MyDrive/archive/archive.html

  python directory_indexer.py /Volumes/MyDrive /tmp/output.html
    → Creates /tmp/output.html (absolute file path)

  python directory_indexer.py /Volumes/MyDrive /tmp
    → Creates /tmp/index_MyDrive_YYYYMMDD_HHMMSS.html (absolute dir path)

  python directory_indexer.py /Volumes/MyDrive --extdb
    → Forces database mode for any size

Output Location:
  - Without output path: Creates subfolder in target directory
  - With relative path: Creates subfolder named after file in target directory
  - With absolute directory path: Generates file in that directory
  - With absolute file path: Uses exact path specified

Modes:
  - JSON mode (default for <200k files): Embeds data in HTML file
  - Database mode (auto for 200k+ files): Creates SQLite database + HTML viewer
    * Generates 3 files: .html, .db, and serve.py
    * Requires running HTTP server: python serve.py
    * Much more efficient for large datasets
  - Use --extdb to force database mode
  - Use --json to force JSON mode (not recommended for large datasets)
        """
    )

    parser.add_argument('directory', help='Directory path to archive')
    parser.add_argument('output', nargs='?', help='Output HTML file path (optional)')
    parser.add_argument('--extdb', action='store_true',
                       help='Force external database mode (creates .db + .html files)')
    parser.add_argument('--json', action='store_true',
                       help='Force JSON mode (embed data in HTML file)')

    # Parse arguments
    args = parser.parse_args()

    root_path = args.directory

    # Validate directory
    if not Path(root_path).exists():
        print(f"Error: Directory '{root_path}' does not exist.")
        sys.exit(1)

    if not Path(root_path).is_dir():
        print(f"Error: '{root_path}' is not a directory.")
        sys.exit(1)

    # Determine output file
    resolver = OutputPathResolver(root_path, args.output)
    output_file = resolver.resolve()

    print("=" * 60)
    print("Directory Structure Archiver")
    print("=" * 60)
    print(f"Output location: {output_file}")
    print("=" * 60)

    # Scan directory using refactored DirectoryScanner
    scanner = DirectoryScanner(root_path)
    try:
        scan_result = scanner.scan()
    except (FileNotFoundError, NotADirectoryError) as e:
        print(f"Error: {e}")
        sys.exit(1)

    if scan_result.file_count == 0:
        print("\nNo files found in the directory.")
        sys.exit(0)

    # Determine mode: database vs JSON
    use_database = args.extdb or (
        scan_result.file_count > DatabaseConfig.FILE_COUNT_THRESHOLD and not args.json
    )

    if use_database:
        # Database mode
        if args.json:
            print("\nWarning: --json flag ignored due to large dataset size")

        run_database_mode(scan_result, root_path, output_file, forced=args.extdb)
    else:
        # JSON mode
        run_json_mode(scan_result, root_path, output_file, force_json=args.json)


if __name__ == "__main__":
    main()
