#!/bin/bash
#
# Register the pipeline template with arvados and immediately
# run from the command line.
#
# This script assumes the script has been checked into the repository.
#
# This also requires the 'json' tool to parse json.  See: https://github.com/trentm/json
#


pipeline_template="canary.pipeline"

# An example dataset to process.  The data set is small and is
# in this subtree of the repository, so we could just reference it directly
# in our script, but the idea is to show how you would use data in your
# crunch script from the keep store.
#
DATAUUID=`arv keep put --no-progress .-canary-data`

# Register the pipeline with Arvados
#
template=`cat $pipeline_template | json -E "this.components.Canary.repository=\"$USER\"" `
ARVUUID=`arv pipeline_template create --pipeline-template "$template" | json uuid`
echo "pipline template:" $ARVUUID

# And run the pipeline here
#
arv pipeline run --no-reuse --run-here --template $ARVUUID Canary::input=$DATAUUID



