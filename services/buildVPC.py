# Define parameters and build aws cfn stack for airflow services

# Import the SDK
import boto
import boto.cloudformation
import boto.ec2
import os
import shutil
import sys
import re
import time
import uuid
import ConfigParser
from os.path import expanduser
import lib.utils

# Custom python modules
sys.path.append("..")
from lib.cfnWrapper import cfnWrapper
#from lib.route53Wrapper import route53Wrapper
import requests
import time
import exceptions
import logging
# from buildRDS import RDS
# from lib.secretsManagerWrapper import secretsManagerWrapper
# from lib.datadogWrapper import datadogWrapper

class VPC(object):
    """Airflow Class"""

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    # Default constructor of the class.
    def __init__(self, resource, args, config):
        self.resource = resource
        self.args = args
        self.config = config
        self.REGION = 'eu-west-1'
        self.cf_conn = boto.cloudformation.connect_to_region(self.REGION, profile_name="srv-sants-jenkins")
        #connect_to_region(region_name, profile_name="str")
        #self.cf_conn = boto.connect_cloudformation(profile_name='srv-sants-jenkins')
        #self.cf_conn = boto.cloudformation.connection.CloudFormationConnection(profile_name='srv-sants-jenkins')

    def deploy(self):

       
        self.resource_name = self.args.resource_name.lower() + '-' + self.args.labelstack

        manage_cfn = cfnWrapper(self.cf_conn)


        params = {
          'PublicSubnet1AZ': self.config.get('VPC', 'vpc.publicsubnet1az'),
          'PublicSubnet2AZ': self.config.get('VPC', 'vpc.publicsubnet2az'),
          'PrivateSubnet3AZ': self.config.get('VPC', 'vpc.privatesubnet3az'),
          'PublicSubnet4AZ': self.config.get('VPC', 'vpc.publicsubnet4az'),
          'CidrVPC': self.config.get('VPC', 'vpc.cidrvpc'),
          'CidrSubnet1AZ': self.config.get('VPC', 'vpc.cidrsubnet1az'),
          'CidrSubnet2AZ': self.config.get('VPC', 'vpc.cidrsubnet2az'),
          'CidrSubnet3AZ': self.config.get('VPC', 'vpc.cidrsubnet3az'),
          'CidrSubnet4AZ': self.config.get('VPC', 'vpc.cidrsubnet4az')
        }

        manage_cfn.create_stack(params, 'cloudformation/vpc', 'vpc', self.args.update_stack, self.args.labelstack)

        vpcstack = manage_cfn.wait_for_stack('vpc-'+self.args.labelstack,  self.args.update_stack, self.args.labelstack)
        outputParams = lib.utils.printTemplateOutputs(vpcstack)

        tags = dict(self.config.items('TAG-'+self.resource.upper()))
        tags.update( dict(self.config.items('TAG-DATADOG')) )

    def delete(self, stackname):

        manage_cfn = cfnWrapper(self.cf_conn)

        response = manage_cfn.delete_stack(stackname)

    def get_list(self):
        """
          Return cortex stack list
        """
        manage_cfn = cfnWrapper(self.cf_conn)
        cf_list = manage_cfn.get_list(self.resource)
        return cf_list

    def get_service(self):
        # Return SCM DataInsights service
        return self.resource

    def get_timeboard_name(self):

        return self.get_service() +'-'+ self.resource_name

