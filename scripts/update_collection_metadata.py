import argparse
import pandas as pd
import sys
import os
import json
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.utils import *


def in_att_list(att_list, att):
    for att_dict in att_list:
        if att_dict["attribute"] == att:
            return True
    return False


def main():
    # Create the main parser
    parser = argparse.ArgumentParser(
        description="update metadata of a collection already on HPCDME using a CSV from AMP"
    )
    parser.add_argument(
        "--csv", required=True, type=str, help="CSV user-projects.csv from AMP"
    )

    # Parse the arguments
    args = parser.parse_args()

    df = pd.read_csv(args.csv)

    for index, row in df.iterrows():
        metadata = dict()
        metadata["project_id"] = row["Project Identifier"]
        collection_path = "/CCBR_Archive/GRIDFTP/Project_" + metadata["project_id"]
        metadata["project_title"] = row["Title"]
        metadata["pi_name"] = row["PI"]
        metadata["requester_name"] = row["Requester"]
        metadata["lead_analyst_name"] = row["Lead Analyst"]
        metadata["analyst_name"] = row["Analyst"]
        metadata["project_data_type"] = row["Expertise"]

        dm_cmd = "dm_get_collection " + collection_path
        results = run_dm_cmd(
            dm_cmd=dm_cmd,
            errormsg="dm_get_collection Failed!",
            returnproc=True,
            exitiffails=False,
        )
        if results.returncode == 0:
            current_metadata = json.loads(results.stdout)

            # current_metadata['collections'][0]['metadataEntries']['selfMetadataEntries'] is a list of attributes
            att_list = current_metadata["collections"][0]["metadataEntries"][
                "selfMetadataEntries"
            ]
            new_metadata = dict()
            new_metadata["metadataEntries"] = list()
            there_is_something_new = 0
            for att in metadata.keys():
                if not in_att_list(att_list=att_list, att=att):
                    if att == "project_data_type" or "analyst":
                        vals = metadata[att].split(";")
                        for val in vals:
                            new_metadata["metadataEntries"].append(
                                {"attribute": att, "value": val}
                            )
                    else:
                        new_metadata["metadataEntries"].append(
                            {"attribute": att, "value": metadata[att]}
                        )
                    there_is_something_new += 1
            if there_is_something_new != 0:
                json_path = os.path.join("/dev/shm", str(uuid4()) + ".json")
                with open(json_path, "w") as outf:
                    json.dump(new_metadata, outf, indent=4)
                dm_cmd = f"dm_register_collection {json_path} {collection_path}"
                run_dm_cmd(
                    dm_cmd=dm_cmd,
                    errormsg="dm_register_collection Failed!",
                    returnproc=False,
                    exitiffails=False,
                )


if __name__ == "__main__":
    main()
