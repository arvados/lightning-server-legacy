#!/usr/bin/python
#

import arvados
import re
import os

this_job = arvados.current_job()
this_task = arvados.current_task()

this_job_input = this_job['script_parameters']['DataUUID']

inputPath = os.path.join( os.environ['TASK_KEEPMOUNT'], this_job_input )

out = arvados.CollectionWriter()

out.set_current_stream_name( "results" )
out.set_current_file_name( "output.txt" )

out.write( "input path : " + str(inputPath) + "\n" )


readme_fp = open( inputPath + "/README" )
out.write( readme_fp.read() )
readme_fp.close()

out.write( "\n\n" )

sampleA_fp = open( inputPath + "/sampleA/seqA.fa" )
out.write( sampleA_fp.read() )
sampleA_fp.close()

out.write( "\n\n" )

sampleB_fp = open( inputPath + "/sampleB/seqB.fa" )
out.write( sampleB_fp.read() )
sampleB_fp.close()

out.write( "\n\n" )

this_task.set_output(out.finish())


