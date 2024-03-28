import json
import os
from uuid import uuid4
from datetime import datetime
from parkit_pkg.src.utils import *


def createemptycollection(collectionpath, projectdesc="", projecttitle=""):
    # Get the current date
    current_date = datetime.now()

    # Format the date as YYYYmmdd
    formatted_date = current_date.strftime("%Y%m%d")

    emptyproject = {
        "metadataEntries": [
            {"attribute": "collection_type", "value": "Project"},
            {
                "attribute": "project_start_date",
                "value": "DATE",
                "dateFormat": "yyyyMMdd",
            },
            {"attribute": "access", "value": "Open Access"},
            {"attribute": "method", "value": "NGS"},
            {"attribute": "origin", "value": "CCBR"},
            {"attribute": "project_affiliation", "value": "CCBR"},
            {"attribute": "project_description", "value": "PROJECTDESCRIPTION"},
            {"attribute": "project_status", "value": "Completed"},
            {"attribute": "retention_years", "value": "7"},
            {"attribute": "project_title", "value": "PROJECTTITLE"},
            {"attribute": "summary_of_samples", "value": "Unknown"},
            {"attribute": "organism", "value": "Unknown"},
        ]
    }

    emptyproject_str = json.dumps(emptyproject)
    emptyproject_str = emptyproject_str.replace("DATE", formatted_date)
    emptyproject_str = emptyproject_str.replace("PROJECTDESCRIPTION", projectdesc)
    emptyproject_str = emptyproject_str.replace("PROJECTTITLE", projecttitle)
    new_emptyproject = json.loads(emptyproject_str)
    json_path = os.path.join("/dev/shm", str(uuid4()) + ".json")
    with open(json_path, "w") as outf:
        json.dump(new_emptyproject, outf, indent=4)

    cmd = f"dm_register_collection {json_path} {collectionpath}"
    run_dm_cmd(
        dm_cmd=cmd, errormsg=f"dm_register_collection failed for {collectionpath}"
    )

    cmd = f"cat {json_path} && rm -f {json_path}"
    run_cmd(cmd=cmd)

    emptyanalysis = {
        "metadataEntries": [
            {"attribute": "collection_type", "value": "Analysis"},
            {
                "attribute": "project_start_date",
                "value": "DATE",
                "dateFormat": "yyyyMMdd",
            },
            {"attribute": "method", "value": "NGS"},
            {"attribute": "number_of_cases", "value": "unknown"},
        ]
    }

    emptyanalysis_str = json.dumps(emptyanalysis)
    emptyanalysis_str = emptyanalysis_str.replace("DATE", formatted_date)
    new_emptyanalysis = json.loads(emptyanalysis_str)
    json_path = os.path.join("/dev/shm", str(uuid4()) + ".json")
    with open(json_path, "w") as outf:
        json.dump(new_emptyanalysis, outf, indent=4)

    analysis_collectionpath = collectionpath + "/Analysis"

    cmd = f"dm_register_collection {json_path} {analysis_collectionpath}"
    run_dm_cmd(
        dm_cmd=cmd,
        errormsg=f"dm_register_collection failed for {analysis_collectionpath}",
    )

    cmd = f"cat {json_path} && rm -f {json_path}"
    run_cmd(cmd=cmd)
