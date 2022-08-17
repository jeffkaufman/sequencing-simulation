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

Very rough:

```
aws s3 cp s3://prjna729801/$(head ~/PRJNA729801-fnames.txt -n 1) - \
  | gunzip \
  | grep ^[GACT]*$ \
  | cat -n \
  | while read n seq; do
     echo ">$n
$seq"
  done > ~/long-query.fasta
```

## Genome identification

Use a machine with at enough RAM to put all of nt into RAM.  This is currently
225GB.  I'm using a c6a.32xlarge.

```
blastn -db nt \
       -query ~/long-query.fasta \
       -num_threads 128 \
       -culling_limit 1 \
       -outfmt "6 qseqid length evalue saccver stitle" \
       -out ~/long-results.txt
```

I'm not confident that this is the right way to invoke BLAST for identifying
shotgun reads, or even whether BLAST is the best tool for this.  Possibly
something that just looks for exactly matching ~40-mers would be much faster?
I should read about how people ususually do this.

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

## Read simulation

After deciding how many total reads we want, we can figure out how many we want
from each genome.  Then we can download the genome with something like:

```
curl 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?\
db=nuccore&id=LR215980.1&rettype=fasta&retmode=text&api_key=[redacted]'
```

and extract the desired number of reads by picking that many offsets.

