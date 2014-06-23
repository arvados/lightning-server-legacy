#!/usr/bin/python
#
# A script to do some basic qurerying of the system
# it's running on.
#
# The output will be put into a collection.
#

import time
sSec = time.time()

import arvados as arv
import subprocess as sp

def logInfo( of ):
  whoinfo = sp.check_output(["whoami"])
  of.write("user: " + whoinfo)

  pwdinfo = sp.check_output(["pwd"])
  of.write("pwd: " + pwdinfo)

  lsinfo = sp.check_output(["ls", "-lahR"])
  of.write("directory structure:\n" + lsinfo)

  dfinfo = sp.check_output(["df", "-h"])
  of.write("df:\n" + dfinfo)

  meminfo = sp.check_output(["free", "-hm"])
  of.write("mem:\n" + meminfo)

  hostinfo = sp.check_output(["hostname"])
  of.write("host: " + hostinfo)


job = arv.current_job()
task = arv.current_task()

of = arv.CollectionWriter()
of.set_current_file_name("info.log")

whoinfo = sp.check_output(["whoami"])
of.write("user: " + whoinfo + "\n" )

pwdinfo = sp.check_output(["pwd"])
of.write("pwd: " + pwdinfo + "\n" )

lsinfo = sp.check_output(["ls", "-lahR"])
of.write("directory structure:\n" + lsinfo)

dfinfo = sp.check_output(["df", "-h"])
of.write("df:\n" + dfinfo + "\n" )

meminfo = sp.check_output(["free", "-hm"])
of.write("mem:\n" + meminfo + "\n" )

hostinfo = sp.check_output(["hostname"])
of.write("host: " + hostinfo + "\n")


eSec = time.time()
of.write( "took: " + "{0:.2f}s".format(eSec - sSec)  + "\n" )


envVar = sp.check_output(["printenv"])
of.write("environment variables:\n" + envVar + "\n" )


ofId = of.finish()
arv.current_task().set_output( ofId )


