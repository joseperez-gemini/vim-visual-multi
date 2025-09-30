#!/usr/bin/env python3

import subprocess
import sys
import time
import os

import pynvim


def wait_for_socket(path, timeout=5):
    for _ in range(timeout * 10):
        if os.path.exists(path):
            return
        time.sleep(0.1)
    raise TimeoutError(f"Socket {path} was not created in time")


def wait_for_vm_active(nv, timeout=5):
    for _ in range(timeout * 10):
        if nv.eval("get(b:, 'visual_multi', 0)"):
            return
        time.sleep(0.1)
    raise TimeoutError("VM mode did not activate in time")


def wait_for_buffer_change(nv, expected, timeout=5):
    for _ in range(timeout * 10):
        if nv.current.buffer[:] == expected:
            return
        time.sleep(0.1)
    raise TimeoutError(
        f"Buffer did not change to expected value. Got: {nv.current.buffer[:]}"
    )


def setup_nvim():
    """Start and configure nvim instance."""
    sock_path = "/tmp/nvim_test.sock"
    if os.path.exists(sock_path):
        os.remove(sock_path)

    # pylint: disable=consider-using-with
    proc = subprocess.Popen(
        ["nvim", "--listen", sock_path, "--headless"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    wait_for_socket(sock_path)
    nv = pynvim.attach("socket", path=sock_path)

    # Load plugin and setup mappings
    nv.command("set runtimepath+=.")
    nv.command("runtime plugin/visual-multi.vim")
    nv.command("let g:VM_live_editing = 1")  # Enable live editing (default)
    # Force load autoload files to pick up changes
    nv.command("runtime autoload/vm/insert.vim")
    nv.command(
        "vnoremap <silent><nowait><expr> <M-j> "
        '":\\<C-u>call vm#commands#visual_cursors_with_pos(" . '
        'line(".") . ", " . col(".") . ")\\<CR>"'
    )
    nv.command("nmap <M-j> <Plug>(VM-Add-Cursor-Down)")

    return nv, proc, sock_path


def test_single_column_block(nv):
    """Test single-column block visual to VM extend mode."""
    nv.current.buffer[:] = [
        "line1",
        "line2",
        "line3",
        "line4",
    ]
    nv.command("normal! gg0l")
    nv.input("<C-v>2j<M-j>")
    wait_for_vm_active(nv)

    vm_extend_mode = nv.eval("exists('g:Vm') && get(g:Vm, 'extend_mode', 0)")
    regions = nv.eval("b:VM_Selection.Regions")

    test_results = [
        (len(regions) == 3, f"Expected 3 regions, got {len(regions)}"),
        (vm_extend_mode, "Not in extend mode"),
        (
            all(
                r["l"] == i + 1 and r["a"] == 2 and r["b"] == 2
                for i, r in enumerate(regions)
            ),
            "Region positions incorrect",
        ),
    ]

    nv.command("call vm#reset()")
    time.sleep(0.1)
    return all(result for result, _ in test_results), test_results


def test_multi_column_block(nv):
    """Test multi-column block visual to VM extend mode."""
    nv.current.buffer[:] = [
        "line1",
        "line2",
        "line3",
        "line4",
    ]
    nv.command("normal! gg0l")
    nv.input("<C-v>2j2l<M-j>")
    wait_for_vm_active(nv)

    vm_extend_mode = nv.eval("exists('g:Vm') && get(g:Vm, 'extend_mode', 0)")
    regions = nv.eval("b:VM_Selection.Regions")

    test_results = [
        (len(regions) == 3, f"Expected 3 regions, got {len(regions)}"),
        (vm_extend_mode, "Not in extend mode"),
        (
            all(
                r["l"] == i + 1 and r["a"] == 2 and r["b"] == 4
                for i, r in enumerate(regions)
            ),
            "Region positions incorrect",
        ),
    ]

    nv.command("call vm#reset()")
    time.sleep(0.1)
    return all(result for result, _ in test_results), test_results


def test_insert_at_start(nv):
    """Test I (insert at beginning) in block VM mode."""
    nv.current.buffer[:] = [
        "line1",
        "line2",
        "line3",
        "line4",
    ]
    nv.command("normal! gg0l")
    nv.input("<C-v>2j2l<M-j>")
    wait_for_vm_active(nv)

    # Flip cursor to start
    nv.command('call feedkeys("o")')
    time.sleep(0.1)

    # Insert character
    nv.command('call feedkeys("IX\\<Esc>")')
    time.sleep(0.3)

    buf_result = nv.current.buffer[:]
    expected = [
        "lXine1",
        "lXine2",
        "lXine3",
        "line4",
    ]

    nv.command("call vm#reset()")
    time.sleep(0.1)
    return buf_result == expected, [
        (buf_result == expected, f"Expected {expected}, got {buf_result}")
    ]


def test_append_at_end(nv):
    """Test A (append at end) in block VM mode."""
    nv.current.buffer[:] = [
        "line1",
        "line2",
        "line3",
        "line4",
    ]
    nv.command("normal! gg0l")
    nv.input("<C-v>2j2l<M-j>")
    wait_for_vm_active(nv)

    # Insert character
    nv.command('call feedkeys("AX\\<Esc>")')
    time.sleep(0.3)

    buf_result = nv.current.buffer[:]
    expected = [
        "lineX1",
        "lineX2",
        "lineX3",
        "line4",
    ]

    nv.command("call vm#reset()")
    time.sleep(0.1)
    return buf_result == expected, [
        (buf_result == expected, f"Expected {expected}, got {buf_result}")
    ]


def test_undo_single_operation(nv):
    """Test that inserting text creates a single undo block."""
    # Force reload the modified autoload file
    nv.command("source autoload/vm/insert.vim")

    nv.current.buffer[:] = [
        "hello",
        "hello",
        "hello",
    ]
    # Create multiple cursors using <M-j> (Add-Cursor-Down)
    nv.command("normal! gg$")
    nv.input("<M-j><M-j>")
    wait_for_vm_active(nv)

    # Insert " word" at end of lines - type character by character
    nv.input("a")  # Enter insert mode
    time.sleep(0.05)
    nv.input(" ")  # Type space
    time.sleep(0.05)
    nv.input("w")  # Type w
    time.sleep(0.05)
    nv.input("o")  # Type o
    time.sleep(0.05)
    nv.input("r")  # Type r
    time.sleep(0.05)
    nv.input("d")  # Type d
    time.sleep(0.05)
    nv.input("<Esc>")  # Exit insert mode
    time.sleep(0.1)

    buf_after_insert = nv.current.buffer[:]
    expected_after = [
        "hello word",
        "hello word",
        "hello word",
    ]

    # Now undo - should undo entire " word" insertion in one step
    nv.command("normal! u")
    time.sleep(0.1)

    buf_after_first_undo = nv.current.buffer[:]
    expected_after_undo = [
        "hello",
        "hello",
        "hello",
    ]

    # If first undo didn't restore, try a second undo (bug exists)
    if buf_after_first_undo != expected_after_undo:
        nv.command("normal! u")
        time.sleep(0.1)
        buf_after_second_undo = nv.current.buffer[:]
    else:
        buf_after_second_undo = None

    test_results = [
        (
            buf_after_insert == expected_after,
            f"After insert: expected {expected_after}, got {buf_after_insert}",
        ),
        (
            buf_after_first_undo == expected_after_undo,
            f"After first undo: expected {expected_after_undo}, got {buf_after_first_undo}"
            + (
                f" - needed 2nd undo which gave: {buf_after_second_undo}"
                if buf_after_second_undo is not None
                else ""
            ),
        ),
    ]

    nv.command("call vm#reset()")
    time.sleep(0.1)
    return all(result for result, _ in test_results), test_results


def cleanup_nvim(nv, nv_process, sock_path):
    """Clean up nvim instance."""
    try:
        nv.command("qa!")
    except Exception:  # pylint: disable=broad-except
        pass
    nv_process.terminate()
    nv_process.wait()
    if os.path.exists(sock_path):
        os.remove(sock_path)


def run_test_and_report(name, test_func, nv):
    """Run a single test and print results."""
    passed, test_results = test_func(nv)
    if passed:
        print(f"✓ {name} test passed")
    else:
        print(f"✗ {name} test failed:")
        for result, msg in test_results:
            if not result:
                print(f"  - {msg}")
    return passed, test_results


def main():
    """Main test execution."""
    nv, nv_process, sock_path = setup_nvim()

    try:
        test_cases = [
            ("Single-column block to VM", test_single_column_block),
            ("Multi-column block to VM", test_multi_column_block),
            ("Insert at start (I)", test_insert_at_start),
            ("Append at end (A)", test_append_at_end),
            ("Undo single operation", test_undo_single_operation),
        ]

        all_results = []
        for name, test_func in test_cases:
            passed, test_results = run_test_and_report(name, test_func, nv)
            all_results.append((name, passed, test_results))

        return 0 if all(passed for _, passed, _ in all_results) else 1

    finally:
        cleanup_nvim(nv, nv_process, sock_path)


if __name__ == "__main__":
    sys.exit(main())
