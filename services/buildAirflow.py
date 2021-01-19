# Define parameters and build aws cfn stack for airflow services

# Import the SDK
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
from lib.route53Wrapper import route53Wrapper
import requests
import time
import exceptions
import logging
from buildRDS import RDS
from lib.secretsManagerWrapper import secretsManagerWrapper
from lib.datadogWrapper import datadogWrapper

class Airflow(object):
    """Airflow Class"""

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    # Default constructor of the class.
    def __init__(self, resource, args, config):
        self.resource = resource
        self.resource_repo = 'airflow'
        self.args = args
        self.config = config
        self.REGION = 'eu-west-1'
        self.cf_conn = boto.cloudformation.connect_to_region(self.REGION,aws_access_key_id=self.args.aws_access_key_id, aws_secret_access_key=self.args.aws_secret_access_key)
        self.datadog = datadogWrapper(self.args, self.resource)


    def main(self):
        # Set connections
        ec2conn = boto.ec2.connect_to_region(self.REGION, aws_access_key_id=self.args.aws_access_key_id, aws_secret_access_key=self.args.aws_secret_access_key)

        self.resource_name = self.args.resource_name.lower() + '-' + self.args.labelstack

        manage_cfn = cfnWrapper(self.cf_conn)

        # Build RDSTarget connection string
        secretname='/{}db/admin/'.format(self.resource)
        print(secretname)
        manage_secret = secretsManagerWrapper(secretname,self.REGION)
        credentials = manage_secret.get_secret(secretname)

        AirflowDBTarget = "postgresql+psycopg2:\\/\\/{user}:{password}@{host}:{port}\\/{db}"\
            .format(user=credentials.get('username'),
                    password=credentials.get('password'),
                    #host=credentials.get('host'),
                    host=self.args.database_to_point + '.' + self.config.get('ROUTE53','route53.domain'),
                    port=self.config.get('AIRFLOWDB', 'rds.rdsport'),
                    db=self.config.get('AIRFLOWDB', 'rds.dbname')
                    )

        secretname_ses='/{}/cfg_properties/'.format(self.resource)
        print(secretname_ses)
        manage_secret_ses = secretsManagerWrapper(secretname_ses,self.REGION)
        credentials_ses = manage_secret.get_secret(secretname_ses)

        ses_user = credentials_ses.get('ses_user')
        ses_password = credentials_ses.get('ses_password')
        fernet_key = credentials_ses.get('fernet_key')

        params = {
          'EnvironmentName': self.args.labelstack,
          'Environment': self.args.environment,
          'Vpc': self.config.get('VPC','vpc.id'),
          'PublicSubnet1AZ': self.config.get('VPC','vpc.publicsubnet1az'),
          'PublicSubnet2AZ': self.config.get('VPC','vpc.publicsubnet2az'),
          'PrivateSubnet3AZ': self.config.get('VPC','vpc.privatesubnet3az'),
          'SubnetId': self.config.get('VPC','vpc.subnet1az'),
          'InstanceType': self.config.get(self.resource.upper(),'ec2.instancetype'),
          'KeyPairName': self.config.get('COMMON','aws.keypairname'),
          'Resource': self.resource,  # it's a resource to deploy
          'SecurityGroup': self.config.get('SECURITYGROUP','ec2.sgscmoficinas'),
          'Hostedzone': self.config.get('ROUTE53','route53.hostedzone'),
          'R53Domain' : self.config.get('ROUTE53','route53.domain'),
          'ResourceName': self.resource_name, #it's a Jira #
          'AirflowDBTarget': AirflowDBTarget,
          'PDITarget': self.config.get('AIRFLOW','ec2.pditarget')+ '.' + self.config.get('ROUTE53','route53.domain') ,
          'DeployBucket': self.config.get('COMMON','s3.deploy.bucket'),
          'ReposBucket': self.config.get('COMMON','s3.repos.bucket'),
          'LogsBucket': self.config.get('COMMON','s3.logs.bucket'),
          'SESUser': ses_user,
          'SESPass': ses_password,
          'FernetKey': fernet_key,
          'UnicronClusterName': self.config.get('COMMON', 'unicron.cluster.name'),
          'UnicronRoleARN': self.config.get('COMMON', 'unicron.role.arn'),
          'CodeDeployApplicationName': self.config.get('AIRFLOW', 'codedeploy.applicationname'),
          "RealResourceName": self.args.resource_name.lower()
        }

        tags = dict(self.config.items('TAG-'+self.resource.upper()))
        tags.update( dict(self.config.items('TAG-DATADOG')) )

        #Deploy new airflow  stack
        manage_cfn.create_stack(params, self.resource, self.resource, self.args.update_stack, self.resource_name, tags )

        # Wait for stack to be depployed
        airflowstack = manage_cfn.wait_for_stack(self.resource,  self.args.update_stack, self.resource_name)

        # Show stack output params values
        outputParams = lib.utils.printTemplateOutputs(airflowstack)

        #### Sleep 1 minute until returning output so that EC2 is deployed and DNS resolves successfully
        time.sleep(30)

        # Create Monitoring Resources.
        if tags.get('datadog') == 'monitored':
            self.datadog.deploy_resources(self.get_service(), self.get_timeboard_name(), self.resource_name)

        webServer = 'http://'+outputParams['InternalDns']+':8080'

        logging.info('Airflow server endpoint: ' + webServer)


    def delete(self, stackname):

        manage_cfn = cfnWrapper(self.cf_conn)

        resource_name = manage_cfn.get_parameter_value(stackname, 'ResourceName')

        #borramos DNs hechas a mano
        manage_route53 = route53Wrapper(self.args.aws_access_key_id, self.args.aws_secret_access_key, self.config.get('ROUTE53','route53.domain'))
        manage_route53.deleteDNS('A', self.resource+'-internal-' + resource_name.lower(), '192.168.1.1' )
        manage_route53.deleteDNS('CNAME', self.resource+'-external-' + resource_name.lower(), 'dummy.compute.amazonaws.com' )

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

