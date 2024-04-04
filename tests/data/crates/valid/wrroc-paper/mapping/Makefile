.PHONY: clean

all: prov-mapping.rdf prov-mapping.json prov-mapping.ttl

clean:
	rm -f prov-mapping-w-metadata.tsv prov-mapping.rdf prov-mapping.ttl prov-mapping.json

prov-mapping-w-metadata.tsv: prov-mapping.yml prov-mapping.tsv
	sssom parse -m prov-mapping.yml prov-mapping.tsv >  prov-mapping-w-metadata.tsv

prov-mapping.rdf: prov-mapping-w-metadata.tsv
	sssom convert prov-mapping-w-metadata.tsv --output-format rdf --output prov-mapping.rdf

prov-mapping.ttl: prov-mapping-w-metadata.tsv
	sssom convert prov-mapping-w-metadata.tsv --output-format owl --output prov-mapping.ttl

prov-mapping.json: prov-mapping-w-metadata.tsv
	sssom convert prov-mapping-w-metadata.tsv --output-format json --output prov-mapping.json
