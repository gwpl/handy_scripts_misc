#!/usr/bin/env python3
import os
import sys
import subprocess
import time
from datetime import datetime
import argparse

def scan(basename, file_format, date_option, sane_device, mode, resolution, verbose, icc_profile, output_file, progress, all_options, extra_args):
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

    scanimage_result = subprocess.run(cmd)

    if scanimage_result.returncode == 0:
        print(filename)
        return filename
    else:
        print(f"ERROR: scanimage failed with return code {scanimage_result.returncode}", file=sys.stderr)
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
    parser.add_argument('-o', '--output-file', help='Save output to the given file instead of stdout')
    parser.add_argument('-p', '--progress', action='store_true', help='Print progress messages')
    parser.add_argument('-A', '--all-options', action='store_true', help='List all available backend options')
    parser.add_argument('-V', '--view', help='Command to view the scanned file. Use {} as a placeholder for the filename.')
    parser.add_argument('extra_args', nargs=argparse.REMAINDER, help='Additional scanimage parameters after --')
    
    args = parser.parse_args()
    
    # if device not provided by user env. $SCANIMAGE_DEVICE is set.
    if args.device_name is None:
        # if device not provided by arg or env then display info
        args.device_name = os.getenv('SCANIMAGE_DEVICE')
        if args.device_name is None:
            print("ERROR: SANE device not provided. Use `scanimage -L` to find one and provide via `-d` flag or set environment variable $SCANIMAGE_DEVICE.", file=sys.stderr)
            sys.exit(1)
    
    filename = scan(args.basename, args.format, args.date, args.device_name, args.mode, args.resolution, args.verbose, args.icc_profile, args.output_file, args.progress, args.all_options, args.extra_args)
    
    if args.view:
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
