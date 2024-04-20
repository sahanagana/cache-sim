#!/bin/bash

#filename="$1"
#outputname="$2"

filename="008.espresso.din"
outputname="sample.out"

cd d4-7
./dineroIV -l1-isize 256K -l1-dsize 256K -l1-irepl r -l1-drepl r -l2-usize 2048K -l2-uassoc 4 -l2-urepl r -l1-ibsize 64 -l1-dbsize 64 -l2-ubsize 64  -informat d < "../Traces/Spec_Benchmark/$filename" > "$outputname"
