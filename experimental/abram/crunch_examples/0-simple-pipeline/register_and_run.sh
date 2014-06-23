#!/bin/bash
#
# Register the pipeline template with arvados and immediately
# run from the command line.
#
# This script assumes the script has been checked into the repository.
#
# This also requires the 'json' tool to parse json.  See: https://github.com/trentm/json
#

pt="systemInfo.pipeline"

template=` cat $pt | json -E "this.components.housekeeper.repository=\"$USER\"" `
ARVUUID=`arv pipeline_template create --pipeline-template "$template" | json uuid`
echo "pipline template:" $ARVUUID

arv pipeline run --run-here --template $ARVUUID



