#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EDL Parser with Object-Oriented Design

This module provides robust EDL (Edit Decision List) parsing capabilities with:
- Object-oriented domain models (Timecode, ClipInstance, ClipGroup)
- Strategy pattern for parser selection (pycmx vs built-in)
- Comprehensive type hints and validation
- Separation of concerns between parsing, formatting, and analytics
- SOLID principles adherence

Default FPS: 23.976 (configurable via --fps argument)
"""

import re
import sys
import csv
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# Optional dependencies
try:
    import pycmx
    PYCMX_AVAILABLE = True
except ImportError:
    PYCMX_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


# ============================================================================
# Custom Exceptions
# ============================================================================

class EDLParserError(Exception):
    """Base exception for EDL parser errors"""
    pass


class TimecodeError(EDLParserError):
    """Exception raised for invalid timecode operations"""
    pass


# ============================================================================
# Domain Models
# ============================================================================

class Timecode:
    """
    Represents a timecode with frame-accurate arithmetic operations.

    Supports standard timecode format HH:MM:SS:FF and provides
    frame-based calculations for sorting and duration computations.

    Attributes:
        hours (int): Hours component (0-23)
        minutes (int): Minutes component (0-59)
        seconds (int): Seconds component (0-59)
        frames (int): Frames component (0-fps-1)
        fps (float): Frames per second rate
    """

    def __init__(self, timecode_str: str, fps: float = 23.976) -> None:
        """
        Initialize timecode from string representation.

        Args:
            timecode_str: Timecode in format "HH:MM:SS:FF" or "HH:MM:SS;FF"
            fps: Frames per second (default: 23.976)

        Raises:
            TimecodeError: If timecode format is invalid
        """
        self.fps = fps
        self._fps_int = round(fps)
        self.hours, self.minutes, self.seconds, self.frames = self._parse(timecode_str)
        self._validate()

    def _parse(self, tc_str: str) -> Tuple[int, int, int, int]:
        """
        Parse timecode string into components.

        Args:
            tc_str: Timecode string

        Returns:
            Tuple of (hours, minutes, seconds, frames)

        Raises:
            TimecodeError: If format is invalid
        """
        # Normalize semicolons to colons
        tc_str = tc_str.replace(';', ':')

        # Match timecode pattern
        match = re.match(r'(\d{1,2}):(\d{1,2}):(\d{1,2}):(\d{1,2})', tc_str)
        if not match:
            raise TimecodeError(f"Invalid timecode format: {tc_str}")

        return tuple(int(x) for x in match.groups())

    def _validate(self) -> None:
        """
        Validate timecode component ranges.

        Raises:
            TimecodeError: If any component is out of valid range
        """
        if not 0 <= self.hours <= 23:
            raise TimecodeError(f"Invalid hours: {self.hours}")
        if not 0 <= self.minutes <= 59:
            raise TimecodeError(f"Invalid minutes: {self.minutes}")
        if not 0 <= self.seconds <= 59:
            raise TimecodeError(f"Invalid seconds: {self.seconds}")
        if not 0 <= self.frames < self._fps_int:
            raise TimecodeError(f"Invalid frames: {self.frames} (fps: {self._fps_int})")

    def to_frames(self) -> int:
        """
        Convert timecode to total frame count.

        Returns:
            Total number of frames from 00:00:00:00
        """
        return (
            self.frames +
            (self.seconds * self._fps_int) +
            (self.minutes * 60 * self._fps_int) +
            (self.hours * 3600 * self._fps_int)
        )

    @classmethod
    def from_frames(cls, frames: int, fps: float = 23.976) -> 'Timecode':
        """
        Create timecode from frame count.

        Args:
            frames: Total frame count
            fps: Frames per second

        Returns:
            Timecode instance
        """
        fps_int = round(fps)

        total_seconds = frames // fps_int
        remaining_frames = frames % fps_int

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        tc_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{remaining_frames:02d}"
        return cls(tc_str, fps)

    def __str__(self) -> str:
        """Return formatted timecode string"""
        return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}:{self.frames:02d}"

    def __repr__(self) -> str:
        """Return detailed representation"""
        return f"Timecode('{str(self)}', fps={self.fps})"

    def __eq__(self, other: object) -> bool:
        """Check equality based on frame count"""
        if not isinstance(other, Timecode):
            return NotImplemented
        return self.to_frames() == other.to_frames()

    def __lt__(self, other: 'Timecode') -> bool:
        """Compare timecodes for sorting"""
        return self.to_frames() < other.to_frames()

    def __sub__(self, other: 'Timecode') -> int:
        """Calculate frame difference between timecodes"""
        return self.to_frames() - other.to_frames()


@dataclass
class ClipInstance:
    """
    Represents a single instance of a clip in the timeline.

    An instance is a contiguous segment of a clip that may appear
    multiple times in the sequence (with gaps between instances).

    Attributes:
        clip_name: Clip name from EDL metadata
        source_file: Source file name from EDL metadata
        source_in: Source in timecode
        source_out: Source out timecode
        sequence_in: Sequence in timecode (record in)
        sequence_out: Sequence out timecode (record out)
        instance_number: Instance number if clip appears multiple times
    """
    clip_name: str
    source_file: str
    source_in: Timecode
    source_out: Timecode
    sequence_in: Timecode
    sequence_out: Timecode
    instance_number: Optional[int] = None

    @property
    def display_name_clip(self) -> str:
        """Get clip name display with instance number if applicable"""
        if self.instance_number is not None:
            return f"{self.clip_name} (Instance {self.instance_number})"
        return self.clip_name

    @property
    def display_name_source(self) -> str:
        """Get source file display with instance number if applicable"""
        if self.instance_number is not None:
            return f"{self.source_file} (Instance {self.instance_number})"
        return self.source_file

    @property
    def source_duration_frames(self) -> int:
        """Calculate source duration in frames"""
        return self.source_out - self.source_in

    @property
    def sequence_duration_frames(self) -> int:
        """Calculate sequence duration in frames"""
        return self.sequence_out - self.sequence_in

    def get_instance_note(self) -> str:
        """
        Get instance notation for Notes column.

        Returns:
            Instance notation string or empty string if no instance number
        """
        if self.instance_number is not None:
            return f"Instance {self.instance_number}"
        return ""

    def validate(self) -> List[str]:
        """
        Validate timecode ranges.

        Returns:
            List of validation warnings (empty if valid)
        """
        warnings = []

        if self.source_out.to_frames() <= self.source_in.to_frames():
            warnings.append(
                f"Invalid source timecodes for {self.display_name_clip}: "
                f"{self.source_in} to {self.source_out}"
            )

        if self.sequence_out.to_frames() <= self.sequence_in.to_frames():
            warnings.append(
                f"Invalid sequence timecodes for {self.display_name_clip}: "
                f"{self.sequence_in} to {self.sequence_out}"
            )

        return warnings

    def to_dict(self, fps: float = 23.976) -> Dict[str, str]:
        """
        Convert to dictionary for output formatting.

        Args:
            fps: Frames per second for duration calculation

        Returns:
            Dictionary with formatted timecode strings including duration and notes
        """
        # Calculate duration timecode
        duration_tc = Timecode.from_frames(self.sequence_duration_frames, fps)

        return {
            'Clip Name': self.clip_name,  # Base name without instance notation
            'Source File': self.source_file,  # Base name without instance notation
            'Source In': str(self.source_in),
            'Source Out': str(self.source_out),
            'Sequence In': str(self.sequence_in),
            'Sequence Out': str(self.sequence_out),
            'Duration (TC)': str(duration_tc),
            'Duration (Frames)': str(self.sequence_duration_frames),
            'Notes': self.get_instance_note()
        }


@dataclass
class RawEdit:
    """
    Represents a raw EDL edit entry before processing.

    This is an intermediate representation used during parsing
    before gap analysis and instance creation.
    """
    clip_name: str
    source_file: str
    source_in: str
    source_out: str
    record_in: str
    record_out: str

    def to_timecodes(self, fps: float) -> Tuple[Timecode, Timecode, Timecode, Timecode]:
        """
        Convert string timecodes to Timecode objects.

        Args:
            fps: Frames per second

        Returns:
            Tuple of (source_in, source_out, record_in, record_out) as Timecode objects
        """
        return (
            Timecode(self.source_in, fps),
            Timecode(self.source_out, fps),
            Timecode(self.record_in, fps),
            Timecode(self.record_out, fps)
        )


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class ParserConfig:
    """Configuration for EDL parsing behavior"""
    fps: float = 23.976
    gap_threshold_frames: int = 1
    skip_black_edits: bool = True
    encoding: str = 'utf-8'
    encoding_errors: str = 'replace'


class OutputFormat(Enum):
    """Supported output formats"""
    TXT = 'txt'
    CSV = 'csv'
    EXCEL = 'excel'


# ============================================================================
# Clip Group Processing
# ============================================================================

class ClipGroupProcessor:
    """
    Processes groups of raw edits to identify distinct clip instances.

    Handles gap detection logic and instance numbering. This centralizes
    the duplicate logic that was previously in both parsers.
    """

    def __init__(self, config: ParserConfig):
        """
        Initialize processor with configuration.

        Args:
            config: Parser configuration
        """
        self.config = config

    def process_clip_edits(
        self,
        raw_edits: List[RawEdit]
    ) -> List[ClipInstance]:
        """
        Process raw edits for a clip to identify distinct instances.

        Sorts edits by record in timecode and detects gaps larger than
        the threshold to separate instances.

        Args:
            raw_edits: List of raw edit entries (all share same clip_name/source_file)

        Returns:
            List of ClipInstance objects with instance numbering
        """
        if not raw_edits:
            return []

        # Convert to timecodes and sort by record in
        sorted_edits = sorted(
            raw_edits,
            key=lambda e: Timecode(e.record_in, self.config.fps).to_frames()
        )

        # Group edits into instances based on gaps
        instances_raw = self._detect_instances(sorted_edits)

        # Create ClipInstance objects
        instances = []
        for idx, instance_edits in enumerate(instances_raw):
            instance_num = idx + 1 if len(instances_raw) > 1 else None
            clip_instance = self._create_clip_instance(
                instance_edits, instance_num
            )
            instances.append(clip_instance)

        return instances

    def _detect_instances(
        self,
        sorted_edits: List[RawEdit]
    ) -> List[List[RawEdit]]:
        """
        Detect instances by finding gaps in the timeline.

        Args:
            sorted_edits: Edits sorted by record in timecode

        Returns:
            List of instance groups (each group is a list of edits)
        """
        instances = []
        current_instance = [sorted_edits[0]]

        for i in range(1, len(sorted_edits)):
            current_edit = sorted_edits[i]
            previous_edit = sorted_edits[i - 1]

            # Calculate gap in frames
            current_start = Timecode(current_edit.record_in, self.config.fps)
            previous_end = Timecode(previous_edit.record_out, self.config.fps)
            gap_frames = current_start - previous_end

            if gap_frames > self.config.gap_threshold_frames:
                # Gap detected - finish current instance and start new one
                instances.append(current_instance)
                current_instance = [current_edit]
            else:
                # No gap - add to current instance
                current_instance.append(current_edit)

        # Add final instance
        if current_instance:
            instances.append(current_instance)

        return instances

    def _create_clip_instance(
        self,
        instance_edits: List[RawEdit],
        instance_num: Optional[int]
    ) -> ClipInstance:
        """
        Create ClipInstance from a group of edits.

        Takes source in/out from first/last edit in the instance,
        and record in/out from first/last edit in the instance.
        Takes clip_name and source_file from first edit (all edits share these values).

        Args:
            instance_edits: Edits belonging to this instance
            instance_num: Instance number (None if only one instance)

        Returns:
            ClipInstance object
        """
        first_edit = instance_edits[0]
        last_edit = instance_edits[-1]

        source_in = Timecode(first_edit.source_in, self.config.fps)
        source_out = Timecode(last_edit.source_out, self.config.fps)
        sequence_in = Timecode(first_edit.record_in, self.config.fps)
        sequence_out = Timecode(last_edit.record_out, self.config.fps)

        return ClipInstance(
            clip_name=first_edit.clip_name,
            source_file=first_edit.source_file,
            source_in=source_in,
            source_out=source_out,
            sequence_in=sequence_in,
            sequence_out=sequence_out,
            instance_number=instance_num
        )


# ============================================================================
# EDL Parsers
# ============================================================================

class EDLParser(ABC):
    """
    Abstract base class for EDL parsers.

    Defines the interface that all EDL parsers must implement,
    enabling the Strategy pattern for parser selection.
    """

    def __init__(self, config: ParserConfig):
        """
        Initialize parser with configuration.

        Args:
            config: Parser configuration
        """
        self.config = config
        self.processor = ClipGroupProcessor(config)

    @abstractmethod
    def parse(self, file_path: Path) -> Optional[List[ClipInstance]]:
        """
        Parse EDL file and return clip instances.

        Args:
            file_path: Path to EDL file

        Returns:
            List of ClipInstance objects, or None if parsing fails
        """
        pass

    def _validate_file(self, file_path: Path) -> bool:
        """
        Validate that file exists and is readable.

        Args:
            file_path: Path to check

        Returns:
            True if valid, False otherwise
        """
        if not file_path.exists():
            print(f"Error: File {file_path} does not exist.")
            return False
        if not file_path.is_file():
            print(f"Error: {file_path} is not a file.")
            return False
        return True


class PycmxEDLParser(EDLParser):
    """
    EDL parser using the pycmx library.

    Provides robust parsing using the industry-standard pycmx library
    with comprehensive EDL format support.
    """

    def parse(self, file_path: Path) -> Optional[List[ClipInstance]]:
        """
        Parse EDL file using pycmx library.

        Args:
            file_path: Path to EDL file

        Returns:
            List of ClipInstance objects, or None if parsing fails
        """
        if not self._validate_file(file_path):
            return None

        try:
            with open(
                file_path, 'r',
                encoding=self.config.encoding,
                errors=self.config.encoding_errors
            ) as f:
                edl = pycmx.parse_cmx3600(f)
        except Exception as e:
            print(f"Error parsing EDL with pycmx: {e}")
            return None

        # Group edits by source file (using source_file as key, not clip_name)
        clip_groups: Dict[str, List[RawEdit]] = defaultdict(list)

        for event in edl.events:
            for edit in event.edits:
                # Extract both clip_name and source_file
                clip_name = edit.clip_name or str(edit.source)
                source_file = edit.source_file or str(edit.source)

                # Skip if no identifier or black/blank
                if not source_file or (self.config.skip_black_edits and source_file == 'BL'):
                    continue

                # Create raw edit with both clip_name and source_file
                raw_edit = RawEdit(
                    clip_name=clip_name,
                    source_file=source_file,
                    source_in=str(edit.source_in),
                    source_out=str(edit.source_out),
                    record_in=str(edit.record_in),
                    record_out=str(edit.record_out)
                )
                # Group by source_file
                clip_groups[source_file].append(raw_edit)

        # Process each clip group to identify instances
        all_instances = []
        for source_file, raw_edits in clip_groups.items():
            instances = self.processor.process_clip_edits(raw_edits)
            all_instances.extend(instances)

        # Validate instances and print warnings
        for instance in all_instances:
            warnings = instance.validate()
            for warning in warnings:
                print(f"Warning: {warning}")

        return all_instances


class BuiltinEDLParser(EDLParser):
    """
    EDL parser using built-in regex-based parsing.

    Provides fallback parsing capability when pycmx is not available.
    Supports standard CMX3600 EDL format.
    """

    # Regex pattern for EDL event lines
    EVENT_PATTERN = re.compile(
        r'(\d+)\s+'                                    # Event number
        r'(\S+)\s+'                                    # Reel
        r'(\S+)\s+'                                    # Channel
        r'(\S+)(?:\s+(\S+))?\s+'                      # Transition (and optional param)
        r'(\d{1,2}:\d{1,2}:\d{1,2}[:;]\d{1,2})\s+'   # Source in
        r'(\d{1,2}:\d{1,2}:\d{1,2}[:;]\d{1,2})\s+'   # Source out
        r'(\d{1,2}:\d{1,2}:\d{1,2}[:;]\d{1,2})\s+'   # Record in
        r'(\d{1,2}:\d{1,2}:\d{1,2}[:;]\d{1,2})'      # Record out
    )

    def parse(self, file_path: Path) -> Optional[List[ClipInstance]]:
        """
        Parse EDL file using built-in parser.

        Args:
            file_path: Path to EDL file

        Returns:
            List of ClipInstance objects, or None if parsing fails
        """
        if not self._validate_file(file_path):
            return None

        try:
            with open(
                file_path, 'r',
                encoding=self.config.encoding,
                errors=self.config.encoding_errors
            ) as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Error reading EDL file: {e}")
            return None

        # Parse raw edits
        raw_edits = self._parse_raw_edits(lines)

        # Group by source_file
        clip_groups: Dict[str, List[RawEdit]] = defaultdict(list)
        for raw_edit in raw_edits:
            clip_groups[raw_edit.source_file].append(raw_edit)

        # Process each clip group to identify instances
        all_instances = []
        for source_file, raw_edits_group in clip_groups.items():
            instances = self.processor.process_clip_edits(raw_edits_group)
            all_instances.extend(instances)

        # Validate instances and print warnings
        for instance in all_instances:
            warnings = instance.validate()
            for warning in warnings:
                print(f"Warning: {warning}")

        return all_instances

    def _parse_raw_edits(
        self,
        lines: List[str]
    ) -> List[RawEdit]:
        """
        Parse raw edits from EDL file lines.

        Args:
            lines: Lines from EDL file

        Returns:
            List of RawEdit objects with clip_name and source_file populated
        """
        raw_edits = []
        current_edit_data: Optional[Dict[str, str]] = None
        current_timecodes: Optional[Tuple[str, str, str, str]] = None

        for line in lines:
            line = line.strip()

            # Skip empty lines and header lines
            if not line or line.startswith('TITLE:') or line.startswith('FCM:'):
                continue

            # Try to match event line
            event_match = self.EVENT_PATTERN.match(line)
            if event_match:
                # Save previous edit if exists
                if current_edit_data is not None and current_timecodes is not None:
                    clip_name, source_file = self._extract_clip_metadata(current_edit_data)
                    if source_file:  # Only add if we have a source_file
                        raw_edit = RawEdit(
                            clip_name=clip_name,
                            source_file=source_file,
                            source_in=current_timecodes[0],
                            source_out=current_timecodes[1],
                            record_in=current_timecodes[2],
                            record_out=current_timecodes[3]
                        )
                        raw_edits.append(raw_edit)

                # Store timecodes for new edit
                current_timecodes = (
                    event_match.group(6),  # source_in
                    event_match.group(7),  # source_out
                    event_match.group(8),  # record_in
                    event_match.group(9)   # record_out
                )
                current_edit_data = {}
                continue

            # Parse comment lines for clip metadata
            if line.startswith('*') and current_edit_data is not None:
                if "FROM CLIP NAME:" in line:
                    current_edit_data['clip_name'] = line.split("FROM CLIP NAME:")[1].strip()
                elif "SOURCE FILE:" in line:
                    current_edit_data['source_file'] = line.split("SOURCE FILE:")[1].strip()

        # Save final edit
        if current_edit_data is not None and current_timecodes is not None:
            clip_name, source_file = self._extract_clip_metadata(current_edit_data)
            if source_file:
                raw_edit = RawEdit(
                    clip_name=clip_name,
                    source_file=source_file,
                    source_in=current_timecodes[0],
                    source_out=current_timecodes[1],
                    record_in=current_timecodes[2],
                    record_out=current_timecodes[3]
                )
                raw_edits.append(raw_edit)

        return raw_edits

    def _extract_clip_metadata(self, metadata: Dict[str, str]) -> Tuple[str, str]:
        """
        Extract clip_name and source_file from metadata.

        Args:
            metadata: Dictionary of clip metadata

        Returns:
            Tuple of (clip_name, source_file)
        """
        # Get source_file and clip_name, use source_file as fallback for clip_name if needed
        source_file = metadata.get('source_file', '')
        clip_name = metadata.get('clip_name', source_file)

        # If still empty, use a placeholder
        if not source_file:
            source_file = clip_name if clip_name else 'UNKNOWN'
        if not clip_name:
            clip_name = source_file

        return (clip_name, source_file)


class EDLParserFactory:
    """
    Factory for creating appropriate EDL parser based on availability.

    Implements Strategy pattern by selecting parser at runtime.
    """

    @staticmethod
    def create_parser(config: ParserConfig) -> EDLParser:
        """
        Create appropriate parser based on library availability.

        Args:
            config: Parser configuration

        Returns:
            EDLParser instance (pycmx if available, otherwise built-in)
        """
        if PYCMX_AVAILABLE:
            print("Using pycmx parser...")
            return PycmxEDLParser(config)
        else:
            print("pycmx not available. Using built-in parser...")
            print("For better EDL parsing, install pycmx: pip install pycmx")
            return BuiltinEDLParser(config)

    @staticmethod
    def create_parser_with_fallback(config: ParserConfig, file_path: Path) -> Optional[List[ClipInstance]]:
        """
        Try pycmx parser first, fall back to built-in if it fails.

        Args:
            config: Parser configuration
            file_path: Path to EDL file

        Returns:
            List of ClipInstance objects, or None if all parsers fail
        """
        if PYCMX_AVAILABLE:
            print("Using pycmx parser...")
            pycmx_parser = PycmxEDLParser(config)
            result = pycmx_parser.parse(file_path)
            if result is not None:
                return result
            print("pycmx parser failed, falling back to built-in parser...")

        print("Using built-in parser...")
        if not PYCMX_AVAILABLE:
            print("For better EDL parsing, install pycmx: pip install pycmx")

        builtin_parser = BuiltinEDLParser(config)
        return builtin_parser.parse(file_path)


# ============================================================================
# Output Formatters
# ============================================================================

class OutputFormatter(ABC):
    """
    Abstract base class for output formatters.

    Defines interface for formatting and writing clip data to various formats.
    """

    @abstractmethod
    def format_and_write(
        self,
        instances: List[ClipInstance],
        output_path: Path
    ) -> bool:
        """
        Format clip instances and write to file.

        Args:
            instances: List of clip instances to format
            output_path: Path for output file

        Returns:
            True if successful, False otherwise
        """
        pass

    @staticmethod
    def _sort_instances(instances: List[ClipInstance]) -> List[ClipInstance]:
        """
        Sort instances by sequence in timecode.

        Args:
            instances: List to sort

        Returns:
            Sorted list
        """
        return sorted(instances, key=lambda inst: inst.sequence_in.to_frames())


class TextFormatter(OutputFormatter):
    """Formats clip data as aligned text output"""

    COLUMN_WIDTHS = {
        'Clip Name': 30,
        'Source File': 30,
        'Source In': 13,
        'Source Out': 13,
        'Sequence In': 13,
        'Sequence Out': 13,
        'Duration (TC)': 13,
        'Duration (Frames)': 16,
        'Notes': 15
    }

    def __init__(self, fps: float = 23.976):
        """
        Initialize Text formatter with FPS for duration calculation.

        Args:
            fps: Frames per second (default: 23.976)
        """
        self.fps = fps

    def format_and_write(
        self,
        instances: List[ClipInstance],
        output_path: Path
    ) -> bool:
        """Format and write text output"""
        if not instances:
            print("No clips found.")
            return False

        sorted_instances = self._sort_instances(instances)
        lines = self._format_lines(sorted_instances)

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            print(f"Text output saved to: {output_path}")
            return True
        except Exception as e:
            print(f"Error writing text file: {e}")
            return False

    def _format_lines(self, instances: List[ClipInstance]) -> List[str]:
        """Format instances as text lines"""
        lines = []
        columns = list(self.COLUMN_WIDTHS.keys())

        # Header
        header = ''.join(
            col.ljust(self.COLUMN_WIDTHS[col])
            for col in columns
        )
        lines.append(header)
        lines.append('-' * sum(self.COLUMN_WIDTHS.values()))

        # Data rows
        for instance in instances:
            data = instance.to_dict(fps=self.fps)
            line = ''
            for col in columns:
                value = data[col]
                max_width = self.COLUMN_WIDTHS[col]
                if len(value) > max_width - 2:
                    value = value[:max_width - 4] + '..'
                line += value.ljust(max_width)
            lines.append(line)
            lines.append('-' * sum(self.COLUMN_WIDTHS.values()))

        return lines


class CSVFormatter(OutputFormatter):
    """Formats clip data as CSV output"""

    def __init__(self, fps: float = 23.976):
        """
        Initialize CSV formatter with FPS for duration calculation.

        Args:
            fps: Frames per second (default: 23.976)
        """
        self.fps = fps

    def format_and_write(
        self,
        instances: List[ClipInstance],
        output_path: Path
    ) -> bool:
        """Format and write CSV output"""
        if not instances:
            print("No clips found.")
            return False

        sorted_instances = self._sort_instances(instances)

        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'Clip Name',
                    'Source File',
                    'Source In',
                    'Source Out',
                    'Sequence In',
                    'Sequence Out',
                    'Duration (TC)',
                    'Duration (Frames)',
                    'Notes'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for instance in sorted_instances:
                    writer.writerow(instance.to_dict(fps=self.fps))

            print(f"CSV output saved to: {output_path}")
            return True
        except Exception as e:
            print(f"Error writing CSV file: {e}")
            return False


class ExcelFormatter(OutputFormatter):
    """Formats clip data as Excel output (requires pandas)"""

    def __init__(self, fps: float = 23.976):
        """
        Initialize Excel formatter with FPS for statistics calculations.

        Args:
            fps: Frames per second (default: 23.976)
        """
        self.fps = fps

    def format_and_write(
        self,
        instances: List[ClipInstance],
        output_path: Path
    ) -> bool:
        """Format and write Excel output with Statistics sheet"""
        if not PANDAS_AVAILABLE:
            print("Warning: pandas is not installed. Excel output is not available.")
            print("Install pandas with: pip install pandas openpyxl")
            return False

        if not instances:
            print("No clips found.")
            return False

        sorted_instances = self._sort_instances(instances)
        # Pass fps to to_dict() for duration calculation
        data = [inst.to_dict(fps=self.fps) for inst in sorted_instances]

        try:
            from openpyxl.worksheet.table import Table, TableStyleInfo

            df = pd.DataFrame(data)

            # Calculate music statistics
            analyzer = EDLAnalyzer(self.fps)
            music_stats = analyzer.calculate_music_stats(sorted_instances)

            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Write EDL Clips sheet
                df.to_excel(writer, index=False, sheet_name='EDL Clips')

                # Auto-adjust column widths for EDL Clips sheet
                worksheet = writer.sheets['EDL Clips']
                for i, col in enumerate(df.columns):
                    max_width = max(
                        df[col].astype(str).map(len).max(),
                        len(col)
                    ) + 2
                    worksheet.column_dimensions[chr(65 + i)].width = min(max_width, 50)

                # Format EDL Clips sheet as table
                edl_table_ref = f"A1:{chr(64 + len(df.columns))}{len(df) + 1}"
                edl_table = Table(displayName="EDLClipsTable", ref=edl_table_ref)
                edl_style = TableStyleInfo(
                    name="TableStyleLight1",
                    showFirstColumn=False,
                    showLastColumn=False,
                    showRowStripes=True,
                    showColumnStripes=False
                )
                edl_table.tableStyleInfo = edl_style
                worksheet.add_table(edl_table)

                # Write Statistics sheet
                if music_stats:
                    stats_data = [
                        {
                            'Music Track': ms.source_file,
                            'Clip Name': ms.clip_name,
                            'Instances': ms.instance_count,
                            'First Appearance': ms.first_appearance_tc,
                            'Duration (TC)': ms.total_duration_timecode,
                            'Duration (Frames)': ms.total_duration_frames,
                            'Percentage': f"{ms.percentage:.2f}%"
                        }
                        for ms in music_stats
                    ]
                    stats_df = pd.DataFrame(stats_data)
                    stats_df.to_excel(writer, index=False, sheet_name='Statistics')

                    # Auto-adjust column widths for Statistics sheet
                    stats_worksheet = writer.sheets['Statistics']
                    for i, col in enumerate(stats_df.columns):
                        max_width = max(
                            stats_df[col].astype(str).map(len).max(),
                            len(col)
                        ) + 2
                        stats_worksheet.column_dimensions[chr(65 + i)].width = min(max_width, 50)

                    # Format Statistics sheet as table
                    stats_table_ref = f"A1:{chr(64 + len(stats_df.columns))}{len(stats_df) + 1}"
                    stats_table = Table(displayName="StatisticsTable", ref=stats_table_ref)
                    stats_style = TableStyleInfo(
                        name="TableStyleLight1",
                        showFirstColumn=False,
                        showLastColumn=False,
                        showRowStripes=True,
                        showColumnStripes=False
                    )
                    stats_table.tableStyleInfo = stats_style
                    stats_worksheet.add_table(stats_table)

            print(f"Excel output saved to: {output_path}")
            return True
        except Exception as e:
            print(f"Error writing Excel file: {e}")
            return False


class OutputFormatterFactory:
    """Factory for creating output formatters"""

    @staticmethod
    def create_formatter(output_format: OutputFormat, fps: float = 23.976) -> OutputFormatter:
        """
        Create formatter for specified format.

        Args:
            output_format: Desired output format
            fps: Frames per second (for duration calculations and statistics)

        Returns:
            Appropriate OutputFormatter instance
        """
        if output_format == OutputFormat.EXCEL:
            return ExcelFormatter(fps=fps)
        elif output_format == OutputFormat.TXT:
            return TextFormatter(fps=fps)
        elif output_format == OutputFormat.CSV:
            return CSVFormatter(fps=fps)
        else:
            raise ValueError(f"Unknown output format: {output_format}")


# ============================================================================
# Analytics
# ============================================================================

@dataclass
class ClipStatistics:
    """Statistics for a single clip"""
    name: str
    duration_timecode: str
    duration_frames: int
    percentage: float


@dataclass
class MusicTrackStatistics:
    """Statistics for a unique music track (aggregated across instances)"""
    source_file: str
    clip_name: str
    instance_count: int
    total_duration_frames: int
    total_duration_timecode: str
    first_appearance_tc: str
    first_appearance_frames: int
    percentage: float = 0.0


@dataclass
class EDLStatistics:
    """Overall EDL statistics"""
    total_clips: int
    total_duration_frames: int
    total_duration_timecode: str
    longest_clip: Optional[ClipStatistics]
    shortest_clip: Optional[ClipStatistics]
    clips_by_percentage: List[ClipStatistics] = field(default_factory=list)


class EDLAnalyzer:
    """
    Analyzes parsed EDL data to generate statistics and reports.

    Provides analytics on clip usage, durations, and percentages.
    """

    def __init__(self, fps: float = 23.976):
        """
        Initialize analyzer.

        Args:
            fps: Frames per second for duration calculations
        """
        self.fps = fps

    def analyze(self, instances: List[ClipInstance]) -> EDLStatistics:
        """
        Analyze clip instances to generate statistics.

        Args:
            instances: List of clip instances to analyze

        Returns:
            EDLStatistics object with comprehensive analytics
        """
        if not instances:
            return EDLStatistics(
                total_clips=0,
                total_duration_frames=0,
                total_duration_timecode="00:00:00:00",
                longest_clip=None,
                shortest_clip=None
            )

        # Calculate clip statistics
        clip_stats_list = [
            self._calculate_clip_stats(inst) for inst in instances
        ]

        # Calculate totals
        total_frames = sum(cs.duration_frames for cs in clip_stats_list)
        total_tc = Timecode.from_frames(total_frames, self.fps)

        # Calculate percentages
        for clip_stat in clip_stats_list:
            clip_stat.percentage = (
                (clip_stat.duration_frames / total_frames * 100)
                if total_frames > 0 else 0
            )

        # Sort by percentage descending
        sorted_by_percentage = sorted(
            clip_stats_list,
            key=lambda cs: cs.percentage,
            reverse=True
        )

        # Find longest and shortest
        longest = max(clip_stats_list, key=lambda cs: cs.duration_frames)
        shortest = min(clip_stats_list, key=lambda cs: cs.duration_frames)

        return EDLStatistics(
            total_clips=len(instances),
            total_duration_frames=total_frames,
            total_duration_timecode=str(total_tc),
            longest_clip=longest,
            shortest_clip=shortest,
            clips_by_percentage=sorted_by_percentage
        )

    def _calculate_clip_stats(self, instance: ClipInstance) -> ClipStatistics:
        """Calculate statistics for a single clip instance"""
        duration_frames = instance.sequence_duration_frames
        duration_tc = Timecode.from_frames(duration_frames, self.fps)

        # Use source_file as the primary name for analytics
        name = instance.display_name_source

        return ClipStatistics(
            name=name,
            duration_timecode=str(duration_tc),
            duration_frames=duration_frames,
            percentage=0.0  # Will be calculated later
        )

    def calculate_music_stats(self, instances: List[ClipInstance]) -> List[MusicTrackStatistics]:
        """
        Calculate statistics for unique music tracks (aggregated across instances).

        Args:
            instances: List of clip instances to analyze

        Returns:
            List of MusicTrackStatistics sorted by first appearance (descending)
        """
        if not instances:
            return []

        # Group instances by source_file (without instance numbers)
        track_groups: Dict[str, List[ClipInstance]] = defaultdict(list)

        for instance in instances:
            # Extract base source_file name (remove " (Instance N)" suffix)
            base_source = instance.source_file
            track_groups[base_source].append(instance)

        # Calculate statistics for each unique track
        track_stats_list = []
        total_music_frames = 0

        for source_file, track_instances in track_groups.items():
            # Sum durations across all instances
            total_duration = sum(inst.sequence_duration_frames for inst in track_instances)
            total_music_frames += total_duration

            # Get clip_name from first instance (all should have same clip_name for a source_file)
            clip_name = track_instances[0].clip_name

            # Find first appearance (earliest sequence_in across all instances)
            first_appearance_frames = min(inst.sequence_in.to_frames() for inst in track_instances)
            first_appearance_tc = Timecode.from_frames(first_appearance_frames, self.fps)

            track_stat = MusicTrackStatistics(
                source_file=source_file,
                clip_name=clip_name,
                instance_count=len(track_instances),
                total_duration_frames=total_duration,
                total_duration_timecode=str(Timecode.from_frames(total_duration, self.fps)),
                first_appearance_tc=str(first_appearance_tc),
                first_appearance_frames=first_appearance_frames,
                percentage=0.0  # Will be calculated next
            )
            track_stats_list.append(track_stat)

        # Calculate percentages
        for track_stat in track_stats_list:
            track_stat.percentage = (
                (track_stat.total_duration_frames / total_music_frames * 100)
                if total_music_frames > 0 else 0
            )

        # Sort by first appearance descending (earliest use first, then later uses)
        track_stats_list.sort(key=lambda ts: ts.first_appearance_frames, reverse=True)

        return track_stats_list


class AnalyticsReportGenerator:
    """Generates formatted analytics reports"""

    def generate_text_report(
        self,
        stats: EDLStatistics,
        output_path: Path
    ) -> bool:
        """
        Generate text analytics report.

        Args:
            stats: Statistics to report
            output_path: Path for output file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("EDL ANALYTICS REPORT\n")
                f.write("===================\n\n")

                # Basic stats
                f.write(f"Total number of unique clips: {stats.total_clips}\n")
                f.write(f"Total sequence duration: {stats.total_duration_timecode}\n\n")

                # Longest/shortest clips
                if stats.longest_clip:
                    f.write(f"Longest clip: {stats.longest_clip.name}\n")
                    f.write(
                        f"  Duration: {stats.longest_clip.duration_timecode} "
                        f"({stats.longest_clip.duration_frames} frames)\n\n"
                    )

                if stats.shortest_clip:
                    f.write(f"Shortest clip: {stats.shortest_clip.name}\n")
                    f.write(
                        f"  Duration: {stats.shortest_clip.duration_timecode} "
                        f"({stats.shortest_clip.duration_frames} frames)\n\n"
                    )

                # Clips by percentage
                f.write("Clips by percentage of total time:\n")
                f.write("---------------------------------\n")
                for i, clip_stat in enumerate(stats.clips_by_percentage, 1):
                    f.write(f"{i}. {clip_stat.name}\n")
                    f.write(
                        f"   Duration: {clip_stat.duration_timecode} "
                        f"({clip_stat.duration_frames} frames)\n"
                    )
                    f.write(f"   Percentage: {clip_stat.percentage:.2f}%\n\n")

            print(f"Analytics report saved to: {output_path}")
            return True
        except Exception as e:
            print(f"Error generating analytics report: {e}")
            return False

    def generate_excel_report(
        self,
        stats: EDLStatistics,
        output_path: Path
    ) -> bool:
        """
        Generate Excel analytics report.

        Args:
            stats: Statistics to report
            output_path: Path for output file

        Returns:
            True if successful, False otherwise
        """
        if not PANDAS_AVAILABLE:
            print("Pandas not available. Excel analytics report will not be generated.")
            print("Install pandas with: pip install pandas openpyxl")
            return False

        try:
            # Create summary data
            summary_data = {
                'Metric': [
                    'Total Clips',
                    'Total Duration (frames)',
                    'Total Duration',
                    'Longest Clip',
                    'Longest Clip Duration',
                    'Shortest Clip',
                    'Shortest Clip Duration'
                ],
                'Value': [
                    stats.total_clips,
                    stats.total_duration_frames,
                    stats.total_duration_timecode,
                    stats.longest_clip.name if stats.longest_clip else 'N/A',
                    stats.longest_clip.duration_timecode if stats.longest_clip else 'N/A',
                    stats.shortest_clip.name if stats.shortest_clip else 'N/A',
                    stats.shortest_clip.duration_timecode if stats.shortest_clip else 'N/A'
                ]
            }
            summary_df = pd.DataFrame(summary_data)

            # Create percentage data
            percentage_data = [
                {
                    'Clip Name': cs.name[:30] + '...' if len(cs.name) > 30 else cs.name,
                    'Duration': cs.duration_frames,
                    'Duration (TC)': cs.duration_timecode,
                    'Percentage': f"{cs.percentage:.2f}%"
                }
                for cs in stats.clips_by_percentage
            ]
            percentage_df = pd.DataFrame(percentage_data)

            # Write to Excel
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                percentage_df.to_excel(writer, sheet_name='Clip Percentages', index=False)

                # Adjust column widths
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width

            print(f"Excel analytics report saved to: {output_path}")
            return True
        except Exception as e:
            print(f"Error generating Excel analytics report: {e}")
            return False


# ============================================================================
# File Management
# ============================================================================

class FileWriteManager:
    """
    Manages file writing with overwrite protection.

    Centralizes file existence checking and overwrite logic.
    """

    def __init__(self, allow_overwrite: bool = True):
        """
        Initialize file write manager.

        Args:
            allow_overwrite: Whether to allow overwriting existing files
        """
        self.allow_overwrite = allow_overwrite

    def should_write(self, file_path: Path) -> bool:
        """
        Check if file should be written based on overwrite settings.

        Args:
            file_path: Path to check

        Returns:
            True if file should be written, False otherwise
        """
        if not self.allow_overwrite and file_path.exists():
            print(
                f"File {file_path} already exists. Skipping "
                "(use without --no-overwrite to overwrite)."
            )
            return False
        return True


# ============================================================================
# Main Application
# ============================================================================

class EDLParserApplication:
    """
    Main application class coordinating EDL parsing workflow.

    Orchestrates parsing, formatting, analytics, and file operations.
    """

    def __init__(
        self,
        edl_file: Path,
        output_formats: List[OutputFormat],
        fps: float = 23.976,
        generate_analytics: bool = False,
        allow_overwrite: bool = True
    ):
        """
        Initialize application.

        Args:
            edl_file: Path to EDL file
            output_formats: List of desired output formats
            fps: Frames per second
            generate_analytics: Whether to generate analytics reports
            allow_overwrite: Whether to allow overwriting existing files
        """
        self.edl_file = edl_file
        self.output_formats = output_formats
        self.fps = fps
        self.generate_analytics = generate_analytics

        self.config = ParserConfig(fps=fps)
        self.file_manager = FileWriteManager(allow_overwrite)
        self.base_path = edl_file.parent / edl_file.stem

    def run(self) -> bool:
        """
        Run the full EDL parsing and output workflow.

        Returns:
            True if successful, False otherwise
        """
        print(f"Parsing EDL file: {self.edl_file}")
        print(f"FPS: {self.fps}")

        # Parse EDL file
        instances = self._parse_edl()
        if not instances:
            print("No clips found or parsing failed.")
            return False

        print(f"Successfully parsed {len(instances)} clip instances.")

        # Generate outputs
        self._generate_outputs(instances)

        # Generate analytics if requested
        if self.generate_analytics:
            self._generate_analytics(instances)

        print("\nAll processing complete!")
        return True

    def _parse_edl(self) -> Optional[List[ClipInstance]]:
        """Parse EDL file using appropriate parser"""
        return EDLParserFactory.create_parser_with_fallback(
            self.config,
            self.edl_file
        )

    def _generate_outputs(self, instances: List[ClipInstance]) -> None:
        """
        Generate all requested output formats.

        Args:
            instances: Parsed clip instances
        """
        for output_format in self.output_formats:
            output_path = self._get_output_path(output_format)

            if not self.file_manager.should_write(output_path):
                continue

            formatter = OutputFormatterFactory.create_formatter(output_format, fps=self.fps)
            success = formatter.format_and_write(instances, output_path)

            # Print to console for text format
            if output_format == OutputFormat.TXT and success:
                self._print_text_output(output_path)

    def _generate_analytics(self, instances: List[ClipInstance]) -> None:
        """
        Generate analytics reports.

        Args:
            instances: Parsed clip instances
        """
        print("\nGenerating analytics reports...")

        analyzer = EDLAnalyzer(self.fps)
        stats = analyzer.analyze(instances)

        report_generator = AnalyticsReportGenerator()

        # Text report
        txt_analytics_path = Path(f"{self.base_path}_analytics.txt")
        if self.file_manager.should_write(txt_analytics_path):
            report_generator.generate_text_report(stats, txt_analytics_path)

        # Excel report
        if PANDAS_AVAILABLE:
            excel_analytics_path = Path(f"{self.base_path}_analytics.xlsx")
            if self.file_manager.should_write(excel_analytics_path):
                report_generator.generate_excel_report(stats, excel_analytics_path)
        else:
            print("Pandas not available. Excel analytics report will not be generated.")

    def _get_output_path(self, output_format: OutputFormat) -> Path:
        """Get output file path for format"""
        extensions = {
            OutputFormat.TXT: '.txt',
            OutputFormat.CSV: '.csv',
            OutputFormat.EXCEL: '.xlsx'
        }
        return Path(f"{self.base_path}_parsed{extensions[output_format]}")

    def _print_text_output(self, output_path: Path) -> None:
        """Print text output to console"""
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                print("\nOutput:")
                print(f.read())
        except Exception as e:
            print(f"Error reading text output: {e}")


# ============================================================================
# CLI Entry Point
# ============================================================================

def main() -> None:
    """Command-line interface entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='EDL Parser with object-oriented design and pycmx support',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s myfile.edl
  %(prog)s myfile.edl --format csv --fps 24
  %(prog)s myfile.edl --format all --analytics
  %(prog)s myfile.edl --format excel --no-overwrite
        """
    )

    parser.add_argument(
        'edl_file',
        type=Path,
        help='Path to the EDL file'
    )
    parser.add_argument(
        '--format',
        choices=['txt', 'csv', 'excel', 'all'],
        default='txt',
        help='Output format (default: txt)'
    )
    parser.add_argument(
        '--fps',
        type=float,
        default=23.976,
        help='Frames per second (default: 23.976)'
    )
    parser.add_argument(
        '--analytics',
        action='store_true',
        help='Generate analytics report'
    )
    parser.add_argument(
        '--no-overwrite',
        action='store_true',
        help='Do not overwrite existing output files'
    )

    args = parser.parse_args()

    # Determine output formats
    if args.format == 'all':
        output_formats = [OutputFormat.TXT, OutputFormat.CSV, OutputFormat.EXCEL]
    else:
        output_formats = [OutputFormat(args.format)]

    # Create and run application
    app = EDLParserApplication(
        edl_file=args.edl_file,
        output_formats=output_formats,
        fps=args.fps,
        generate_analytics=args.analytics,
        allow_overwrite=not args.no_overwrite
    )

    success = app.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
