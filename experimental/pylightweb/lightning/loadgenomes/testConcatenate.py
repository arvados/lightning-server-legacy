#testConcatenate

import sys
import subprocess

input_file = 'chr1_band0_s0_e2300000.fj.gz'


p = subprocess.Popen(['gunzip', '-c', input_file], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
print p
stdout, stderr = p.communicate(None)
print p.returncode

for thing in stdout:
    print thing
