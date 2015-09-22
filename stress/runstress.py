import sys
import subprocess
import os
import select
import time
import signal
import argparse


__author__ = "Jim Plush"
__copyright__ = "Copyright 2015, CrowdStrike"
__license__ = "Apache 2.0"
__version__ = "1.0.0"
__maintainer__ = "Jim Plush"
__status__ = "Production"

stress_location = '/home/ubuntu/apache-cassandra-2.1.5/tools/bin/'


#stress for weather station 95% write %5 read load
cmd_weather_95 = '{stress}cassandra-stress user duration=100000m cl=ONE profile=/home/ubuntu/summit_weather_stress.yaml ops\(insert=19,simple=1\) no-warmup {popseq}  -mode native cql3 -node {seednode} -rate threads={threads}  -errors ignore'

# weather pure write
cmd_weather = '{stress}cassandra-stress user duration=100000m cl=ONE profile=/home/ubuntu/summit_weather_stress.yaml ops\(insert=1\) no-warmup {popseq}  -mode native cql3 -node {seednode} -rate threads={threads} -errors ignore'

cmd_stress = '{stress}cassandra-stress user duration=100000m cl=ONE profile=/home/ubuntu/summit_stress.yaml ops\(insert=1\) no-warmup  {popseq} -mode native cql3 -node {seednode} -rate threads={threads}  -errors ignore'

cmd_stress95 = '{stress}cassandra-stress user duration=100000m cl=ONE profile=/home/ubuntu/summit_stress.yaml ops\(insert=19,simple=1\) no-warmup  {popseq} -mode native cql3 -node {seednode} -rate threads={threads}  -errors ignore'

# 10% writes, 90% reads
cmd_stress10 = '{stress}cassandra-stress user duration=100000m cl=ONE profile=/home/ubuntu/summit_stress.yaml ops\(insert=1,simple=9\) no-warmup  {popseq} -mode native cql3 -node {seednode} -rate threads={threads}  -errors ignore'

# 100% read
cmd_stressread = '{stress}cassandra-stress user duration=100000m cl=ONE profile=/home/ubuntu/summit_stress.yaml ops\(simple=1\) no-warmup  {popseq} -mode native cql3 -node {seednode} -rate threads={threads}  -errors ignore'


profiles = {
    "weather": cmd_weather,
    "weather95": cmd_weather_95,
    "stress": cmd_stress,
    "stress95": cmd_stress95,
    "stress10": cmd_stress10,
    "stressread": cmd_stressread
}


restarts = 0

def runstress(args):
    global restarts

    if args.profile not in profiles:
        print "Invalid profile"
        sys.exit(1)

    cmd_to_run = profiles[args.profile]


    pop_sub = ""

    # try and get from environment
    nodenum = os.environ.get('NODENUM')
    if nodenum is not None:
        print "convert to int"
        nodenum = int(nodenum)

    if args.nodenum is not None:
        nodenum = args.nodenum

    if nodenum is None:
        nodenum = 1

    end = args.basepop * nodenum
    start = 1
    if nodenum > 1:
        start = (end - args.basepop) + 1
    pop_sub = "-pop seq={}..{}".format(start, end)

    #parse out seednode
    cmd_to_run = cmd_to_run.format(stress=stress_location, seednode=args.seednode, popseq=pop_sub, threads=args.threads)

    print "Going to run {}".format(cmd_to_run)

 
    #get rid of existing java procs
    os.system("sudo kill -9 `ps -aux | grep java  | awk '{print $2}'`")
    p = subprocess.Popen(cmd_to_run,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, preexec_fn=os.setsid)
    while True:
        reads = [p.stdout.fileno(), p.stderr.fileno()]
        ret = select.select(reads, [], [])

        for fd in ret[0]:
            if fd == p.stdout.fileno():
                line = p.stdout.readline()
                sys.stdout.write('stdout: ' + line)

            if fd == p.stderr.fileno():
                line = p.stderr.readline()
                sys.stderr.write('stderr: ' + line)

                if "AssertionError" in line:
                    print "GOT EXCEPTION RESTARTS [{}] RESTARTING.....".format(restarts)
                    restarts += 1
                    try:
                        print "Forced kill"
                        return
                        #os.killpg(p.pid, signal.SIGTERM)

                    except OSError, e:
                        print "Terminated gracefully"
                        time.sleep(5)
                        #sys.exit(1)
                        return

        if p.poll() != None:
            break

def exit_gracefully(signum, frame):
    print "Terminating program in background"
    os.system("pkill -f stress")


"""

python runstress.py --profile=stress --seednode=10.10.10.XX --nodenum=4

this script will try and grab the nodenumber from the environment
export NODENUM=1
that will help seed unique values from each stress writer to make sure you're writing unique keys

it runs in a continuous loop, due to the fact C Stress errors out weirdly and if you have this running in the background you don't want 
to have to babysit it.

"""

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='runs load testing')
    parser.add_argument('--profile', '-p', required=True, help='what profile do you want to run?' )
    parser.add_argument('--seednode', '-s', required=True, help='what seed node are we pointing to in the C* cluster?' )
    parser.add_argument('--nodenum', '-n', required=False, type=int, help='if running on multiple nodes, need a seed number to avoid dupe writes' )
    parser.add_argument('--basepop', '-b', required=False, type=int, default=100000000, help='base number used for population sequence, default 100M' )
    parser.add_argument('--threads', '-t', required=False, type=int, default=1000, help='number of threads to run, default 1,000' )

    args = parser.parse_args()

    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, exit_gracefully)

    while True:
        runstress(args)
