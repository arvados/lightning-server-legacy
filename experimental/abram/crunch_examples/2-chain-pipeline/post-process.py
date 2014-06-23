#!/usr/bin/python
#

import arvados
import re

arvados.job_setup.one_task_per_input_file(if_sequence=0, and_end_task=True)

this_job = arvados.current_job()
this_task = arvados.current_task()
this_task_input = this_task['parameters']['input']

input_file = list( arvados.CollectionReader(this_task_input).all_files() )[0]

out = arvados.CollectionWriter()
out.set_current_file_name(input_file.decompressed_name())
out.set_current_stream_name(input_file.stream_name())
for line in input_file.readlines():
  out.write( "!!!" + line.upper() )

this_task.set_output(out.finish())



