.PHONY: clean-photos

clean-photos:
	find photos -mindepth 1 -maxdepth 1 -type d ! -name 123456789 -exec rm -rf {} +
