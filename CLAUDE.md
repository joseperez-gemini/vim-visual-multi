# Claude Development Guidelines

## Testing

Run the test suite:
```bash
nix develop --command python test/test_block_vm.py
```

## Code Quality

Run all linters and formatters before committing:
```bash
# 1. Format code
nix develop --command black test/test_block_vm.py

# 2. Type checking (should show 0 errors)
nix develop --command pyright test/test_block_vm.py

# 3. Linting (should be 10.0/10)
nix develop --command pylint test/test_block_vm.py
```

## Test Coverage

The test suite (`test/test_block_vm.py`) covers:
1. Single-column block visual to VM extend mode transition
2. Multi-column block visual to VM extend mode transition
3. Insert at start with `I` in block VM mode
4. Append at end with `A` in block VM mode

## Important Notes

- The `<M-j>` mapping must use `<expr>` so that `line('.')` and `col('.')` are evaluated while still in visual mode
- Always call `vm#reset()` between tests to clean up VM state
- Use `feedkeys()` for sending key sequences to VM mode
- Wait for VM mode to activate using `wait_for_vm_active()` helper