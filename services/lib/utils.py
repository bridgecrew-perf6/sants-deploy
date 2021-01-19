#@author Ismael Arab

##########################################################################
#
#
# 
#
##########################################################################
import logging
import logging.config
import time
import datetime
import ConfigParser
import boto3
import zipfile
import os, fnmatch
import shutil
import json

def getProperties(fileProperties, section):
  # Load bootstrap actions
    config = ConfigParser.ConfigParser()
    config.read(fileProperties)
    properties = {}

    sections = config.sections()
    for section in sections:
        print "Section: "+section

        if section == self.environment:
            properties = configSectionMap(config, section)
            return properties

    raise ValueError("Section doesn't exist.")

def configSectionMap(config, section):
    dict1 = {}
    options = config.options(section)
    for option in options:
        try:
            dict1[option] = config.get(section, option)
            if dict1[option] == -1:
                DebugPrint("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None

    return dict1

def printTemplateOutputs(stackOutput):
  outputParams = {}
  for output in stackOutput.outputs:
    print output.key+': '+output.value
    outputParams[output.key] = output.value

  return outputParams

def unzip_build(aws_access_key_id, aws_secret_access_key, aws_region, bucket_name, folder, zipppedfile, target_dir):
    #Descargamos zip de S3
    session = boto3.session.Session(aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
    s3 = session.resource("s3")

    bucket = s3.Bucket(bucket_name)
    obj = bucket.Object(folder+'/'+zipppedfile+'.zip').download_file(zipppedfile+'.zip')

    #Descomprimimos
    with zipfile.ZipFile(zipppedfile+".zip","r") as zip_ref:
        #Delete folder before to extract files.
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        zip_ref.extractall(target_dir)

def parseJSON(template, dictionary):

        with open(template+'_parsed', 'w') as dest_file:
            with open(template, 'r+') as file:
                content = file.read()

                for key, value in dictionary.iteritems():
                    content = content.replace(key, value)
                
                dest_file.write(content)
                dest_file.closed
                file.closed

        

        content = None

        with open(template+'_parsed') as data_file:
            content = json.load(data_file)

        return content

def findReplace(directory, find, replace, filePattern):
    for path, dirs, files in os.walk(os.path.abspath(directory)):
        for filename in fnmatch.filter(files, filePattern):
            filepath = os.path.join(path, filename)
            with open(filepath) as f:
                s = f.read()
            s = s.replace(find, replace)
            with open(filepath, "w") as f:
                f.write(s)
