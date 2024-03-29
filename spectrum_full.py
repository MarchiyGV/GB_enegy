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
parser.add_argument("-s", "--structure", required=False)
parser.add_argument("-v", "--verbose", default=False, action='store_true', required=False)
parser.add_argument("-f", "--force", default=False, action='store_true', required=False,
                     help='force to restart calculations')
parser.add_argument("--np", required=False, default=1)
args = parser.parse_args()

os.chdir('scripts')

structure = args.structure
if not structure:
    fname = f'../workspace/{args.name}/conf.txt'
    flag=False
    with open(fname, 'r') as f :
        for line in f:
            if 'ann_minimized' in line:
                structure = line.split()[-1]
                atom_arg = '1'
                print(structure)
                flag = True
    if not flag:
        raise ValueError(f'cannot find structure in conf.txt')
    
id_file = f'../workspace/{args.name}/dump/CNA/ids_c.txt'
outname = f'../workspace/{args.name}/dump/CNA/ms_renormed.txt'

ids = np.loadtxt(id_file).astype(int)
i0 = 0

if (not args.force) and os.path.isfile(outname):
    out = np.loadtxt(outname)
    i0 = np.where(out[:, 0]==0)[0][0]
    structure = f'seg_minimize_full_{i0-1}.dat'
    atom_arg = '0'
    print(f'found previous calculations, continue from #{i0}/{len(out)} point')
else:
    print(f'starting new calculation')
    out = np.zeros((ids.shape[0], 2))

if args.jobs == 1:
    suffix = ''
else:
    suffix = f' -sf omp -pk omp {args.jobs} '

from datetime import datetime
now = datetime.now()
print('Starting time: ', now.strftime("%H:%M:%S"))
for i in range(i0, len(ids)):
    ids_i = ids[i]
    ids_i = ids_i[ids_i!=-1]
    print(f'#{i+1}/{len(ids)} id {ids_i}')
    ids_i_arg = (' '.join(str(id) for id in ids_i))
    task = f'mpirun -np {args.np} {lmp} -in in.seg_minimize_full -var count {i} -var name {args.name} -var structure_name {structure}  -var atom_types {atom_arg} -var id {ids_i_arg} {suffix}'
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
    out[i, 0] = len(ids_i)
    out[i, 1] = E
    np.savetxt(outname, out, header='number E')
    structure = datfile # first calculation done with minimized pure structer, all consequent get structure from previous step
    atom_arg = '0'                      # first calculation done with minimized pure structer, all consequent get structure from previous step
print('All done')