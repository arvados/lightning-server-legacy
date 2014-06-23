#!/bin/bash
#
# Register the pipeline template with arvados and immediately
# run from the command line.
#
# This script assumes the script has been checked into the repository.
#
# This also requires the 'json' tool to parse json.  See: https://github.com/trentm/json
#


pipeline_template="multiInput.pipeline"

# An example dataset to process.  The data set is small and is
# in this subtree of the repository, so we could just reference it directly
# in our script, but the idea is to show how you would use data in your
# crunch script from the keep store.
#
DATAUUID0=`arv keep put --no-progress 3-multiple-input-data/input0.txt`
DATAUUID1=`arv keep put --no-progress 3-multiple-input-data/input1.txt`
echo "input0.txt uuid $DATAUUID0"
echo "input1.txt uuid $DATAUUID1"

# Register the pipeline with Arvados
#

template=`cat $pipeline_template | json -E "this.components.heartlessness.repository=\"$USER\"" `
ARVUUID=`arv pipeline_template create --pipeline-template "$template"  | json uuid`
echo "pipline template:" $ARVUUID

# And run the pipeline here.
#
echo "running: 'arv pipeline run --run-here --no-reuse --template $ARVUUID heartlessness::inputA=$DATAUUID0 heartlessness::inputB=$DATAUUID1'"
arv pipeline run --run-here --no-reuse --template $ARVUUID heartlessness::inputA=$DATAUUID0 heartlessness::inputB=$DATAUUID1



