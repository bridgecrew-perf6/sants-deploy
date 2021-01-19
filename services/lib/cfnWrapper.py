#@author Ismael Arab

##########################################################################
#   Data Info:     
#       ec2 attributes:
#               https://github.com/boto/boto/blob/develop/boto/cloudformation/stack.py
#               https://github.com/boto/boto/blob/develop/boto/cloudformation/connection.py
##########################################################################


import sys
import boto.ec2
import logging
import logging.config
import time
import datetime
import boto.exception

logging.basicConfig( level=logging.INFO,
    format='[%(levelname)s] - %(threadName)-10s : %(message)s')
logger = logging.getLogger('cfnWrapper')
logger.setLevel(logging.INFO)

class DeployException(Exception):
    pass

class CloudformationException(Exception):
    pass

class cfnWrapper(object):
    
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    def __init__(self, cf_conn):

        self.cf_conn = cf_conn


    def create_stack(self, params, template, stack_name, update_stack, stacklabel, tags={} ):
      # create or update stack      
      capabilities = ["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"]
      cfn_template_body = self.get_template_body(template + '.json')

      if update_stack == 'no':
        try:
            logging.info( "Calling create stack: "+ stack_name+'-'+stacklabel )
            self.cf_conn.create_stack( stacklabel, template_body=cfn_template_body, parameters=tuple(params.items()), capabilities=capabilities, tags=tags )
            logging.info( "Create stack "+ stack_name+'-'+stacklabel + " completed")
        except boto.exception.BotoServerError, ex:
            raise CloudformationException('error occured while creating stack %s: %s' % (template, ex.message))

      elif update_stack == 'yes':
        try:
            if stacklabel == '':
                stacklabel =  stack_name;
            else:
                stacklabel =  stack_name+'-'+stacklabel
            self.cf_conn.update_stack(stacklabel, template_body=cfn_template_body, parameters=tuple(params.items()), capabilities=capabilities )
        except boto.exception.BotoServerError, ex:
            if ex.message == 'No updates are to be performed.':
                # this is not really an error, but there aren't any updates.
                return False
            else:
                raise CloudformationException('error occured while updating stack %s: %s' % (stacklabel, ex.message))
        else:
            return True

    def delete_stack(self, stackname ):
      # delete stack stack
      try:
          self.cf_conn.delete_stack(stackname)
          logging.info( 'Stack deleted: ' + stackname )
      except Exception, ex:
          print ex.message

    ###  WAIT FOR STACK
    #######################
    def wait_for_stack(self, stackname, update_stack, stacklabel):

      if update_stack == 'no':
        expected_status = 'CREATE_COMPLETE'
      else:
        expected_status = 'UPDATE_COMPLETE'

      if stacklabel <> '':
        stackname =  stacklabel

      logging.info( "Stack "+ stackname +" deployed. Waiting..." )
      # wait until we get a CREATE_FAILED, ROLLBACK_COMPLETE, or CREATE_COMPLETE on the stack

      #en el caso del update coge el valor anterior de UPDATE_COMPLETE y sale a la primera vuelta de bucle. Por eso ponemos un sleep de 5 segundos
      time.sleep(5)

      stack_is_deploying = True
      while stack_is_deploying:
        logging.info( 'Waiting '+stackname+' infrastructure to be deployed...' )
        events = self.cf_conn.describe_stack_events(stackname)
        if any((e.resource_type == 'AWS::CloudFormation::Stack' and (e.resource_status == 'CREATE_FAILED' or e.resource_status == 'ROLLBACK_COMPLETE'  or e.resource_status == 'ROLLBACK_FAILED' ) for e in events)):
          logging.info( 'Something has FAILED deploying stack infrastructure. ')
          raise DeployException()

# Cambiamos la compararacion de la condicion de salida. El describe_stack_events devuelve todos los eventos que tenga un CloudFormation::Stack, por lo que si el stack ha tenido anteriormente
# un UPDATE_COMPLETE, estariamos saliendo del bucle porque teniamos un "any" en la condicion del IF.
#        if any((e.resource_type == 'AWS::CloudFormation::Stack' and e.resource_status == expected_status for e in events)):
#          stack_is_deploying = False
# Asi pues, lo que pasaremos a hacer ahora es recorrer los eventos (vienen ordenados por mas fresco) y nos quedaremos con la primera ocurrencia de CloudFormation::Stack.
# De esa, miramos su status y si es UPDATE_COMPLETE (o CREATE_COMPLETE), modificamos la condicion de salida del bucle. Si no, salimos del recorrido de eventos de todas formas
# y pasamos a la siguiente iteracion de describe_stack_events
        for e in events:
            if e.resource_type == 'AWS::CloudFormation::Stack':
                if e.resource_status == expected_status:
                    stack_is_deploying = False
                break

        time.sleep(5)

      return self.cf_conn.describe_stacks(stackname)[0]

    ###  GET TEMPLATE BODY
    #######################
    def get_template_body(self, jsonFile):
      tpl_file = open(jsonFile)
      cfn_template_body = tpl_file.read()
      tpl_file.close()

      return cfn_template_body

    def get_list(self, resource):
        stacks = self.cf_conn.describe_stacks()
        print "stacks from cloudformation/lib/cfnWrapper.py are: {}".format(stacks)
        stack_list = []
        for stack in stacks:
            StackName = stack.stack_name
            #cogemos solo los stacks que su primera parte del nombre coincida con el recurso a borrar.
            # Para cortex-ee contamos 2 desde la derecha (DI-18221). Para el resto 3 (cortex-ee-222b9e56150a56b548abfa04b1b4eceae3d81912-35 hay que coger 2)
            if resource == 'cortex-ee':
                if resource in stack.stack_name.rsplit('-',2)[0]:
                    stack_list.append(StackName)
            else:
                if resource == stack.stack_name.rsplit('-',3)[0]:
                    stack_list.append(StackName)
        return stack_list

    def get_physical_resource_id(self, stackname, logical_resource_id):
        cf_resources = self.cf_conn.describe_stack_resource(stack_name_or_id=stackname,logical_resource_id=logical_resource_id)['DescribeStackResourceResponse']['DescribeStackResourceResult']['StackResourceDetail']
        physical_resource_id=cf_resources['PhysicalResourceId']
        return physical_resource_id

    def get_parameter_value(self, stackname, parameter_key):
        cf_parameters = self.cf_conn.describe_stacks(stack_name_or_id=stackname)[0]
        for param in cf_parameters.parameters:
            if param.key == parameter_key:
                parameter_value = param.value

        return parameter_value

