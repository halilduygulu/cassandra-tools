#!/usr/bin/env python

__author__ = "Jim Plush, Kyle Quest"
__copyright__ = "Copyright 2015, CrowdStrike"
__license__ = "Apache 2.0"
__version__ = "1.0.0"
__maintainer__ = "Jim Plush"
__status__ = "Production"

#this file will allow you to launch an EC2 instance that's configured as a Cassandra node
import boto,boto.ec2,time,sys,os,stat,re,json,pprint
from boto.ec2.blockdevicemapping import BlockDeviceType
from boto.ec2.blockdevicemapping import BlockDeviceMapping
from boto.ec2.blockdevicemapping import EBSBlockDeviceType

from fabric.api import *
import argparse
import logging
import sys


log = logging.getLogger(__name__)
out_hdlr = logging.StreamHandler(sys.stdout)
out_hdlr.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
out_hdlr.setLevel(logging.INFO)
log.addHandler(out_hdlr)
log.setLevel(logging.INFO)

settings = {}

def AwsLoadCreds(configSpec):
    if configSpec['Verbose']:
        log.info("[AwsLoadCreds]")

    awsKey = os.environ.get('AWS_ACCESS_KEY_ID','')
    awsSecret = os.environ.get('AWS_SECRET_ACCESS_KEY','')

    if (awsKey != '') and (awsSecret != ''):
        return awsKey,awsSecret

    return awsKey,awsSecret


def AwsConnect(configSpec,awsKey,awsSecret):
    if configSpec['Verbose']:
        logging.info("[AwsConnect]")

    targetRegion = None
    if 'Region' in configSpec:
        targetRegion = boto.ec2.get_region(configSpec['Region'])

    conn = boto.connect_ec2(awsKey,awsSecret,region = targetRegion)
    return conn


def AwsStartFromConfigSpec(args, configSpec):
    global settings,aws, log


    if configSpec['Verbose']:
        log.info("[AwsStartInstanceImpl]")

    k, s = AwsLoadCreds(configSpec)
    conn = AwsConnect(configSpec,k,s)

    reservation = None
    subnetId = None
    securityGroups = None
    securityGroupIds = None
    shutdownBehavior = None

    #NOTE: shutdown behavior can only be defined for EBS backed instances
    if 'EbsInstance' in configSpec:
        if configSpec['EbsInstance']:
            shutdownBehavior = 'terminate'
    else:
        shutdownBehavior = 'stop'


    if configSpec['InVpc']:
        securityGroupIds = configSpec['SecurityGroups']
    else:
        securityGroups = configSpec['SecurityGroups']

    deviceMap = None
    ebsOptimized = False
    if 'EBSRaid' in configSpec and configSpec["EBSRaid"]:
        ebsOptimized = True
        deviceMap = BlockDeviceMapping()
        if configSpec['InstanceType'] == 'm3.2xlarge':
            print "Mapping EBS block devices for m3.2xlarge"
            ep0 = BlockDeviceType()
            ep0.ephemeral_name = 'ephemeral0'
            deviceMap['/dev/xvdb'] = ep0
            ep1 = BlockDeviceType()
            ep1.ephemeral_name = 'ephemeral1'
            deviceMap['/dev/xvdc'] = ep1

        if configSpec['InstanceType'] == 'c3.4xlarge':
            print "Mapping EBS block devices for c3.4xlarge"
            ep0 = BlockDeviceType()
            ep0.ephemeral_name = 'ephemeral0'
            deviceMap['/dev/xvdb'] = ep0
            ep1 = BlockDeviceType()
            ep1.ephemeral_name = 'ephemeral1'
            deviceMap['/dev/xvdc'] = ep1





    if 'EphemeralRaid' in configSpec and configSpec['EphemeralRaid']:
        if configSpec['Verbose']:
            log.info( "AwsStartFromConfigSpec(): configSpec['EphemeralRaid']=%s (%s)" % (configSpec['EphemeralRaid'],configSpec['InstanceType']))
        deviceMap = BlockDeviceMapping()
        if configSpec['InstanceType'] == 'm1.xlarge':
            ep0 = BlockDeviceType()
            ep0.ephemeral_name = 'ephemeral0'
            deviceMap['/dev/sdb'] = ep0
            ep1 = BlockDeviceType()
            ep1.ephemeral_name = 'ephemeral1'
            deviceMap['/dev/sdc'] = ep1
            ep2 = BlockDeviceType()
            ep2.ephemeral_name = 'ephemeral2'
            deviceMap['/dev/sdd'] = ep2
            ep3 = BlockDeviceType()
            ep3.ephemeral_name = 'ephemeral3'
            deviceMap['/dev/sde'] = ep3
        elif configSpec['InstanceType'] == 'm1.large':
            ep0 = BlockDeviceType()
            ep0.ephemeral_name = 'ephemeral0'
            deviceMap['/dev/sdb'] = ep0
            ep1 = BlockDeviceType()
            ep1.ephemeral_name = 'ephemeral1'
            deviceMap['/dev/sdc'] = ep1
        elif configSpec['InstanceType'] == 'c3.8xlarge':
            ep0 = BlockDeviceType()
            ep0.ephemeral_name = 'ephemeral0'
            deviceMap['/dev/sdb'] = ep0
            ep1 = BlockDeviceType()
            ep1.ephemeral_name = 'ephemeral1'
            deviceMap['/dev/sdc'] = ep1
        elif configSpec['InstanceType'] == 'i2.2xlarge':
            ep0 = BlockDeviceType()
            ep0.ephemeral_name = 'ephemeral0'
            deviceMap['/dev/xvdb'] = ep0
            ep1 = BlockDeviceType()
            ep1.ephemeral_name = 'ephemeral1'
            deviceMap['/dev/xvdc'] = ep1
        else:
            log.error("AwsStartFromConfigSpec(): unexpected instance type => %s" % configSpec['InstanceType'])
            sys.exit(-1)


    ami_image = configSpec['AmiId']

    aws_az = args.az

    subnet = configSpec['Subnets'][aws_az]['subnet']

    log.info("Using AZ: {0}".format(aws_az))

    try:
        log.info("Launching in AZ: {0}".format(aws_az))
        if args.dryrun == True:
          log.warn("DRY RUN, NOT LAUNCHING....")
          sys.exit()
        else:
          print "DEVICE MAPPING"
          print deviceMap
          print
          #sys.exit()
          reservation = conn.run_instances(
                                         ami_image,
                                         placement=aws_az,
                                         min_count=settings['total-nodes'],
                                         max_count=settings['total-nodes'],
                                         instance_initiated_shutdown_behavior = shutdownBehavior,
                                         instance_type=configSpec['InstanceType'],
                                         key_name=configSpec['SshKeys']['KeyPairName'],
                                         subnet_id=subnet,
                                         security_groups=securityGroups,
                                         security_group_ids=securityGroupIds,
                                         ebs_optimized=ebsOptimized,
                                         block_device_map = deviceMap)

    except boto.exception.EC2ResponseError as x:
        log.error("Failed to start an AWS instance: %s" % x)
        return


    except Exception as e:
        print "Got reservation error"
        print e
        return


    if reservation:
        log.info('Waiting for VM instances to start...')

    time.sleep(15)

    #for ri in reservation.instances:
    #    pprint.pprint(ri.__dict__)


    instanceSetInfo = []
    instanceIds = [] # stores a list of all the active instanceids we can use to attach ebs volumes to
    instanceIps = []
    isFirst = True
    firstNodeIp = None
    for i, instance in enumerate(reservation.instances):
        status = instance.update()
        while not status == 'running':
            log.info("Instance status: %s" % status)
            if status == 'terminated':
                sys.exit(-1)

            time.sleep(4)
            status = instance.update()

        if configSpec['Verbose']:
            print "Instance ID: %s" % instance.id
            print "Instance Private IP: %s" % instance.private_ip_address
            print "Instance Public DNS: %s" % instance.public_dns_name

        if isFirst:
            firstNodeIp = instance.private_ip_address



        info = {'Id':instance.id, 'PrivateIp': instance.private_ip_address,'PublicDnsName': instance.public_dns_name, 
                'FirstNode': isFirst}
        isFirst = False
        instanceSetInfo.append(info)
        instanceIds.append(instance.id)
        instanceIps.append(instance.private_ip_address)

    tags = configSpec['Tags']

    for instance in reservation.instances:
        conn.create_tags([instance.id], tags)


    ips = ",".join(instanceIps)
    print "IPS ARE"
    print "-"*10
    print ips
    print "-"*10
    print
    for ip in instanceIps:
        print ip
    print



def Run(args):
    global settings
    configFileName = settings['json']
    if len(configFileName) < 3:
        sys.exit('Bad configFileName: %s' % configFileName)

    configPath = ''
    if configFileName[0] == '/':
        configPath = configFileName
    else:
        configPath = os.path.join(os.path.dirname(os.path.abspath(__file__)),configFileName)

    if not os.path.isfile(configPath):
        sys.exit('%s not found, please select a valid configuration' % configPath)

    configSpec = None
    with open(configPath,'r') as f:
        configSpec = json.load(f)

    if configSpec is None:
        sys.exit('Config spec (%s) is not loaded... exiting.' % configPath)

    if configSpec['Verbose']:
        log.info("Starting Cassandra Cluster (with config: %s)..." % configPath)

    AwsStartFromConfigSpec(args, configSpec)

    if configSpec['Verbose']:
         log.info("Done starting Cassandra Cluster!")


def check_for_errors(args):
    global aws
    if args.nodes == 0:
      log.error("You need to at least launch one node, you have no nodes being launched")
      sys.exit()


    if args.balanced and get_total_nodes(args) % 3 != 0:
        log.error("In --balanced mode you must have your nodes divisible by 3 as we launch across 3 availability zones")
        sys.exit()

    log.info("ARGS: " + str(args))



def set_options(args):
  global settings
  log.info("setting options based on params..." )
  settings['json'] = "configs/config-%s.json" % args.config

  settings['total-nodes'] = args.nodes
  log.info("SETTINGS: " + str(settings))

def launchNodeCmd(args): 
    check_for_errors(args)
    set_options(args)
    Run(args)




helpdesc = '''

This script automates the building of cassandra nodes in a cluster

requirements:
  - boto is required to be installed to run this and fabric
  - pip install -r requirements.txt

launch 1 cassandra node into us-east-1a
python launch.py launch --env=c4-ebs-hvm --cass=1 --dryrun --az=us-east-1a


todo get balanced working to say --balanced and 60 nodes and it auto creates reservations in n azs from the config
'''

parser = argparse.ArgumentParser(description=helpdesc,
    formatter_class=argparse.RawDescriptionHelpFormatter)
subparsers = parser.add_subparsers(help='sub-command help')

packageparser = subparsers.add_parser('launch', help='Builds a node(s) in the cassandra cluster')
packageparser.add_argument('--nodes', '-c', type=int, required=True, default=0, help="number of regular cassandra nodes you want in the cluster")
packageparser.add_argument('--env', '-e', required=False, default="summit-dev")
packageparser.add_argument('--config', '-cfg', required=True)
packageparser.add_argument('--az', '-az', required=True, default="DEFAULT", help="Allows you to specify what AZ you want to deploy to us-east-1a for example")
packageparser.add_argument('--balanced', '-bal', required=False, default=False, action='store_true', help="If you want to make sure your nodes are balanced across AZs")
packageparser.add_argument('--dryrun', '-dr', required=False, default=False,action='store_true', help="If you want to just print out the debug and everything but launch the real deal")


packageparser.set_defaults(func=launchNodeCmd)


args = parser.parse_args()
args.func(args)


