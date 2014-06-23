#!/usr/bin/python
#

import arvados
import re

this_job = arvados.current_job()
this_task = arvados.current_task()

this_job_inputA = this_job['script_parameters']['inputA']
this_job_inputB = this_job['script_parameters']['inputB']

# use fileA and fileB as strings to file ...
#
#fileA = arvados.get_task_param_mount( 'inputA' )
#fileB = arvados.get_task_param_mount( 'inputB' )


input_fileA = list( arvados.CollectionReader( this_job_inputA ).all_files() )[0]
input_fileB = list( arvados.CollectionReader( this_job_inputB ).all_files() )[0]

out = arvados.CollectionWriter()


out.set_current_file_name("output.txt")
out.set_current_stream_name("results")

for line in input_fileA.readlines():
  out.write( "text from 'inputA': " + line.upper() )

for line in input_fileB.readlines():
  out.write( "text from 'inputB: " + line.upper() )

this_task.set_output(out.finish())


