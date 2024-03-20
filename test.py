import json
import pprint
pp = pprint.PrettyPrinter(indent=4)

with open('compound_query.json') as json_file:
	data = json.load(json_file)
pp.pprint(data)
