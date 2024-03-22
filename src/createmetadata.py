from pathlib import Path
import json
from uuid import uuid4
from src.utils import *


def createmetadata(infile, collectionpath):
    analysis_collectionpath = collectionpath + "/Analysis"
    p = Path(infile)
    p = p.absolute()

    filename = p.name
    vaultpath = analysis_collectionpath + "/" + filename

    md5file = str(p) + ".md5"
    if check_file_exists(md5file):
        infile = open(md5file)
        x = infile.readlines()[0]
        md5sum = x.strip()
    else:
        md5sum = get_md5sum(file_path=str(p))

    filetype = p.suffix.upper()[1:]

    infilemetadata = {
        "metadataEntries": [
            {"attribute": "phi_content", "value": "Unspecified"},
            {"attribute": "pii_content", "value": "Unspecified"},
            {"attribute": "data_encryption_status", "value": "Unspecified"},
            {"attribute": "analysis_team", "value": "CCBR"},
            {"attribute": "sample_name", "value": "FILENAME"},
            {"attribute": "object_name", "value": "VAULTPATH"},
            {"attribute": "alias", "value": "LOCALPATH"},
            {"attribute": "file_type", "value": "FILETYPE"},
            {"attribute": "data_compression_status", "value": "Not Compressed"},
            {"attribute": "md5_checksum", "value": "MD5SUM"},
        ]
    }

    infilemetadata_str = json.dumps(infilemetadata)
    infilemetadata_str = infilemetadata_str.replace("VAULTPATH", vaultpath)
    infilemetadata_str = infilemetadata_str.replace("FILENAME", filename)
    infilemetadata_str = infilemetadata_str.replace("LOCALPATH", str(p))
    infilemetadata_str = infilemetadata_str.replace("MD5SUM", md5sum)
    infilemetadata_str = infilemetadata_str.replace("FILETYPE", filetype)
    new_infilemetadata = json.loads(infilemetadata_str)
    json_path = str(p) + ".metadata.json"
    with open(json_path, "w") as outf:
        json.dump(new_infilemetadata, outf, indent=4)
    return json_path
