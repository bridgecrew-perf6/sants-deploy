import ConfigParser
import sys
import os
import argparse
import ConfigParser
import logging


sys.path.append('..')
from buildEMR import buildEMR
from buildRedshift import Redshift
from buildCategorizator import buildCategorizator
from buildCortex import Cortex
from buildSQS import Sqs
from buildQSense import QSense
from buildRDS import RDS
from buildAirflow import Airflow



parser = argparse.ArgumentParser(description='Process Arguments.')
parser.add_argument("-ev", "--environment", default='', type=str, required = True,
                    help="Environment.")
parser.add_argument("-bl", "--blacklist", default=[], type=str, nargs='+', required = False,
                    help="resource to delete.")
parser.add_argument("-wl", "--white_list", default=[], type=str, nargs='+', required = False,
                    help="intochauble resources.")
parser.add_argument("-dr", "--delete_resources", default=[], type=str, nargs='+', required = True,
                    help="resources to delete.")
parser.add_argument("-dn", "--dry_run", default='', type=str, required = True,
                     help="dry run")
parser.add_argument("-rn", "--resource_name", default='', type=str, required = True,
                     help="dry run")

args = parser.parse_args()

# CONFIG SECTION
# Set properties
REGION = 'eu-west-1'
properties_file = 'config/config.properties_'+args.environment

config = ConfigParser.RawConfigParser()
config.read(properties_file)



class DeleteResource:
    """ delete Resource class"""

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    def __init__(self,args):
        self.args = args
        self.factory = Factory(args)
        
    def delete_resource(self, resources, whitelist, dry_run):
        for resource in resources:
            logging.info("Resource being parsed: "+resource)
            items = self.get_items_resource(resource)
            for item in items:               
                response = self.factory.getResource(resource)
                inside = False
                for x in whitelist:
                    itemlower = item.lower()
                    if itemlower.find(x.lower()) > -1:
                        inside = True
                        break
                if not inside:
                     print "Resource to delete: "+item
                     if dry_run != 'True':
                        response.delete(item)
                        print "Item to delete: "+item
                     else:
                        print "Test: Item to delete: "+item
                        pass

    def get_items_resource(self, resource):
        response = self.factory.getResource(resource)
        print "Response in get_items_resource: "
        print response
        items_list = response.get_list()
        return items_list

    def delete_resource_only(self, resources, blacklist, whitelist, dry_run):
        logging.info("##### Blacklist:")
        for i in range(0, len(blacklist)): logging.info(blacklist[i])

        ## Clean blacklist of whitelist elements.
        ## blacklist elements must be id jiras
        logging.info("##### Items WhiteList: ")
        for i in range(0, len(whitelist)): logging.info(whitelist[i])

        ##### Extract from blacklist that elements included in whitelist
        cleanBlackList = []
        for x in blacklist:
            isWhite = False
            itemBlack = x.lower()
            for itemWhite in whitelist:
                itemWhite = itemWhite.lower()
                if itemWhite.find(itemBlack) > -1 or itemBlack.find(itemWhite) > -1:
                    isWhite = True
                    break
                else:
                    pass

            if not(isWhite):
                cleanBlackList.append(x)

        logging.info("##### List black without white: ")
        for i in range(0, len(cleanBlackList)): logging.info(cleanBlackList[i])
        
        ##### Delete stacks included in blacklist for resources provided.
        logging.info("##### Deleting resources ... ")
        for resource in resources:
            logging.info("### Resource being deleted: "+resource)
            items = self.get_items_resource(resource)
            #items = map(lambda x:x.lower(),items)
            for item in items:               
                response = self.factory.getResource(resource)
                inside = False
                for x in cleanBlackList:
                    response = self.factory.getResource(resource)
                    itemlower = item.lower()
                    if itemlower.find(x.lower()) > -1:
                        inside = True
                        logging.info("Deleting resource: "+item)
                        if dry_run != 'True':
                            response.delete(item)
                            break
                        else:
                            logging.info("Test")
                            pass

class Factory:

    def __init__(self,args):
        self.args = args

    def getResource(self, resource):  
        if resource in  ['VPC']:
            return VPC(resource=resource, args=self.args, config=config)


if __name__ == '__main__':

    whitelist = config.get('AWSCLEAN','whitelist.stacks').split(',') + args.white_list

    logging.info("Resources in the whitelist:")
    if (args.blacklist == []):
        deleteResource = DeleteResource(args)
        deleteResource.delete_resource(args.delete_resources, whitelist, args.dry_run)
    else:
        deleteResource = DeleteResource(args)
        deleteResource.delete_resource_only(args.delete_resources, args.blacklist, whitelist, args.dry_run)
		
