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

    # Load plugin and setup mapping
    nv.command("set runtimepath+=.")
    nv.command("runtime plugin/visual-multi.vim")
    nv.command(
        "vnoremap <silent><nowait><expr> <M-j> "
        '":\\<C-u>call vm#commands#visual_cursors_with_pos(" . '
        'line(".") . ", " . col(".") . ")\\<CR>"'
    )

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


def main():
    """Main test execution."""
    nv, nv_process, sock_path = setup_nvim()

    try:
        test_cases = [
            ("Single-column block to VM", test_single_column_block),
            ("Multi-column block to VM", test_multi_column_block),
            ("Insert at start (I)", test_insert_at_start),
            ("Append at end (A)", test_append_at_end),
        ]

        all_results = []
        for name, test_func in test_cases:
            passed, test_results = test_func(nv)
            all_results.append((name, passed, test_results))
            if passed:
                print(f"✓ {name} test passed")
            else:
                print(f"✗ {name} test failed:")
                for result, msg in test_results:
                    if not result:
                        print(f"  - {msg}")

        return 0 if all(passed for _, passed, _ in all_results) else 1

    finally:
        try:
            nv.command("qa!")
        except Exception:  # pylint: disable=broad-except
            pass
        nv_process.terminate()
        nv_process.wait()
        if os.path.exists(sock_path):
            os.remove(sock_path)


if __name__ == "__main__":
    sys.exit(main())
