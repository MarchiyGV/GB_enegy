from pathlib import Path
import argparse, os, sys, shutil
from subprocess import Popen, PIPE
import time, re, shutil, sys, glob
import numpy as np

sys.path.insert(1, f'{sys.path[0]}/scripts')
from set_lammps import lmp

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", required=True)
parser.add_argument("-j", "--jobs", type=int, required=False, default=1)
parser.add_argument("--id", required=True, type=int)
parser.add_argument("-s", "--structure", required=False)
parser.add_argument("-v", "--verbose", default=False, action='store_true', required=False)
parser.add_argument("--np", required=False, default=1)
args = parser.parse_args()

os.chdir('scripts')

structure = args.structure
if not structure:
    fname = f'../workspace/{args.name}/conf.txt'
    flag=False
    with open(fname, 'r') as f :
        for line in f:
            if 'minimized' in line:
                structure = line.split()[-1]
                print(structure)
                flag = True
    if not flag:
        raise ValueError(f'cannot find structure in conf.txt')
    

outname = f'../workspace/{args.name}/dump/CNA/bulkEs.txt'

if args.jobs == 1:
    suffix = ''
else:
    suffix = f' -sf omp -pk omp {args.jobs} '

task = f'mpirun -np {args.np} {lmp} -in in.seg_minimize -var name {args.name} -var structure_name {structure} -var self bulk_seg -var id {args.id} {suffix}'
exitflag = False
db_flag = False
db = 0

print(task)
with Popen(task.split(), stdout=PIPE, bufsize=1, universal_newlines=True) as p:
    time.sleep(0.1)
    print('\n')
    for line in p.stdout:
        if "Dangerous builds" in  line:
            db = int(line.split()[-1])
            if db>0:
                db_flag = True
        elif "dumpfile" in line:
            dumpfile = (line.replace('dumpfile ', '')).replace('\n', '')
        elif "datfile" in line:
            datfile = (line.replace('datfile ', '')).replace('\n', '')
        elif "Seg energy" in line:
            print((line.replace('Seg energy ', '')).replace('\n', ''))
            E = float((line.replace('Seg energy ', '')).replace('\n', ''))
        elif "All done" in line:
            exitflag = True
        elif "settings made for type" in line:
            ns = int(line.split()[0])
            if ns != 1:
                raise ValueError(f'There is no atoms with id {args.id}')
        if not args.verbose:
            if '!' in line:
                print(line.replace('!', ''), end='')
        else:
            print(line, end='')   
                
if not exitflag:
    raise ValueError('Error in LAMMPS')

print('done\n')
if db > 0:
    print(f'WARNING!!!\nDengerous neighboor list buildings: {db}')

print(f'E {E}')
append = os.path.isfile(outname)
if append:
    with open(outname, "ab") as f:
        f.write(b"\n")
        np.savetxt(f, [[args.id, E]])
else:
    np.savetxt(outname, [[args.id, E]], header='id E')
print('All done')