#!/usr/bin/env python3
# please see https://github.com/lh3/asub
import argparse
import csv
import os
import re
import shutil
import stat
import subprocess
import sys
import pandas as pd
from datetime import datetime

__author__ = 'Jie Zhu'
__email__ = 'zhujie@genomics.cn'
__version__ = '0.3.1'
__date__ = 'Aug 22, 2019'


def parse_job(job_name, job_file, a_job_line, logdir):
    df_list = []
    df = pd.DataFrame()
    if job_file is not None:
        for f in job_file:
            df = pd.read_csv(f, sep='\t', names=["script"])
            df_list.append(df)
        df = pd.concat(df_list)
    else:
        df = pd.read_csv(sys.stdin, sep='\t', names=["script"])
    job_num = 0
    for i in range(0, len(df), a_job_line):
        job_num += 1
        job_f = os.path.join(logdir, f"{job_name}_{job_num}.sh")
        df.iloc[i:i+a_job_line]\
          .to_csv(job_f, sep='\t', index=False, header=False, quoting=csv.QUOTE_NONE)
    return job_num


def submit_job(job_name, total_job_num, queue, prj_id, resource, logdir):
    submit_f = os.path.join(os.path.dirname(logdir), f"{job_name}_submit.sh")
    array_range = f"1-{total_job_num}:1"
    job_script = os.path.join(logdir, f"{job_name}_$SGE_TASK_ID.sh")
    num_proc = resource.split('=')[-1]
    with open(submit_f, 'w') as submit_h:
        submit_h.write(f'''#!/bin/bash\n\
#$ -clear
#$ -S /bin/bash
#$ -V
#$ -N {job_name}
#$ -cwd
#$ -l {resource}
#$ -binding linear:{num_proc}
#$ -q {queue}
#$ -P {prj_id}
#$ -t {array_range}
jobscript={job_script}
bash $jobscript\n''')

    os.chmod(submit_f, stat.S_IRWXU)
    error = os.path.join(logdir, f"{job_name}_\\$TASK_ID.e")
    output = os.path.join(logdir, f"{job_name}_\\$TASK_ID.o")
    qsub = shutil.which("qsub")
    submit_cmd = f"{qsub} -e {error} -o {output} {submit_f}"
    subprocess.call(submit_cmd, shell=True)


def main():
    '''it is a very simple script to submit array job, but you need supply real run command'''
    parser = argparse.ArgumentParser(description='make submit array job easy')
    parser.add_argument('-jobfile', nargs='*', help='job file to read, if empty, stdin is used')
    parser.add_argument('-jobname', type=str, help='job name', default='job')
    parser.add_argument('-jobline', type=int, help='set the number of lines to form a job', default=1)
    parser.add_argument('-queue', type=str, help='submit queue', default='st.q')
    parser.add_argument('-project', type=str, help='project id', default='P18Z10200N0127')
    parser.add_argument('-resource', type=str, help='resourse requirment', default='vf=50M,p=1')
    parser.add_argument('-logdir', type=str, default=None, help='array job log directory')
    args = parser.parse_args()

    assert re.match(r'vf=[\d\.]+\w,p=\d+', args.resource), "please specific memory usage and number processor"
    assert not re.match(r'^\d+', args.jobname), "array job name cannot start with a digit"
    assert args.jobline >= 1, "a job line can't to be zero"

    args.jobname += "_" + datetime.now().strftime("%Y%m%d%H%M%S")

    if args.logdir is None:
        args.logdir = args.jobname + "_qsub"
    else:
        args.logdir = args.logdir.rstrip("/")
        if (args.logdir == ".") or (args.logdir == "~") or (args.logdir == os.path.expanduser("~")):
            args.logdir = os.path.join(args.logdir, args.jobname + "_qsub")
    #if os.path.exists(args.logdir):
    #    os.remove(args.logdir)
    #print(args.logdir)
    os.makedirs(args.logdir)

    total_job_num = parse_job(args.jobname, args.jobfile, args.jobline, args.logdir)
    submit_job(args.jobname, total_job_num, args.queue, args.project, args.resource, args.logdir)


if __name__ == '__main__':
    main()
