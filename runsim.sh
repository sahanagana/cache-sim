#!/bin/bash

#filename="$1"
#outputname="$2"

outputname="sample.out"

for filename in Traces/Spec_Benchmark/*.din; do
	echo what
	./d4-7/dineroIV -l1-isize 32K -l1-dsize 32K -l1-irepl r -l1-drepl r -l2-usize 256K -l2-uassoc 4 -l2-urepl r -l1-ibsize 64 -l1-dbsize 64 -l2-ubsize 64  -informat d < "$filename" > "$outputname"
done
