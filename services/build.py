# Python Script       : build-all.py
# Author              : Ismael Arab
# Date Written        : September 2014
# This script deploys the cfn infrastructure

# Import the SDK
import boto.cloudformation
import boto.ec2
import boto.vpc
import boto.redshift
import os
import shutil
import sys
import re
import time
import uuid
import ConfigParser
from os.path import expanduser

import argparse

# Custom python modules
sys.path.append("..")
from lib.cfnWrapper import cfnWrapper
#from lib.route53Wrapper import route53Wrapper
import lib.utils
from buildVPC import VPC
from buildEKS import EKS
# from buildCortex import Cortex
# from buildQSense import QSense
# from buildRedshift import Redshift
# from buildRDS import RDS
# from buildCategorizator import buildCategorizator
# from buildEMR import buildEMR
# from buildAirflow import Airflow
# from buildSQS import Sqs

#from lib.redshiftSQL import RedshiftSQL



# Parse arguments
parser = argparse.ArgumentParser(description='Process Arguments.')
parser.add_argument("-ls", "--labelstack", default='', type=str, required = False,
                    help="Stack label.")
parser.add_argument("-ev", "--environment", default='', type=str, required = True,
                    help="Environment.")
parser.add_argument("-ak", "--aws_access_key_id", default='', type=str, required = False,
                    help="Access Key.")
parser.add_argument("-sk", "--aws_secret_access_key", default='', type=str, required = False,
                    help="Secret key.")
parser.add_argument("-rn", "--resource_name", default='', type=str, required = False,
                    help="Name for new redshift cluster.")
parser.add_argument("-sl", "--stacks_list", default=[], type=str, nargs='+', required = True,
                    help="Stacks to update.")
parser.add_argument("-rg", "--aws_region", default='eu-west-1', type=str, required = True,
                    help="AWS Deploy region.")
parser.add_argument("-zn", "--aws_zone", default='', type=str, required = True,
                    help="AWS zone region.")
parser.add_argument("-us", "--update_stack", default='', type=str, required = True,
                    help="Update stack.")
args = parser.parse_args()

# if sys.argv is None or len(sys.argv) < 15:
#     raise ValueError("Usage: python build-all.py LABELSTACK ENVIRONMENT AWSACCESSKEY AWSSECRETKEY STACKDRIVERAPIKEY REUSEVPC UPDATESTACK UPDATESTACKLABEL RESOURCEBUILD CATEGORIZATORBUILD THALAMUSSNAPSHOT RECSYSBUILD MASTERINSTANCE TASKNODE TASKINSTANCE CORENODE COREINSTANCE PROJECTNAME STACKS_LIST REGION")
# else:
#     pass


labelstack = args.labelstack
stacks_list = args.stacks_list
resource_name = args.resource_name.lower()

# CONFIG SECTION
# Set properties

properties_file = 'config/config.properties_'+args.environment

cf_conn = boto.cloudformation.connect_to_region(args.aws_region)

# load configuration properties
config = ConfigParser.RawConfigParser()
config.read(properties_file)


# INIT
######
cfnWrapper = cfnWrapper(cf_conn)
#route53Wrapper = route53Wrapper(aws_access_key_id, aws_secret_access_key, config.get('ROUTE53','route53.domain') )
#vpc_working = reuse_vpc


# CREATE VPC STACK
#######################
resource = [ 'vpc' ]
for res in resource:
    if res in stacks_list:
        vpc = VPC( res, args, config )
        outputParams = vpc.deploy()

# CREATE VPC STACK
#######################
resource = [ 'eks' ]
for res in resource:
    if res in stacks_list:
        eks = EKS( res, args, config )
        outputParams = eks.deploy()