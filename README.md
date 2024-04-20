`./dineroIV -l1-isize 256K -l1-dsize 256K -l1-irepl r -l1-drepl r -l2-usize 2048K -l2-uassoc 4 -l2-urepl r -l1-ibsize 64 -l1-dbsize 64 -l2-ubsize 64  -informat d < "../Traces/Spec_Benchmark/$filename" > "$outputname"`

l1-isize: size of L1 instruction cache (in kibibits)
l1-dsize: size of L1 data cache (kibibits)
l1-irepl: replacement algorithm for instruction cache
l1-drepl: replacement algorithm for data cache
(l1-iassoc): L1 instruction cache associativity (leaving as default)
(l1-dassoc): L1 data cache associativity (leaving as default)
l1-ibsize: instruction cache block size (bytes)
l1-dbsize: instruction cache block size (bytes)

l2-usize: size of L2 unified cache (kibibits)
l2-uassoc: L2 unified cache associativity
l2-urepl: unified replacement algorithm (set to random)
l2-ubsize: unified cache block size (bytes)

informat: dniero format

Arg 1: input file
Arg 2: output file
