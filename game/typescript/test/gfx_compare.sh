#!/bin/bash
# usage: test/gfx_compare.sh ASSETS FIRST LAST [--preset] [--wander]   (one process pair per seed, in parallel)
cd "$(dirname "$0")/.."
A=$1; F=$2; L=$3; shift 3
T=${GFX_OUT:-$(mktemp -d)}; mkdir -p $T
one() {
  s=$1; shift; A=$1; shift; T=$1; shift
  python3 test/gfx_game_py.py "$A" $s $s "$@" --answers $T/ans$s.json > $T/py$s.txt 2>$T/py$s.err
  node test/gfx_game.mjs "$A" $s $s "$@" --answers $T/ans$s.json > $T/ts$s.txt 2>$T/ts$s.err
  if diff -q $T/py$s.txt $T/ts$s.txt >/dev/null; then echo "seed $s OK $(cat $T/ts$s.txt)"; else echo "seed $s DIFFER py=[$(cat $T/py$s.txt)] ts=[$(cat $T/ts$s.txt)] $(head -c 300 $T/ts$s.err)"; fi
}
export -f one
seq $F $L | xargs -P ${JOBS:-6} -I{} bash -c "one {} $A $T $*"
