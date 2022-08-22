# Reads from stdin, writes to stdout.
#
# Args:
#   lengths: file with lines in the form "count length"
#   qualities: file with lines in the form "{'char': freq}"
#
# Input: lines in the form
#
#   [number to generate] [accession number]
#   [number to generate] [accession number]
#   ...
#
# Output: simulated reads in fasta format
#
# Ex:
#    cat freqs \
#      | python simulate-reads.py \
#            PRJNA729801-even-sample-1000x-polyg.lengths \
#            quality-by-position.jsons \
#      | gzip
#      | aws s3 cp - s3://prjna729801/simulated.fastq.gz

import os
import re
import sys
import json
import random
import subprocess
from collections import defaultdict

qualities_choices = ['F', ':', ',', '#']
numeric_quality = [10**(-.1*(ord(x)-33)) for x in qualities_choices]

def start(lengths_fname, qualities_fname):
    lengths_weights = process_lengths(lengths_fname)
    lengths_choices = list(range(1, len(lengths_weights) + 1))

    qualities_weights_by_position = process_qualities(qualities_fname)

    for line in sys.stdin:
        count, accession_number = line.strip().split()
        simulate_reads(
            int(count), accession_number,
            lengths_weights, lengths_choices,
            qualities_weights_by_position)

def generate_seq(genome, length):
    start = random.randint(0, len(genome) - length)
    seq = genome[start : start + length]
    if not re.fullmatch(seq, '[ACTG]*'):
        return seq
    return None

def error_base(base, quality):
    if random.random() < numeric_quality[qualities_choices.index(quality)]:
        return random.choice('ACTG')
    return base

def error_seq(plain_seq, quality_line):
    return ''.join(
        error_base(base, quality) for
        (base, quality) in zip(plain_seq, quality_line))

def simulate_reads(count, accession_number,
                   lengths_weights, lengths_choices,
                   qualities_weights_by_position):
    genome = get_genome(accession_number)
    n_generated = 0
    while n_generated < count:
        length, = random.choices(lengths_choices, weights=lengths_weights)
        plain_seq = generate_seq(genome, length)
        if not plain_seq:
            continue

    
        quality_line = ''.join(
            random.choices(qualities_choices,
                           weights=qualities_weights_by_position[i])[0]
            for i in range(length))

        errored_seq = error_seq(plain_seq, quality_line)

        print(">%s-%s" % (accession_number, n_generated))
        print(plain_seq)
        print('+')
        print(quality_line)

        n_generated += 1

def process_lengths(lengths_fname):
    lengths_raw = defaultdict(int)
    total = 0
    with open(lengths_fname) as inf:
        for line in inf:
            count, length = line.strip().split()
            lengths_raw[int(length)] = int(count)
            total += int(count)

    return [lengths_raw[i] for i in range(max(lengths_raw))]

def process_qualities(qualities_fname):
    qualities_weights_by_position = []
    with open(qualities_fname) as inf:
        for line in inf:
            qualities = json.loads(line)
            qualities_weights_by_position.append(
                (qualities.get('F', 0),
                 qualities.get(',', 0),
                 qualities.get(':', 0),
                 qualities.get('#', 0)))
    return qualities_weights_by_position

def get_genome(accession_number):
    return subprocess.check_output(
        ['blastdbcmd',
         '-entry', accession_number,
         '-db', 'nt',
         '-outfmt', '%s'],
        cwd="/home/ec2-user/nt").decode('utf-8')

if __name__ == "__main__":
    start(*sys.argv[1:])
    
