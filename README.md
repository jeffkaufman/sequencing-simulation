# sequencing-simulation

We have a relatively small amount of shotgun sequencing data, and want to
simulate a much larger set of data.  One way to do that is:

1. Convert your sequencing data into a set of genomes and frequencies
2. Simulate reads from those genomes at those frequencies

This repo is currently pretty experimental, and is a mixture of automated and
manual steps.

## Input data

We're using data collected for [RNA Viromics of Southern California Wastewater
and Detection of SARS-CoV-2 Single-Nucleotide
Variants](https://journals.asm.org/doi/full/10.1128/AEM.01448-21).

We have this in S3 under `s3://prjna729801/SRR*.fastq.gz`

## Read extraction

Sample evenly over the input files:

```
cat ~/PRJNA729801-fnames.txt \
  | while read fname ; do
      aws s3 cp s3://prjna729801/$fname - \
        | gunzip \
        | head -n 120000
     done \
  > PRJNA729801-even-sample-1000x.fastq
```

Remove poly-G trailers and convert to fasta:

```
cat ~/PRJNA729801-even-sample-1000x.fastq \
  | grep -o ^[ACTG]*$ \
  | sed 's/GGGGGGGGG*$//' \
  | cat -n \
  | awk '{print ">"$1"\n"$2}' \
  > ~/PRJNA729801-even-sample-1000x-polyg.fasta
```

## Genome identification

Use a machine with at enough RAM to put all of nt into RAM.  This is currently
225GB.  I'm using a c6a.32xlarge.

```
screen
cd nt
time blastn -db nt \
            -query ~/PRJNA729801-even-sample-1000x-polyg.fasta \
            -num_threads 128 \
            -culling_limit 1 \
            -outfmt "6 qseqid length evalue saccver sskingdom" \
            -word_size 40 \
            -evalue 1e-40 \
  > ~/result-es-10m-pg-k40-e40.txt
```

## Genome counting

On a subset:

```
$ cat long-results.txt | awk -F'\t' '{print $4}' | sort | uniq -c | sort -n
  39634 LN899821.1
  23632 LR135185.1
  14478 MN549394.1
   4933 CP032354.1
   2486 CP075188.1
   1512 CP020544.1
   1272 LN899827.1
   1219 LN899524.1
   1201 LN899822.1
   1179 LC662918.1
...
```

## Understanding read distribution

### Get quality distribution by position

```
cat PRJNA729801-even-sample-1000x.fastq \
  | python3 count-quality.py \
  > quality-by-position.jsons
```

### Get length distribution

```
cat PRJNA729801-even-sample-1000x-polyg.fasta \
  | grep -v '^>' \
  | awk "{print length()}" \
  | sort -n \
  | uniq -c \
  > PRJNA729801-even-sample-1000x-polyg.lengths
```

## Read simulation

After deciding how many total reads we want, we can figure out how many we want
from each genome.  Then we can extract the genome from the blast db with:

```
blastdbcmd -entry LN899821.1 -db nt -outfmt '%s'
```

and extract the desired number of reads by picking that many offsets.

```
cat counts.txt \
  | python3 simulate-reads.py \
      PRJNA729801-even-sample-1000x-polyg.lengths \
      quality-by-position.jsons \
  | gzip
  | aws s3 cp - s3://prjna729801/simulated.fastq.gz
```
