#!/usr/bin/env python

# ENCODE DCC IDR wrapper
# Author: Jin Lee (leepc12@gmail.com)

import sys
import os
import argparse
import multiprocessing
import math
from encode_dcc_common import *

def parse_arguments():
    parser = argparse.ArgumentParser(prog='ENCODE DCC IDR.',
                        description='NarrowPeak or RegionPeak only.')
    parser.add_argument('peak1', type=str,
                        help='Peak file 1.')
    parser.add_argument('peak2', type=str,
                        help='Peak file 2.')
    parser.add_argument('peak_pooled', type=str,
                        help='Pooled peak file.')
    parser.add_argument('--prefix', default='idr', type=str,
                        help='Prefix basename for output IDR peak.')
    parser.add_argument('--idr-thresh', default=0.1, type=float,
                        help='IDR threshold.')
    parser.add_argument('--idr-rank', default='p.value', type=str,
                        choices=['p.value','q.value','signal.value'],
                        help='IDR ranking method.')
    parser.add_argument('--out-dir', default='.', type=str,
                        help='Output directory.')
    parser.add_argument('--log-level', default='INFO', 
                        choices=['NOTSET','DEBUG','INFO',
                            'WARNING','CRITICAL','ERROR','CRITICAL'],
                        help='Log level')
    args = parser.parse_args()

    log.setLevel(args.log_level)
    log.info(sys.argv)
    return args

def get_npeak_col_by_rank(rank):
    if rank=='signal.value':
        return 7
    elif rank=='p.value':
        return 8
    elif rank=='q.value':
        return 9
    else:
        raise ValueError('Invalid score ranking method')

# only for narrowPeak (or regionPeak) type 
def idr(basename_prefix, peak1, peak2, peak_pooled, 
    thresh, rank, out_dir):
    prefix = os.path.join(out_dir, basename_prefix)
    prefix += '.idr{}'.format(thresh)
    peak_ext = get_ext(peak1)
    idr_peak = '{}.{}.gz'.format(prefix,peak_ext)
    idr_out_gz = '{}.unthresholded-peaks.txt.gz'.format(prefix)
    idr_plot = '{}.unthresholded-peaks.txt.png'.format(prefix)
    idr_stdout = '{}.log'.format(prefix)
    # temporary
    idr_12col_bed = '{}.12-col.bed.gz'.format(peak_ext)
    idr_out = '{}.unthresholded-peaks.txt'.format(prefix)

    cmd1 = 'idr --samples {} {} --peak-list {} --input-file-type narrowPeak '
    cmd1 += '--output-file {} --rank {} --soft-idr-threshold {} '
    cmd1 += '--plot --use-best-multisummit-IDR --log-output-file {}'
    cmd1 = cmd1.format(
        peak1,
        peak2,
        peak_pooled,
        idr_out,
        rank,
        thresh,
        idr_stdout)
    run_shell_cmd(cmd1)

    col = get_npeak_col_by_rank(rank)
    neg_log10_thresh = -math.log10(thresh)
    # LC_COLLATE=C 
    cmd2 = 'awk \'BEGIN{{OFS="\\t"}} $12>={} '
    cmd2 += '{{if ($2<0) $2=0; '
    cmd2 += 'print $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12}}\' {} '
    cmd2 += '| sort | uniq | sort -s -grk{},{} | gzip -nc > {}'
    cmd2 = cmd2.format(
        neg_log10_thresh,
        idr_out,
        col,
        col,
        idr_12col_bed)
    run_shell_cmd(cmd2)

    cmd3 = 'zcat {} | '
    cmd3 += 'awk \'BEGIN{{OFS="\\t"}} '
    cmd3 += '{{print $1,$2,$3,$4,$5,$6,$7,$8,$9,$10}}\' | '
    cmd3 += 'gzip -nc > {}'
    cmd3 = cmd3.format(
        idr_12col_bed,
        idr_peak)
    run_shell_cmd(cmd3)

    cmd4 = 'gzip -f {}'.format(idr_out)
    run_shell_cmd(cmd4)

    rm_f([idr_out, idr_12col_bed])
    rm_f('{}.*.noalternatesummitpeaks.png'.format(prefix))
    return idr_peak, idr_plot, idr_out_gz, idr_stdout

def main():
    # read params
    args = parse_arguments()
    log.info('Initializing and making output directory...')

    # make out_dir (root of all outputs)
    mkdir_p(args.out_dir)

    log.info('Do IDR...')
    idr_peak, idr_plot, idr_out_gz, idr_stdout = idr(
        args.prefix, 
        args.peak1, args.peak2, args.peak_pooled, 
        args.idr_thresh, args.idr_rank, args.out_dir)

    log.info('Checking if output is empty...') # bedtools issue
    assert_file_not_empty(idr_peak)
    
    log.info('All done.')

if __name__=='__main__':
    main()