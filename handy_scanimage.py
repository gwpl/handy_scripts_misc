#!/usr/bin/env python3
import os
import sys
import subprocess
import time
from datetime import datetime
import argparse

def scan(basename, file_format, date_option, sane_device, mode, resolution, verbose, icc_profile, output_file, progress, all_options, extra_args, retries=3, delay=1, source='Flatbed'):
    cmd = [
        'scanimage',
        '--device', sane_device,
        '--mode', mode,
        '--resolution', resolution,
        '--format', file_format,
        '--source', source
    ]
    
    if icc_profile:
        cmd.extend(['--icc-profile', icc_profile])
    
    if progress:
        cmd.append('--progress')
    
    if all_options:
        cmd.append('--all-options')
        cmd.extend(extra_args)
        if verbose:
            print(f"INFO: Running command: {' '.join(cmd)}", file=sys.stderr)
        scanimage_result = subprocess.run(cmd)
        return None

    if output_file:
        filename = output_file
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")
        if date_option == 'prefix':
            filename = f"{timestamp}-{basename}.{file_format}"
        elif date_option == 'suffix':
            filename = f"{basename}-{timestamp}.{file_format}"
        else:
            filename = f"{basename}.{file_format}"

    cmd.extend(['--output-file', filename])

    if verbose:
        print(f"INFO: Running command: {' '.join(cmd)}", file=sys.stderr)

    while not output_file and os.path.exists(filename):
        if verbose:
            print(f"INFO: File {filename} already exists. Waiting 1 second.", file=sys.stderr)
        time.sleep(1)
        timestamp = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")
        if date_option == 'prefix':
            filename = f"{timestamp}-{basename}.{file_format}"
        elif date_option == 'suffix':
            filename = f"{basename}-{timestamp}.{file_format}"
        else:
            filename = f"{basename}.{file_format}"
        cmd[-1] = filename

    cmd.extend(extra_args)

    attempt = 0
    while attempt <= retries:
        scanimage_result = subprocess.run(cmd)
        if scanimage_result.returncode == 0:
            print(filename)
            return filename
        else:
            print(f"ERROR: scanimage failed with return code {scanimage_result.returncode}", file=sys.stderr)
            if attempt < retries:
                print(f"INFO: Retrying in {delay} seconds... (Attempt {attempt + 1} of {retries})", file=sys.stderr)
                time.sleep(delay)
            attempt += 1
    return None


def main():
    parser = argparse.ArgumentParser(description='Scan an image with options.')
    parser.add_argument('-b', '--basename', default='scanimage', help='Base name for the output file')
    parser.add_argument('-f', '--format', default=os.getenv('SCANIMAGE_FORMAT', 'png'), help='Output file format ( pnm|tiff|png|jpeg|pdf )')
    parser.add_argument('-m', '--mode', default='Color', choices=['Color', 'Gray'], help='Scan mode (Color|Gray)')
    parser.add_argument('-r','--resolution','--dpi', default=os.getenv('SCANIMAGE_RESOLUTION', '600'), help='Scan resolution in dpi')
    parser.add_argument('--date', choices=['prefix', 'suffix', 'no'], default='suffix', help='Date position in filename')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('-d', '--device-name', default=None, help='SANE device to use (use `scanimage -L` to find one), if not provided, env. $SCANIMAGE_DEVICE is used')
    parser.add_argument('-i', '--icc-profile', help='Include this ICC profile into TIFF file')
    parser.add_argument('-o', '--output-file', help='Save output to the given file instead of stdout (or if --batch is used, treat this as the batch prefix).')
    parser.add_argument('-p', '--progress', action='store_true', help='Print progress messages')
    parser.add_argument('-A', '--all-options', action='store_true', help='List all available backend options')
    parser.add_argument('-V', '--view', help='Command to view the scanned file. Use {} as a placeholder for the filename.')
    parser.add_argument('--retries', type=int, default=3, help='Number of retries if scanimage fails')
    parser.add_argument('--delay', type=int, default=1, help='Delay in seconds between retries')

    # New source argument
    parser.add_argument('-s','--source', choices=['Flatbed','ADF','ADF Duplex'], default='Flatbed',
                        help='Scan source (Flatbed, ADF, or ADF Duplex)')

    # New argument to handle batch scanning, similar to scanimage's CLI.
    parser.add_argument('--batch', nargs='?', const=True,
                        help='Enable batch scanning with optional prefix format for the output file(s). '
                             'If prefix is omitted, uses --output-file if provided, otherwise uses "scan_%%d.<format>". '
                             'If prefix does not contain "%%d", it is automatically appended.')

    parser.add_argument('extra_args', nargs=argparse.REMAINDER, help='Additional scanimage parameters after --')
    
    args = parser.parse_args()
    
    if args.device_name is None:
        args.device_name = os.getenv('SCANIMAGE_DEVICE')
        if args.device_name is None:
            print("ERROR: SANE device not provided. Use `scanimage -L` to find one and provide via `-d` flag or set environment variable $SCANIMAGE_DEVICE.", file=sys.stderr)
            sys.exit(1)

    # If user chose ADF Duplex but did NOT specify --batch, let's automatically
    # switch to batch mode with a default prefix that includes date and page number.
    if args.source == 'ADF Duplex' and args.batch is None:
        timestamp = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")
        if args.output_file:
            base_no_ext = args.output_file
        else:
            if args.date == 'prefix':
                base_no_ext = f"{timestamp}-{args.basename}"
            elif args.date == 'suffix':
                base_no_ext = f"{args.basename}-{timestamp}"
            else:
                base_no_ext = f"{args.basename}"
        prefix = f"{base_no_ext}-page-%d.{args.format}"
        if args.verbose:
            print(f"INFO: Source is ADF Duplex but no batch specified, automatically enabling batch scanning with prefix '{prefix}'", file=sys.stderr)
        args.batch = prefix

    # If batch mode is requested (or forced above), replicate the scanimage batch behavior.
    if args.batch is not None:
        # Determine the prefix
        if args.batch is True:
            # user typed --batch with no argument
            if args.output_file:
                prefix = args.output_file
            else:
                prefix = "scan_%d"
        else:
            # user typed --batch=something (or we forced it above)
            prefix = str(args.batch)

        # If there's no '%d' in prefix, append it
        if '%d' not in prefix:
            if '.' in prefix:
                dot_index = prefix.rfind('.')
                prefix = prefix[:dot_index] + '_%d' + prefix[dot_index:]
            else:
                prefix += '_%d'

        # If there's no extension at all, add one based on --format
        if '.' not in prefix:
            prefix += '.' + args.format

        # Build the batch command
        batch_cmd = [
            'scanimage',
            '--device', args.device_name,
            '--mode', args.mode,
            '--resolution', args.resolution,
            '--format', args.format,
            '--source', args.source,
            f'--batch={prefix}'
        ]

        # If the user selected ADF Duplex, automatically add '--batch-double' and '--batch-increment=1' if missing
        if args.source == 'ADF Duplex':
            has_batch_double = any(arg.startswith('--batch-double') for arg in args.extra_args) or any(arg.startswith('--batch-double') for arg in batch_cmd)
            if not has_batch_double:
                if args.verbose:
                    print("INFO: Adding --batch-double for ADF Duplex", file=sys.stderr)
                batch_cmd.append('--batch-double')

            has_batch_increment = any(arg.startswith('--batch-increment=') for arg in args.extra_args) or any(arg.startswith('--batch-increment=') for arg in batch_cmd)
            if not has_batch_increment:
                if args.verbose:
                    print("INFO: Adding --batch-increment=1 for ADF Duplex", file=sys.stderr)
                batch_cmd.append('--batch-increment=1')

        if args.icc_profile:
            batch_cmd.extend(['--icc-profile', args.icc_profile])

        if args.progress:
            batch_cmd.append('--progress')

        if args.all_options:
            batch_cmd.append('--all-options')

        # Include extra_args
        batch_cmd.extend(args.extra_args)

        if args.verbose:
            print(f"INFO: Running command: {' '.join(batch_cmd)}", file=sys.stderr)

        ret = subprocess.run(batch_cmd)
        if ret.returncode != 0:
            print(f"ERROR: scanimage batch mode failed with return code {ret.returncode}", file=sys.stderr)
            sys.exit(ret.returncode)
        else:
            # We won't attempt to open with a viewer because many files could be created
            # in batch mode. The user can open them manually if needed.
            sys.exit(0)

    # If not batch, do a single scan
    filename = scan(
        basename=args.basename,
        file_format=args.format,
        date_option=args.date,
        sane_device=args.device_name,
        mode=args.mode,
        resolution=args.resolution,
        verbose=args.verbose,
        icc_profile=args.icc_profile,
        output_file=args.output_file,
        progress=args.progress,
        all_options=args.all_options,
        extra_args=args.extra_args,
        retries=args.retries,
        delay=args.delay,
        source=args.source
    )
    
    # If we have a viewer command, try to open the scanned file
    if filename and args.view:
        if '{}' in args.view:
            view_cmd = args.view.format(filename)
            view_cmd_list = view_cmd.split()
        else:
            view_cmd_list = args.view.split() + [filename]
        
        if args.verbose:
            print(f"INFO: Running viewer command: {' '.join(view_cmd_list)}", file=sys.stderr)
        
        subprocess.run(view_cmd_list)

if __name__ == '__main__':
    main()
