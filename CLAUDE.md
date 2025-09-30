# Claude Development Guidelines

## Quick Commands

```bash
make format      # Format code with black
make typecheck   # Type check with pyright (should show 0 errors)
make lint        # Lint with pylint (should be 10.0/10)
make test        # Run test suite
make all         # Run all checks
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