#!/usr/bin/python
#

import arvados as arv
import re
import os

job_uuid  = os.environ['JOB_UUID']
task_uuid = os.environ['TASK_UUID']
work_dir  = os.environ['JOB_WORK']


task_qsequence = os.environ['TASK_QSEQUENCE']
task_sequence  = os.environ['TASK_SEQUENCE']

this_job  = arv.current_job()

seq = int(task_sequence)

# This is the parent task, so create a bunch of jobs
# that will process on the input we specify.
#
if seq == 0 :

  taskName = 0
  mount_uuid = this_job['script_parameters']['MountUUID']
  for a in range(1,6):
    for b in range(100,107):
      new_task_attributes = {
          'job_uuid' : job_uuid,
          'created_by_job_task_uuid' : task_uuid,
          'sequence' : 1,
          'parameters' : { 'MountUUID' : mount_uuid, 'filenameA' : "A/A" + str(a) + ".txt" , 'filenameB' : "B/B" + str(b) + ".txt", 'taskName' : str(taskName) }
          }
      taskName += 1

      # Queue up the task
      #
      arv.api('v1').job_tasks().create( body = new_task_attributes ).execute()

  # Exit this parent task with a 'success' message
  #
  arv.api('v1').job_tasks().update( uuid = task_uuid, body={'success':True }).execute()
  exit(0)


# From here down is the child task created by the parent task
#

this_task = arv.current_task()

mount_dir = os.path.join( os.environ['TASK_KEEPMOUNT'], this_task['parameters']['MountUUID'] )

filenameA = this_task["parameters"]["filenameA"]
filenameB = this_task["parameters"]["filenameB"]
taskName = this_task["parameters"]["taskName"]


out = arv.CollectionWriter()
out.set_current_stream_name( "output/ofjob" )
out.set_current_file_name( "output" + str(taskName) + ".txt" )

fa = open( os.path.join( mount_dir, filenameA ) )
outputA = fa.read()
fa.close()

fb = open( os.path.join( mount_dir, filenameB ) )
outputB = fb.read()
fb.close()


out.write( "seq " + str(seq) + ", taskName " + str(taskName) + "\n" )
out.write( str(outputA) + "\n" )
out.write( str(outputB) + "\n" )

this_task.set_output(out.finish())


