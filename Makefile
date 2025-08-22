.PHONY: build serve json markdown

build: json markdown
	mkdocs build

serve: json markdown
	mkdocs serve

json: docs/index.json

markdown: docs/index.md

%.md: config.yaml
	./process markdown --filename $< > $@

%.json: config.yaml
	./process json --filename $< > $@
