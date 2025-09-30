.PHONY: format typecheck lint test all

format:
	nix develop --command black test/test_block_vm.py

typecheck:
	nix develop --command pyright test/test_block_vm.py

lint:
	nix develop --command pylint test/test_block_vm.py

test:
	nix develop --command python test/test_block_vm.py

all: format typecheck lint test