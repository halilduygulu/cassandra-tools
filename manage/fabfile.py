from fabric.api import sudo, run, prompt, env, task, put, execute, runs_once, parallel, settings, prompt
from fabric.contrib.files import append, sed, upload_template
from fabric.colors import green, red, cyan
import time
import os
import sys
import glob
import os.path


__author__ = "Jim Plush"
__copyright__ = "Copyright 2015, CrowdStrike"
__license__ = "Apache 2.0"
__version__ = "1.0.0"
__maintainer__ = "Jim Plush"
__status__ = "Production"
__credits__ = ["github.com/riptano/ComboAMI"]

env.colorize_errors = True
env.forward_agent = True

'''
#install a fresh cluster
fab -u ubuntu  bootstrapcass21:config=c4-highperf

# set the seeds for the cluster before it starts
fab -u ubuntu  set_seeds:config=c4-highperf,seeds='10.10.10.XX'

#start up cassandra
fab -u ubuntu  cmd:config=c4-highperf,cmd="sudo service cassandra start"

# get the running process PIDs for c*
fab -u ubuntu  getrunning:config=c4-highperf


fab -u ubuntu  putstress:config=c4-ebs-hvm

'''

# CONSTANTS
config_dir = "/etc/cassandra"

@task
def _set_hosts(config):
    hostfile = "configs/{}/hostfile.txt".format(config)
    hostfile = prompt('Specify hostfile you want to perform operation on. Note you can use something like /tmp/hosts.txt', 'hostfile', default=hostfile)

    green("Setting hosts from [{}]".format(hostfile))
    hosts = open(hostfile, 'r').readlines()
    hosts = [x.strip() for x in hosts]
    env.hosts = hosts
    print hosts

@task
def _set_hosts_stress():
    hostfile = "../stress/hostfile.txt"
    hostfile = prompt('Specify Stress hostfile you want to perform operation on. Note you can use something like /tmp/hosts.txt', 'hostfile', default=hostfile)

    green("Setting hosts from [{}]".format(hostfile))
    hosts = open(hostfile, 'r').readlines()
    hosts = [x.strip() for x in hosts]
    env.hosts = hosts
    print hosts

''' WORKS WITH FULL HOSTS FILE '''

@task
def bootstrapcass20(config):
    ''' Bootstraps a new node with everything a growing node needs to live in this world '''
    _set_hosts(config)
    execute(_bootstrapcass)
    execute(_install_cassandra_2_0)
    execute(_setup_disk_and_perf)
    execute(setup_defaults, config=config)
    execute(_yamlfile, config=config)
    execute(_envfile, config=config)
    execute(_agentip, config=config)


@task
def bootstrapcass21(config):
    ''' Bootstraps a new node with everything a growing node needs to live in this world with 2.1 '''
    _set_hosts(config)
    execute(_bootstrapcass)
    execute(_install_cassandra_2_1)
    execute(_setup_disk_and_perf)
    execute(setup_defaults, config=config)
    execute(_yamlfile, config=config)
    execute(_envfile, config=config)
    execute(_agentip, config=config)



@task
def bootstrapcass21_i2(config):
    ''' Bootstraps a new node with everything a growing node needs to live in this world  with 2.1 for i2.2xl for raid0'''
    _set_hosts(config)
    execute(_bootstrapcass)
    execute(_install_cassandra_2_1)
    execute(_setup_disk_and_perf_i2)
    execute(setup_defaults, config=config)
    execute(_yamlfile, config=config)
    execute(_envfile, config=config)
    execute(_agentip, config=config)




@task
def configs(config):
    '''
    This task will configure the yaml and env.sh scripts at the same time
    '''
    _set_hosts(config)
    execute(setup_defaults, config=config)
    execute(_yamlfile, config=config)
    execute(_envfile, config=config)
    execute(_agentip, config=config)


@task
def dseperf(config):
    _set_hosts(config)
    execute(_dseperf)
    #`execute(_dirty, config=config)
    #execute(_yamlfile, config=config)
    #execute(_envfile, config=config)
    #execute(_agentip, config=config)

@task
def installagent(config):
    "installs the DataStax Agent"
    _set_hosts(config)
    execute(_agentip, config=config)
    #execute(_restart_agent)

@task
def install21(config):
    "Installs a complete 2.1 community release"
    _set_hosts(config)
    execute(_cass21)
    execute(_dseperf)
    execute(setup_defaults, config=config)
    execute(_yamlfile, config=config)
    execute(_envfile, config=config)
    execute(_agentip, config=config)

@task
def cass21(config):
    _set_hosts(config)
    execute(_cass21)

@task
def dirty(config):
    _set_hosts(config)
    execute(_dirty, config=config)




@task
def opscenter_address(config):
    """
    set the opscenter address in the address.yaml file for the datastax agent
    """
    _set_hosts(config)
    execute(_agentip, config=config)

@task
def set_seeds(config, seeds):
    """
    Manually set the seeds you want to use for your yaml file:  fab -i ~/.ssh/id_cass -u ubuntu -P set_seeds:config=c4-ebs-hvm,seeds='10.10.10.x'
    """
    _set_hosts(config)
    execute(_set_seeds, seeds=seeds)

@task
def restart(config):
    """
    Restart DSE and The DataStax Agent: fab -i ~/.ssh/yourkey -u ubuntu -P set_seeds:config=c4-ebs-hvm
    """
    _set_hosts(config)
    execute(_restart_dse)
    execute(_restart_agent)



@task
def restart_cass(config, sleep=0):
    """ Restart Cassandra only """
    _set_hosts(config)
    execute(_restart_cass, sleep=sleep)

@task
def start_cass(config, sleep=1):
    """ Restart Cassandra only """
    _set_hosts(config)
    execute(_start_cass, sleep=sleep)


@task
def stop(config):
    """
    Stop DSE across the hosts
    """
    _set_hosts(config)
    execute(_stop)

@task
def start(config):
    """ Start DSE only """
    _set_hosts(config)
    execute(_start)

@task
def restart_agent(config):
    """ Restart Datastax Opscenter Agent """
    _set_hosts(config)
    execute(_restart_agent)


@task
def setxen(config):
    """ Revert to XEN clocksource """
    _set_hosts(config)
    execute(_setxen)


@task
def installstress():
    """ Installs the Stress code and runner files """
    _set_hosts_stress()
    execute(_installstress)

@task
def putstress():
    """ Puts a stress yaml file on the stress runner boxes """
    _set_hosts_stress()
    execute(_putstress)



@task
def push_jar(config):
    """ Push a custom jar up to the servers """
    _set_hosts(config)
    execute(push_jar_impl, config=config)



@task
def maskcpu(config):
    """
    Mask out the 0 CPU. You can only run this one while cassandra is runnning, because you need the PID
    """
    _set_hosts(config)
    execute(_maskCPU)


@task
@runs_once
def getrunning(config):
    """
    Gets all the running Cassandra processes so you know if C* is fully running across the cluster
    """
    _set_hosts(config)
    results = execute(_getpid)
    i = 1
    completed = 0
    for host, result in results.items():
        print "host {} [{}] pid is [{}]".format(i, host, result.strip())
        i += 1
        if len(result) > 1:
            completed += 1

    print "-"*50
    print "{} out of {} hosts are running C*".format(completed, len(results))
    print "-"*50


@task
@runs_once
def cmd(config, cmd):
    """ EXECS a unix command on the remote hosts: fab -i ~/.ssh/id_cass -u ubuntu cmd:config=c4-ebs-hvm,cmd="df -h" """

    # Examples
    # fab cmd:config=c4-ebs-hvm,cmd="java -version 2>&1 | grep version  | awk '{print $NF}'"
    # fab cmd:config=c4-ebs-hvm,cmd="grep MAX_HEAP_SIZE /etc/dse/cassandra/cassandra-env.sh | grep G"

    # delete commit log with lots of files
    #fab -u ubuntu  cmd:config=c4-ebs-hvm,cmd="find /raid0/cassandra/commitlog -name '*.log' -print0 | xargs -0 sudo rm"

    # remove files
    # fab  -u ubuntu cmd:c4-ebs-hvm,cmd="find /raid0/cassandra/commitlog/* -name "*.log" -print0 | xargs -0 sudo rm"
    _set_hosts(config)
    results = execute(_exec, cmd=cmd)
    i = 1
    for host, result in results.items():
        print "host {} [{}] result is [{}]".format(i, host, result.strip())
        i += 1





''' INDIVIDUAL TASKS '''

@task
@parallel
def _setxen():
    """ revert back to xen clocksource to test perf """
    sudo("echo tsc > /sys/devices/system/clocksource/clocksource0/current_clocksource")

@task
@parallel
def _cass21():
    run('echo "deb http://debian.datastax.com/community stable main" | sudo tee -a /etc/apt/sources.list.d/cassandra.sources.list')
    run('curl -L http://debian.datastax.com/debian/repo_key | sudo apt-key add -')
    sudo("apt-get update")
    #sudo("apt-get purge --force-yes -y dse-libcassandra")
    sudo("sudo apt-get install --force-yes -y dsc21 datastax-agent")
    with settings(warn_only=True):
        sudo("service cassandra stop")
    sudo("rm -rf /mnt/cassandra/data/system/*")
    sudo("rm -rf /mnt/cassandra/data/dse*")

@task
@parallel
def _dseperf():
    """ based on updated DSE performance doc from 4/23/2015 """
    sudo("add-apt-repository -y ppa:webupd8team/java")
    sudo("apt-get update")
    sudo("apt-get install -y oracle-java8-installer oracle-java8-set-default")

    sudo("echo tsc > /sys/devices/system/clocksource/clocksource0/current_clocksource")

    sudo("apt-get install -y schedtool")

    #sudo('echo "vm.dirty_expire_centisecs = 10" >> /etc/sysctl.d/dirty.conf')
    #sudo("sysctl -p /etc/sysctl.d/dirty.conf")

    # FIX HOSTS FILE for metrics to record remote IP properly
    host  = 'ip-%s' % env.host_string.replace('.','-')
    sudo('sed -i "/127/c\\127.0.0.1 {} localhost" /etc/hosts'.format(host))


@task
@parallel
def _install_cassandra_2_0():
     #install cassandra
    run('echo "deb http://debian.datastax.com/community stable main" | sudo tee -a /etc/apt/sources.list.d/cassandra.sources.list')
    run('curl -L http://debian.datastax.com/debian/repo_key | sudo apt-key add -')
    sudo("apt-get update")
    sudo("sudo apt-get install --force-yes -y dsc20=2.0.12-1 cassandra=2.0.12 datastax-agent")
    with settings(warn_only=True):
        sudo("service cassandra stop")
    sudo("rm -rf /mnt/cassandra/data/system/*")
    sudo("rm -rf /mnt/cassandra/data/dse*")

    with settings(warn_only=True):
        sudo("mv /etc/security/limits.d/cassandra.conf /etc/security/limits.d/cassandra.conf.bak")

    run('echo "cassandra - memlock unlimited" | sudo tee -a /etc/security/limits.d/cassandra.conf')
    run('echo "cassandra - nofile 100000" | sudo tee -a /etc/security/limits.d/cassandra.conf')
    run('echo "cassandra - nproc 32768" | sudo tee -a /etc/security/limits.d/cassandra.conf')
    run('echo "cassandra - as unlimited" | sudo tee -a /etc/security/limits.d/cassandra.conf')

    # for Ubuntu
    run('echo "root - memlock unlimited" | sudo tee -a /etc/security/limits.d/cassandra.conf')
    run('echo "root - nofile 100000" | sudo tee -a /etc/security/limits.d/cassandra.conf')
    run('echo "root - nproc 32768" | sudo tee -a /etc/security/limits.d/cassandra.conf')
    run('echo "root - as unlimited" | sudo tee -a /etc/security/limits.d/cassandra.conf')



@task
@parallel
def _install_cassandra_2_1():
     #install cassandra

    run('echo "deb http://debian.datastax.com/community stable main" | sudo tee -a /etc/apt/sources.list.d/cassandra.sources.list')
    run('curl -L http://debian.datastax.com/debian/repo_key | sudo apt-key add -')
    sudo("apt-get update")
    sudo("sudo apt-get install --force-yes -y dsc21=2.1.9-1 cassandra=2.1.9 cassandra-tools=2.1.9 datastax-agent")
    with settings(warn_only=True):
        sudo("service cassandra stop")
    sudo("rm -rf /mnt/cassandra/data/system/*")
    sudo("rm -rf /mnt/cassandra/data/dse*")

    with settings(warn_only=True):
        sudo("mv /etc/security/limits.d/cassandra.conf /etc/security/limits.d/cassandra.conf.bak")

    run('echo "cassandra - memlock unlimited" | sudo tee -a /etc/security/limits.d/cassandra.conf')
    run('echo "cassandra - nofile 100000" | sudo tee -a /etc/security/limits.d/cassandra.conf')
    run('echo "cassandra - nproc 32768" | sudo tee -a /etc/security/limits.d/cassandra.conf')
    run('echo "cassandra - as unlimited" | sudo tee -a /etc/security/limits.d/cassandra.conf')

    # for Ubuntu
    run('echo "root - memlock unlimited" | sudo tee -a /etc/security/limits.d/cassandra.conf')
    run('echo "root - nofile 100000" | sudo tee -a /etc/security/limits.d/cassandra.conf')
    run('echo "root - nproc 32768" | sudo tee -a /etc/security/limits.d/cassandra.conf')
    run('echo "root - as unlimited" | sudo tee -a /etc/security/limits.d/cassandra.conf')



@task
@parallel
def _bootstrapcass():

    # FIX HOSTS FILE for metrics to record remote IP properly
    host  = 'ip-%s' % env.host_string.replace('.','-')
    sudo('sed -i "/127/c\\127.0.0.1 {} localhost" /etc/hosts'.format(host))

    sudo("apt-get update")

    # install required packages
    sudo("""apt-get -y install --fix-missing libjna-java binutils pssh pbzip2 xfsprogs schedtool zip unzip ruby openssl ruby-dev libruby1.9.1 curl liblzo2-dev ntp subversion python-pip  unzip xfsprogs ethtool""")

    # install sysadmin tools
    sudo("apt-get -y install --fix-missing iftop sysstat htop s3cmd nethogs nmon dstat tree collectd collectd-utils")
    sudo("echo oracle-java8-installer shared/accepted-oracle-license-v1-1 select true | sudo /usr/bin/debconf-set-selections")
    sudo("add-apt-repository -y ppa:webupd8team/java")
    sudo("apt-get update")
    sudo("apt-get install -y oracle-java8-installer oracle-java8-set-default")
    sudo("update-java-alternatives -s java-8-oracle")

    #fix clocksource -> network performance
    sudo("echo tsc > /sys/devices/system/clocksource/clocksource0/current_clocksource")

@task
@parallel
def _setup_disk_and_perf_i2():
    ''' 
    installs two ephemeral drives as raid0 
    todo: set this up to work across all i2 series with n number of ssd drives for raid0

    '''
    sudo("DEBIAN_FRONTEND=noninteractive apt-get install -y --fix-missing mdadm xfsprogs")
    sudo("mkdir /raid0")

    sudo("/usr/bin/yes|/sbin/mdadm --create /dev/md0 --level=0 -c256 --raid-devices=2 /dev/xvdb /dev/xvdc")
    sudo("echo 'DEVICE /dev/xvdb /dev/xvdc' > /etc/mdadm.conf")
    sudo("/sbin/mdadm --detail --scan >> /etc/mdadm.conf")
    sudo("/sbin/blockdev --setra 65536 /dev/md0")
    sudo("mkfs.xfs -f /dev/md0")
    sudo("/bin/mount -t xfs -o noatime /dev/md0 /raid0")
    sudo("/bin/mv /etc/fstab /etc/fstab.orig")
    sudo("/bin/sed '/\/mnt/ c /dev/md0 /raid0 xfs defaults 0 0' < /etc/fstab.orig > /etc/fstab")
    sudo("mkdir -p /raid0/cassandra/data")
    sudo("mkdir -p /raid0/cassandra/commitlog")
    sudo("mkdir -p /raid0/cassandra/saved_caches")
    sudo("chown -R cassandra:cassandra /raid0")

@task
@parallel
def _setup_disk_and_perf():
    # MOUNT DRIVES 1 4TB for data on /mnt
    # 1 200G 1500 PIOPS for commit log /
    sudo("mkdir -p /mnt/cassandra")
    sudo("mkdir -p /mnt/cassandra/saved_caches")
    sudo("chown -R cassandra:cassandra /mnt")

    #DATA DIRECTORY
    device = "/dev/xvdf"
    mnt_point = "/mnt"
    sudo('mkdir -p {0}'.format(mnt_point))
    sudo('mkfs.xfs -f {0}'.format(device))
    run("echo '{0}\t{1}\txfs\tdefaults,nobootwait,noatime\t0\t0' | sudo tee -a /etc/fstab".format(device, mnt_point))
    sudo('sudo mount -a')
    sudo('sudo mkdir -p /mnt/cassandra')
    sudo('sudo chown -R cassandra:cassandra {0}'.format(os.path.join(mnt_point, 'cassandra'))) 
    print "format_ebs_volume {} completed!".format(device)

    #COMMIT LOG
    device = "/dev/xvdk"
    mnt_point = "/raid0"
    sudo('mkdir -p {0}'.format(mnt_point))
    sudo('mkfs.xfs -f {0}'.format(device))
    run("echo '{0}\t{1}\txfs\tdefaults,nobootwait,noatime\t0\t0' | sudo tee -a /etc/fstab".format(device, mnt_point))
    sudo('sudo mount -a')
    sudo('sudo mkdir -p /raid0/cassandra')
    sudo('sudo chown -R cassandra:cassandra {0}'.format(os.path.join(mnt_point, 'cassandra'))) 
    print "format_ebs_volume {} completed!".format(device)








@task
@parallel
def _exec(cmd):
    with settings(warn_only=True):
        return run(cmd)



@task
@parallel
def _set_seeds(seeds):
    global config_dir
    seed_str = ",".join(seeds.split(":"))
    print seed_str
    dest_file = "{}/cassandra.yaml".format(config_dir)
    aftertext = 'seeds: "{}"'.format(seed_str) + "}"
    sed(dest_file,before='seeds.*$',after=aftertext,use_sudo=True,backup='')




@parallel
@task
def _restart_cass(sleep):
    with settings(warn_only=True):
        print "Restarting {} with a sleep of {}".format(env.host_string, sleep)
        sudo("service cassandra restart")
        time.sleep(float(sleep))

#@parallel
@task
def _start_cass(sleep):
    with settings(warn_only=True):
        print "Starting {} with a sleep of {}".format(env.host_string, sleep)
        sudo("service cassandra start")
        time.sleep(float(sleep))

@task
def _restart_dse(sleep):
    with settings(warn_only=True):
        print "Restarting {} with a sleep of {}".format(env.host_string, sleep)
        sudo("service dse restart")
        time.sleep(float(sleep))


@task
@parallel
def _restart_agent():
    with settings(warn_only=True):
        sudo("service datastax-agent restart")
        time.sleep(10)


@task
@parallel
def _stop():
    sudo("service dse stop")


@task
def _start():
    sudo("service dse start")


@task
@parallel
def _getpid():
    return run("ps -ef | grep cassandra | grep jamm | grep -v grep | awk  '{print $2}'").strip()


@task
@parallel
def _maskCPU():
    '''
    The Linux kernel's process/thread scheduler tries to be completely fair to all running applications. An EC2, all
    interrupts are wired to core0 by default, which means that
    core needs to process any interrupts. Scheduling application threads to run on core0 has an impact on IO latency since
    caches are shared and a kernel IO thread may have to wait for a user thread to finish its time on the CPU
    '''
    pid = run("ps -ef | grep cassandra | grep rmi | grep -v grep | awk  '{print $2}'").strip()
    print "Cassandra PID is [{}]".format(pid)
    # 15 on a 16 core cluster!, 7 otherwise
    sudo("taskset -apc 1-15 {}".format(pid))


@task
@parallel
def _putstress():
     ''' puts latest stress files on stress machines '''
     pattern = "../stress/*"
     files = glob.glob(pattern)
     for src in files:
        filename = os.path.basename(src)
        dest_file = "/home/ubuntu/{}".format(filename)
        if ".py" in src or ".yaml" in src:
            put(src, dest_file)

@task
@parallel
def _installstress():
     ''' installs a stress files on stress machines '''
     src = "../stress/CASSANDRA-STRESS-2-1.tgz"
     dest = "~/STRESS.tgz"
     put(src, dest)
     run("tar -xzf ~/STRESS.tgz")
     execute(_putstress)


@task
@parallel
def push_jar_impl(config):
    ''' use this if we have a custom jar we want to upload '''
    libdir = "/usr/share/cassandra"
    old = "apache-cassandra-2.1.9.jar"
    new = "apache-cassandra-2.1.9.jar" # we want this new jar running
    src_file = "configs/{}/{}".format(config, new)
    dest_file = "{}/{}".format(libdir, new)
    put(src_file, dest_file, use_sudo=True)

@task
@parallel
def setup_defaults(config):
    ''' sets up directories or files that need to be maintained on the server '''
    host = env.host_string
    sudo("chown -R cassandra:cassandra /var/log/cassandra")

    #PUSH COLLECTD
    put("configs/{}/collectd.conf".format(config), "/etc/collectd/", use_sudo=True)
    aftertext = 'Hostname "{}"'.format(host)
    dest_file = "/etc/collectd/collectd.conf"
    sed(dest_file,before='Hostname "\$HOST"',after=aftertext,use_sudo=True,backup='')
    sudo("service collectd restart")

    ## SET UP GRAPHITE REPORTING
    sudo("rm -f /usr/share/cassandra/lib/reporter-config*")
    put("configs/{}/reporter-config-2.3.1.jar".format(config), "/usr/share/cassandra/lib/", use_sudo=True)
    put("configs/{}/metrics-graphite-2.2.0.jar".format(config), "/usr/share/cassandra/lib/", use_sudo=True)
    put("configs/{}/metrics.yaml".format(config), "/etc/cassandra/metrics.yaml", use_sudo=True)

    
    run('echo "vm.max_map_count = 131072" | sudo tee -a /etc/sysctl.conf')
    sudo("sysctl -p")

    #disable swap
    sudo("swapoff --all")

@task
@parallel
def setup_defaults_dse46(config):
    ''' sets up directories or files that need to be maintained on the server '''
    sudo("mkdir -p /raid0/cassandra/commitlog")
    sudo("mkdir -p /mnt/cassandra")
    sudo("mkdir -p /mnt/cassandra/saved_caches")
    sudo("chown -R cassandra:cassandra /mnt")
    sudo("chown -R cassandra:cassandra /raid0")
    sudo("chown -R cassandra:cassandra /var/log/cassandra")
    sudo("chown -R cassandra:cassandra /mnt")


@task
@parallel
def _dirty(config):
    # push the custom dirty.conf file for controling page flushing
    src_file = "configs/{}/dirty.conf".format(config)
    green("Syncing dirty.conf file from [{}]".format(src_file))
    dest_file = "/etc/sysctl.d/dirty.conf"
    put(src_file, dest_file, use_sudo=True)
    sudo("sysctl -p {}".format(dest_file))



@task
@parallel
def _yamlfile(config):
    host = env.host_string
    src_file = "configs/{}/cassandra.yaml".format(config)
    green("Syncing YAML File from [{}]".format(src_file))
    dest_file = "{}/cassandra.yaml".format(config_dir)
    put(src_file, dest_file, use_sudo=True)
    aftertext = "rpc_address: {}".format(host)
    sed(dest_file,before='rpc_address: \$HOST',after=aftertext,use_sudo=True,backup=".bak")

    aftertext = "listen_address: {}".format(host)
    sed(dest_file,before='listen_address: \$HOST',after=aftertext,use_sudo=True,backup='')

    # grab the first 3 hosts in the host file and use as seed nodes, could be improved
    seed_str = ",".join(env.hosts[0:3])
    aftertext = 'seeds: "{}"'.format(seed_str)
    sed(dest_file,before='seeds: \$SEEDS',after=aftertext,use_sudo=True,backup='')



@task
@parallel
def _envfile(config):
    src_file = "configs/{}/cassandra-env.sh".format(config)
    green("Syncing ENV File from [{}]".format(src_file))

    dest_file = "{}/cassandra-env.sh".format(config_dir)
    put(src_file, dest_file, use_sudo=True)
    aftertext = 'rmi.server.hostname={}"'.format(env.host_string)
    sed(dest_file,before='rmi.server.hostname=\$HOST"',after=aftertext,use_sudo=True,backup='')



@task
@parallel
def _agentip(config):
    ''' Use this task to control what IP is used for opscenter '''

    src_file = "configs/{}/address.yaml".format(config)
    dest_file = "/var/lib/datastax-agent/conf/address.yaml"

    put(src_file, dest_file, use_sudo=True)

    aftertext = 'hosts: ["{}"]'.format(env.host_string)
    sed(dest_file,before='hosts: \["\$HOST"\]',after=aftertext,use_sudo=True,backup='')


    #sed("/var/lib/datastax-agent/conf/address.yaml", \
        #before="^stomp_interface: .*$", \
        #after="stomp_interface: {}".format(ip), use_sudo=True, backup='.bak')



