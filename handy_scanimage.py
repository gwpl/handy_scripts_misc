#!/usr/bin/env python3
import os
import sys
import subprocess
import time
from datetime import datetime
import argparse

def scan(basename, file_format, date_option, sane_device, mode, resolution, verbose, icc_profile, output_file, progress, all_options, extra_args, retries=3, delay=1):
    cmd = ['scanimage', '--device', sane_device, '--mode', mode, '--resolution', resolution, '--format', file_format]
    
    if icc_profile:
        cmd.extend(['--icc-profile', icc_profile])
    
    if progress:
        cmd.append('--progress')
    
    if all_options:
        cmd.append('--all-options')
        cmd.extend(extra_args)
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

    # New argument to handle batch scanning, similar to scanimage's CLI.
    # If used with no value, it becomes True, meaning "batch mode", no specific prefix passed.
    # If a string is provided, that is the prefix format. 
    parser.add_argument('--batch', nargs='?', const=True,
                        help='Enable batch scanning with optional prefix format for the output file(s). If prefix is omitted, uses --output-file if provided, otherwise uses "scan_%d.<format>". If prefix does not contain "%%d", it is automatically appended.')

    parser.add_argument('extra_args', nargs=argparse.REMAINDER, help='Additional scanimage parameters after --')
    
    args = parser.parse_args()
    
    if args.device_name is None:
        args.device_name = os.getenv('SCANIMAGE_DEVICE')
        if args.device_name is None:
            print("ERROR: SANE device not provided. Use `scanimage -L` to find one and provide via `-d` flag or set environment variable $SCANIMAGE_DEVICE.", file=sys.stderr)
            sys.exit(1)

    # If batch mode is requested, replicate the scanimage batch behavior.
    if args.batch is not None:
        # Determine the prefix
        if args.batch is True:
            # user typed --batch with no argument
            if args.output_file:
                prefix = args.output_file
            else:
                prefix = "scan_%d"
        else:
            # user typed --batch=something
            prefix = str(args.batch)

        # If there's no '%d' in prefix, append it
        if '%d' not in prefix:
            # add it before any extension if present
            if '.' in prefix:
                dot_index = prefix.rfind('.')
                prefix = prefix[:dot_index] + '_%d' + prefix[dot_index:]
            else:
                prefix += '_%d'

        # If there's no extension at all, add one based on --format
        # A simple check: if the last '.' is before any path slash or not present
        # We'll do a naive approach: if there's no '.' in prefix (after we've possibly appended '_%d'),
        # we add '.' + format
        if '.' not in prefix:
            prefix += '.' + args.format

        # Build the batch command
        batch_cmd = [
            'scanimage',
            '--device', args.device_name,
            '--mode', args.mode,
            '--resolution', args.resolution,
            '--format', args.format,
            f'--batch={prefix}'
        ]

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
            # in batch mode. The user can open them manually.
            sys.exit(0)

    # If not batch, do a single scan
    filename = scan(args.basename, args.format, args.date, args.device_name, args.mode,
                    args.resolution, args.verbose, args.icc_profile, args.output_file,
                    args.progress, args.all_options, args.extra_args, args.retries, args.delay)
    
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
