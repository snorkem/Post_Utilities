#!/usr/bin/env python3
"""
Lower Thirds Generator - Refactored CLI

A utility script to generate lower third graphics from Excel or CSV data.
This script is designed for visual effects and graphics workflows in film and TV.

EXCEL/CSV FORMAT:
Required columns (in this order):
1. Main Text      - The primary text (typically a name)
2. Secondary Text - The secondary text (typically a title or description)
3. Justification  - Text position: "Left", "Right", "Center", "Lower Left", etc.
4. Main Font      - Font name or path to font file for the main text

Optional columns:
- Secondary Font, File Name, Main Font Size, Secondary Font Size
- Padding, Main Color, Secondary Color, Background Color, Bar Color
- Text Outline, Text Shadow, Shadow Color

USAGE:
    python l3rds_from_excel.py input.xlsx output_folder [options]

For full help:
    python l3rds_from_excel.py --help
"""

import sys
from pathlib import Path

from l3rds.config.parser import ConfigParser
from l3rds.config.validator import ConfigValidator
from l3rds.data.loader import ExcelLoader
from l3rds.data.extractor import ExcelRowExtractor
from l3rds.data.subtitle_loader import SubtitleLoader
from l3rds.data.subtitle_extractor import SubtitleRowExtractor
from l3rds.rendering.generator import LowerThirdGenerator
from l3rds.io.image_saver import ImageSaver
from l3rds.io.preview import PreviewManager
from l3rds.io.template_generator import TemplateGenerator
from l3rds.utils.logger import setup_logging, get_logger
from l3rds.utils.exceptions import L3rdsException


def main() -> int:
    """Main entry point for the CLI.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Print banner
    print("=" * 80)
    print("Lower Thirds Generator v2.0 - Refactored Edition".center(80))
    print("=" * 80)
    print()

    try:
        # Parse arguments
        parser = ConfigParser()
        config, extra_args = parser.parse_args()

        # Handle template generation mode
        if extra_args["generate_template"]:
            output_file = extra_args["generate_template"]

            # Ensure .xlsx extension
            if not output_file.endswith('.xlsx'):
                output_file += '.xlsx'

            print(f"Generating Excel template: {output_file}")
            TemplateGenerator.create_template(output_file)

            print(f"\n✓ Template created successfully!")
            print(f"\nThe template includes:")
            print(f"  • Data sheet - Ready for your entries")
            print(f"  • Examples sheet - 5 sample rows demonstrating features")
            print(f"  • Instructions sheet - Comprehensive formatting guide")
            print(f"\nLocation: {Path(output_file).absolute()}")
            return 0

        # Handle subtitle file mode
        if extra_args.get("subtitle_file"):
            # Validate output directory is provided
            if not extra_args["output_dir"]:
                print("\nError: output_dir is required for subtitle file processing", file=sys.stderr)
                parser.parser.print_help()
                return 1

            # Setup logging
            logger = get_logger(__name__)
            logger.info("Starting Lower Thirds Generator - Subtitle Mode")

            # Validate output directory
            ConfigValidator.validate_output_dir(extra_args["output_dir"], create=True)

            # Load subtitle file
            subtitle_loader = SubtitleLoader()
            logger.info(f"Loading subtitle file: {extra_args['subtitle_file']}")
            subtitles, fps = subtitle_loader.load(extra_args["subtitle_file"])

            logger.info(f"Loaded {len(subtitles)} subtitles (detected {fps} fps)")

            # Create subtitle extractor
            extractor = SubtitleRowExtractor(
                config=config,
                filename_format=extra_args.get("subtitle_filename_format", "timecode")
            )

            # Create generator and saver
            generator = LowerThirdGenerator(config)
            saver = ImageSaver(config.output)

            # Test mode - preview first subtitle only
            if extra_args["test_mode"]:
                logger.info("Test mode: Previewing first subtitle only")

                first_subtitle = subtitles[0]
                row_data = extractor.extract_from_subtitle(first_subtitle, index=0)

                # Generate preview
                image = generator.generate_preview(row_data)

                # Show settings
                print("\nPreview Settings:")
                print(f"  Dimensions: {config.width}x{config.height}")
                print(f"  Background: {config.bg_color}")
                print(f"  Text Color: {config.text.text_color}")
                print(f"  Format: {config.output.format}")
                if config.text.shadow.enabled:
                    print(f"  Shadow: Enabled (blur={config.text.shadow.blur})")
                if config.text.outline.enabled:
                    print(f"  Outline: Enabled (width={config.text.outline.width})")
                print(f"  Subtitle Text: {first_subtitle.text}")
                print()

                # Show preview
                PreviewManager.show(image)

                print("\nPreview complete. Run without --test to generate all subtitle images.")
                return 0

            # Normal mode - process all subtitles
            count_success = 0
            count_failed = 0

            for index, subtitle in enumerate(subtitles):
                try:
                    # Extract row data from subtitle
                    row_data = extractor.extract_from_subtitle(subtitle, index)

                    # Generate image
                    image = generator.generate_from_row(row_data)

                    # Save image
                    filename = row_data.get_output_filename()
                    output_path = saver.save(image, extra_args["output_dir"], filename)

                    print(f"✓ Generated: {output_path.name}")
                    count_success += 1

                except L3rdsException as e:
                    logger.error(f"Failed to generate subtitle {index + 1}: {e}")
                    print(f"✗ Failed: Subtitle {index + 1} - {e}")
                    count_failed += 1

                except Exception as e:
                    logger.error(f"Unexpected error on subtitle {index + 1}: {e}", exc_info=True)
                    print(f"✗ Failed: Subtitle {index + 1} - {e}")
                    count_failed += 1

            # Summary
            print()
            print("=" * 80)
            print(f"Completed: {count_success} subtitle images generated")
            if count_failed > 0:
                print(f"Warning: {count_failed} images failed to generate")
                logger.warning(f"{count_failed} images failed to generate")
            print(f"Output directory: {Path(extra_args['output_dir']).absolute()}")
            print("=" * 80)

            return 0 if count_failed == 0 else 1

        # Validate required arguments for Excel/CSV mode
        if not extra_args["input_file"] or not extra_args["output_dir"]:
            print("\nError: input_file and output_dir are required (unless using --generate-template or --subtitle-file)", file=sys.stderr)
            parser.parser.print_help()
            return 1

        # Setup logging
        logger = get_logger(__name__)
        logger.info("Starting Lower Thirds Generator - Excel/CSV Mode")

        # Validate configuration
        ConfigValidator.validate(config, extra_args["input_file"])
        ConfigValidator.validate_output_dir(extra_args["output_dir"], create=True)

        # Load data
        loader = ExcelLoader()
        data = loader.load(extra_args["input_file"])

        # Create extractor and generator
        extractor = ExcelRowExtractor(debug=config.debug, default_justification=config.default_justification)
        generator = LowerThirdGenerator(config)

        # Create image saver
        saver = ImageSaver(config.output)

        # Test mode - preview first image only
        if extra_args["test_mode"]:
            logger.info("Test mode: Previewing first image only")

            first_row = data.iloc[0]
            row_data = extractor.extract_row(first_row, row_index=0)

            # Generate preview
            image = generator.generate_preview(row_data)

            # Show settings
            print("\nPreview Settings:")
            print(f"  Dimensions: {config.width}x{config.height}")
            print(f"  Background: {config.bg_color}")
            print(f"  Text Color: {config.text.text_color}")
            print(f"  Format: {config.output.format}")
            if config.text.shadow.enabled:
                print(f"  Shadow: Enabled (blur={config.text.shadow.blur})")
            if config.text.outline.enabled:
                print(f"  Outline: Enabled (width={config.text.outline.width})")
            print()

            # Show preview
            PreviewManager.show(image)

            print("\nPreview complete. Run without --test to generate all images.")
            return 0

        # Normal mode - generate all images
        logger.info(f"Generating {len(data)} lower thirds...")

        count_success = 0
        count_failed = 0

        for index, row in data.iterrows():
            try:
                # Extract row data
                row_data = extractor.extract_row(row, row_index=index)

                # Generate image
                image = generator.generate_from_row(row_data)

                # Save image
                filename = row_data.get_output_filename()
                output_path = saver.save(image, extra_args["output_dir"], filename)

                print(f"✓ Generated: {output_path.name}")
                count_success += 1

            except L3rdsException as e:
                logger.error(f"Failed to generate row {index}: {e}")
                print(f"✗ Failed: Row {index + 1} - {e}")
                count_failed += 1

            except Exception as e:
                logger.error(f"Unexpected error on row {index}: {e}", exc_info=True)
                print(f"✗ Failed: Row {index + 1} - {e}")
                count_failed += 1

        # Summary
        print()
        print("=" * 80)
        print(f"Completed: {count_success} lower thirds generated")
        if count_failed > 0:
            print(f"Warning: {count_failed} images failed to generate")
            logger.warning(f"{count_failed} images failed to generate")
        print(f"Output directory: {Path(extra_args['output_dir']).absolute()}")
        print("=" * 80)

        return 0 if count_failed == 0 else 1

    except L3rdsException as e:
        print(f"\nError: {e}", file=sys.stderr)
        if "--debug" in sys.argv:
            import traceback
            traceback.print_exc()
        return 1

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"\nCritical error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
