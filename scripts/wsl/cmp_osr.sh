O=$HOME/work/t8/osr/G
PYTHONPATH=$HOME/ext/g-style $HOME/venvs/gstyle/bin/python /mnt/c/Work/3DGSAnimation-T8/scripts/wsl/compare_sr.py --gt $O/gt --dirs bicubic2x=$O/all/bicubic2x sr2x=$O/all/sr2x native4096=$O/all/s2 --out $O/summary.json 2>&1 | tail -15
