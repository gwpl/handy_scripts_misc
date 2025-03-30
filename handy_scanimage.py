#!/usr/bin/env python3
import os
import sys
import subprocess
import time
from datetime import datetime
import argparse

def scan(basename, file_format, date_option, sane_device, verbose):
    cmd = ['scanimage', '--device', sane_device, '--mode=Color', '--resolution', '600', '--format=tiff']
    
    if verbose:
        print(f"INFO: Running command: {' '.join(cmd)}", file=sys.stderr)
    
    timestamp = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")
    if date_option == 'prefix':
        filename = f"{timestamp}-{basename}.{file_format}"
    elif date_option == 'suffix':
        filename = f"{basename}-{timestamp}.{file_format}"
    else:
        filename = f"{basename}.{file_format}"
    
    while os.path.exists(filename):
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
    
    with open(filename, 'wb') as f:
        scanimage_result = subprocess.run(cmd, stdout=f)

    # if process is successful we print just the filename
    if scanimage_result.returncode == 0:
        print(filename)
    else:
        print(f"ERROR: scanimage failed with return code {scanimage_result.returncode}", file=sys.stderr)
    
    if verbose:
        print(f"INFO: Scan saved to {filename}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description='Scan an image with options.')
    parser.add_argument('-b', '--basename', default='scanimage', help='Base name for the output file')
    parser.add_argument('-f', '--format', default='png', help='Output file format')
    parser.add_argument('--date', choices=['prefix', 'suffix', 'no'], default='suffix', help='Date position in filename')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('-d', '--device', default=None, help='SANE device to use (use `scanimage -L` to find one), if not provided, env. $SCANIMAGE_DEVICE is used')
    
    args = parser.parse_args()
    
    # if device not provided by user env. $SCANIMAGE_DEVICE is set.
    if args.device is None:
        # if device not provided by arg or env then display info
        args.device = os.getenv('SCANIMAGE_DEVICE')
        if args.device is None:
            print("ERROR: SANE device not provided. Use `scanimage -L` to find one and provide via `-d` flag or set environment variable $SCANIMAGE_DEVICE.", file=sys.stderr)
            sys.exit(1)
    
    scan(args.basename, args.format, args.date, args.device, args.verbose)

if __name__ == '__main__':
    main()
