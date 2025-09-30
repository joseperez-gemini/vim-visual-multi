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


def wait_for_regions(nv, count, timeout=5):
    """Wait for VM to have exactly 'count' regions."""
    for _ in range(timeout * 10):
        regions = nv.eval("get(get(b:, 'VM_Selection', {}), 'Regions', [])")
        if len(regions) == count:
            return regions
        time.sleep(0.1)
    regions = nv.eval("get(get(b:, 'VM_Selection', {}), 'Regions', [])")
    raise TimeoutError(
        f"Expected {count} regions, but got {len(regions)} after {timeout}s: {regions}"
    )


def wait_for_condition(_nv, condition_fn, error_msg, timeout=5):
    """Wait for a custom condition function to return True."""
    for _ in range(timeout * 10):
        if condition_fn():
            return
        time.sleep(0.1)
    raise TimeoutError(f"{error_msg} (timeout after {timeout}s)")


def wait_for_vm_inactive(nv, timeout=5):
    """Wait for VM mode to be deactivated."""
    for _ in range(timeout * 10):
        if not nv.eval("get(b:, 'visual_multi', 0)"):
            return
        time.sleep(0.1)
    raise TimeoutError("VM mode did not deactivate in time")


def wait_for_regions_on_lines(nv, expected_lines, timeout=5):
    """Wait for VM regions to be on specific lines."""
    for _ in range(timeout * 10):
        regions = nv.eval("get(get(b:, 'VM_Selection', {}), 'Regions', [])")
        if len(regions) == len(expected_lines):
            actual_lines = [r["l"] for r in regions]
            if actual_lines == expected_lines:
                return regions
        time.sleep(0.1)
    regions = nv.eval("get(get(b:, 'VM_Selection', {}), 'Regions', [])")
    actual_lines = [r["l"] for r in regions]
    raise TimeoutError(
        f"Expected regions on lines {expected_lines}, got {actual_lines} after {timeout}s"
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

    # Setup <M-n> mapping for Find Under
    nv.command("nmap <M-n> <Plug>(VM-Find-Under)")
    # For visual mode, yank the selection first, then call find_all
    # Yank to default register so find_under can access it
    nv.command("xnoremap <silent> <M-n> y:<C-u>call vm#commands#find_all(1, 0)<CR>")

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
    wait_for_vm_inactive(nv)
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
    wait_for_vm_inactive(nv)
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

    # Insert character and wait for buffer to change
    nv.command('call feedkeys("IX\\<Esc>")')
    expected = [
        "lXine1",
        "lXine2",
        "lXine3",
        "line4",
    ]
    wait_for_buffer_change(nv, expected)

    buf_result = nv.current.buffer[:]

    nv.command("call vm#reset()")
    wait_for_vm_inactive(nv)
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

    # Insert character and wait for buffer to change
    nv.command('call feedkeys("AX\\<Esc>")')
    expected = [
        "lineX1",
        "lineX2",
        "lineX3",
        "line4",
    ]
    wait_for_buffer_change(nv, expected)

    buf_result = nv.current.buffer[:]

    nv.command("call vm#reset()")
    wait_for_vm_inactive(nv)
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
    # The sleeps here are intentional to simulate real typing and test undo grouping
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

    expected_after = [
        "hello word",
        "hello word",
        "hello word",
    ]
    wait_for_buffer_change(nv, expected_after)
    buf_after_insert = nv.current.buffer[:]

    # Now undo - should undo entire " word" insertion in one step
    nv.command("normal! u")
    expected_after_undo = [
        "hello",
        "hello",
        "hello",
    ]
    wait_for_buffer_change(nv, expected_after_undo, timeout=2)

    buf_after_first_undo = nv.current.buffer[:]

    # If first undo didn't restore, try a second undo (bug exists)
    if buf_after_first_undo != expected_after_undo:
        nv.command("normal! u")
        wait_for_buffer_change(nv, expected_after_undo, timeout=2)
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
    wait_for_vm_inactive(nv)
    return all(result for result, _ in test_results), test_results


def test_find_under_at_line_start(nv):
    """Test <M-n> (Find Under) when word starts at column 0."""
    # Force reload the modified autoload file
    nv.command("source autoload/vm/commands.vim")

    nv.current.buffer[:] = [
        "hello",
        "hello",
    ]
    # Position cursor at start of first line (column 0)
    nv.command("normal! gg0")

    # Press <M-n> - should select both "hello" occurrences
    nv.input("<M-n>")
    wait_for_vm_active(nv)

    # Should have 2 regions (both "hello"s selected)
    regions = wait_for_regions(nv, 2)

    test_results = [
        (
            len(regions) == 2,
            f"Expected 2 regions (both hellos), got {len(regions)}: {regions}",
        ),
        (
            regions[0]["l"] == 1,
            f"First region should be on line 1, got line {regions[0]['l']}",
        ),
        (
            regions[1]["l"] == 2,
            f"Second region should be on line 2, got line {regions[1]['l']}",
        ),
    ]

    nv.command("call vm#reset()")
    wait_for_vm_inactive(nv)
    return all(result for result, _ in test_results), test_results


def test_find_next_single_line_multi_match(nv):
    """Test <M-n> doesn't select all matches when multiple on same line."""
    # Force reload the modified autoload file
    nv.command("source autoload/vm/commands.vim")
    nv.command("messages clear")

    nv.current.buffer[:] = [
        "    test test hello test test",
        "    world test test test",
        "    test test hello world test",
        "    test test hello world test",
    ]
    # Position cursor on first "test" of first line
    nv.command(
        "normal! gg0w"
    )  # Go to first line, skip leading spaces, land on first "test"

    # Press <M-n> - should initialize with 2 regions (current + next)
    nv.input("<M-n>")
    wait_for_vm_active(nv)
    regions_after_first = wait_for_regions(nv, 2)

    # Count how many are on line 1 after first <M-n>
    regions_on_line_1_first = sum(1 for r in regions_after_first if r["l"] == 1)

    # Press <M-n> again - should add ONE more "test" (total 3)
    nv.input("<M-n>")
    regions_after_second = wait_for_regions(nv, 3)

    # Count how many are on line 1 after second <M-n>
    regions_on_line_1_second = sum(1 for r in regions_after_second if r["l"] == 1)

    test_results = [
        (
            len(regions_after_first) == 2,
            f"Expected 2 regions after first <M-n>, got {len(regions_after_first)}: "
            f"{regions_after_first}",
        ),
        (
            regions_on_line_1_first == 2,
            f"Expected 2 matches on line 1 after first <M-n>, got {regions_on_line_1_first}",
        ),
        (
            len(regions_after_second) == 3,
            f"Expected 3 regions after second <M-n>, got {len(regions_after_second)}: "
            f"{regions_after_second}",
        ),
        (
            regions_on_line_1_second == 3,
            f"Expected 3 matches on line 1 after second <M-n>, got {regions_on_line_1_second}",
        ),
    ]

    nv.command("call vm#reset()")
    wait_for_vm_inactive(nv)
    return all(result for result, _ in test_results), test_results


def test_visual_find_smart_linewise(nv):
    """Test smart visual find in line-wise mode (creates cursors on selected lines)."""
    nv.command("source autoload/vm/plugs.vim")
    nv.command("source autoload/vm/commands.vim")
    # Call permanent() to register the plugs
    nv.command("call vm#plugs#permanent()")
    nv.command("xmap <M-n> <Plug>(VM-Visual-Find-Smart)")

    nv.current.buffer[:] = [
        "line1 target item",
        "line2 item target",
        "line3 target item",
    ]

    # First, search for "item" to set the search pattern
    nv.command("normal! gg")
    nv.input("/item<CR>")  # Search for "item"

    # Now do line-wise visual selection of lines 1-2
    nv.command("normal! ggV1j")  # Select lines 1-2 in line-wise visual mode

    # Use the smart visual find
    nv.input("<M-n>")  # Should create cursors on lines 1 and 2 only

    wait_for_vm_active(nv)
    regions = wait_for_regions(nv, 2)  # Should have 2 regions (lines 1 and 2)

    # Buffer layout:
    # Line 1: "line1 target item" - "item" at cols 14-17
    # Line 2: "line2 item target" - "item" at cols 7-10
    # Line 3: "line3 target item" - "item" at cols 14-17 (not selected)

    lines_with_regions = sorted([r["l"] for r in regions])
    positions = sorted([(r["l"], r["a"], r["b"]) for r in regions])

    test_results = [
        (
            len(regions) == 2,
            f"Expected 2 regions from line selection, got {len(regions)}",
        ),
        (
            lines_with_regions == [1, 2],
            f"Expected regions on lines [1, 2] only (not line 3), got {lines_with_regions}",
        ),
        (
            positions == [(1, 14, 17), (2, 7, 10)],
            f"Expected regions at [(1, 14, 17), (2, 7, 10)], got {positions}",
        ),
    ]

    nv.command("call vm#reset()")
    wait_for_vm_inactive(nv)
    return all(result for result, _ in test_results), test_results


def test_visual_find_smart_linewise_all_matches(nv):
    """Test linewise visual find selects all matches on selected lines."""
    nv.command("source autoload/vm/plugs.vim")
    nv.command("source autoload/vm/commands.vim")
    nv.command("call vm#plugs#permanent()")
    nv.command("xmap <M-n> <Plug>(VM-Visual-Find-Smart)")

    nv.current.buffer[:] = [
        "test test hello test test",
        "world test test test",
        "test test hello world test",
        "test test hello world test",
    ]

    # Search for "test" to set the search pattern
    nv.command("normal! gg")
    nv.input("/test<CR>")

    # Select first 2 lines in line-wise visual mode
    nv.command("normal! ggV1j")

    # Use smart visual find
    nv.input("<M-n>")

    wait_for_vm_active(nv)
    # Should have 7 regions - all matches on lines 1 and 2
    regions = wait_for_regions(nv, 7)

    # Buffer layout (1-indexed Vim columns):
    # Line 1: "test test hello test test" - "test" at cols 1-4, 6-9, 17-20, 22-25 (4 matches)
    # Line 2: "world test test test" - "test" at cols 7-10, 12-15, 17-20 (3 matches)

    positions = sorted([(r["l"], r["a"], r["b"]) for r in regions])

    test_results = [
        (
            len(regions) == 7,
            f"Expected 7 regions (all matches on lines 1 and 2), got {len(regions)}",
        ),
        (
            positions
            == [
                (1, 1, 4),
                (1, 6, 9),
                (1, 17, 20),
                (1, 22, 25),
                (2, 7, 10),
                (2, 12, 15),
                (2, 17, 20),
            ],
            f"Expected all matches at [(1, 1, 4), (1, 6, 9), (1, 17, 20), (1, 22, 25), "
            f"(2, 7, 10), (2, 12, 15), (2, 17, 20)], got {positions}",
        ),
    ]

    nv.command("call vm#reset()")
    wait_for_vm_inactive(nv)
    return all(result for result, _ in test_results), test_results


def test_search_forward_multiline(nv):
    """Test that / search works across multiple lines in VM mode."""
    nv.command("source autoload/vm/commands.vim")

    nv.current.buffer[:] = [
        "  word1 = rec {",
        '    value1 = "abc123";',
        "    field1 = value1;",
        "  };",
        "  word1 = rec {",
        '    value1 = "def456";',
        "    field1 = value1;",
        "  };",
        "  word1 = rec {",
        '    value1 = "ghi789";',
        "    field1 = value1;",
        "  };",
    ]

    # Start by selecting all "word1" occurrences
    nv.command("normal! gg0w")  # Move to "word1" on first line
    nv.input("<M-n><M-n><M-n>")  # Select all 3 word1 occurrences
    wait_for_vm_active(nv)
    regions_initial = wait_for_regions(nv, 3)

    # Now search forward for "value1" - should move all cursors to their respective value1
    nv.input("/value1<CR>")
    # Wait for regions to move to lines 2, 6, 10
    regions_after_search = wait_for_regions_on_lines(nv, [2, 6, 10])

    test_results = [
        (
            len(regions_initial) == 3,
            f"Expected 3 initial regions, got {len(regions_initial)}",
        ),
        (
            len(regions_after_search) == 3,
            f"Expected 3 regions after search, got {len(regions_after_search)}",
        ),
        (
            [r["l"] for r in regions_after_search] == [2, 6, 10],
            f"Expected cursors on lines [2, 6, 10] after search, "
            f"got {[r['l'] for r in regions_after_search]}",
        ),
    ]

    nv.command("call vm#reset()")
    wait_for_vm_inactive(nv)
    return all(result for result, _ in test_results), test_results


def test_find_visual_selection_incremental(nv):
    """Test <M-n> in visual mode finds next occurrence (incremental, not all)."""
    # Force reload the modified autoload files
    nv.command("source autoload/vm/commands.vim")
    nv.command("source autoload/vm/plugs.vim")
    nv.command("source autoload/vm/search.vim")
    # Call permanent() to register the plugs
    nv.command("call vm#plugs#permanent()")
    nv.command("xmap <M-n> <Plug>(VM-Visual-Find-Smart)")
    nv.command("messages clear")

    nv.current.buffer[:] = [
        "test test hello test test",
        "world test test test",
        "test test hello world test",
    ]
    # Visually select "test test" on first line
    nv.command("normal! gg0")
    nv.input("v8l")  # Select exactly "test test"

    # Press <M-n> - should find next occurrence (incremental, total 2)
    nv.input("<M-n>")
    wait_for_vm_active(nv)
    regions_after_first = wait_for_regions(nv, 2)

    # Press <M-n> again - should add one more (total 3)
    nv.input("<M-n>")
    regions_after_second = wait_for_regions(nv, 3)

    # Press <M-n> again - should add one more (total 4, all occurrences)
    nv.input("<M-n>")
    regions_after_third = wait_for_regions(nv, 4)

    # Buffer layout:
    # Line 1: "test test hello test test" - "test test" at cols 1-9, 17-25
    # Line 2: "world test test test" - "test test" at cols 7-15, 12-20 (overlapping)
    # Line 3: "test test hello world test" - "test test" at cols 1-9

    # After first <M-n>: should have original selection (1:1-9) + next (1:17-25)
    # After second <M-n>: should add line 2 first occurrence (2:7-15)
    # After third <M-n>: should add line 3 occurrence (3:1-9)

    # Extract positions for verification
    positions_first = sorted([(r["l"], r["a"], r["b"]) for r in regions_after_first])
    positions_second = sorted([(r["l"], r["a"], r["b"]) for r in regions_after_second])
    positions_third = sorted([(r["l"], r["a"], r["b"]) for r in regions_after_third])

    test_results = [
        (
            len(regions_after_first) == 2,
            f"Expected 2 regions after first <M-n>, got {len(regions_after_first)}",
        ),
        (
            positions_first == [(1, 1, 9), (1, 17, 25)],
            f"Expected regions at [(1, 1, 9), (1, 17, 25)], got {positions_first}",
        ),
        (
            len(regions_after_second) == 3,
            f"Expected 3 regions after second <M-n>, got {len(regions_after_second)}",
        ),
        (
            positions_second == [(1, 1, 9), (1, 17, 25), (2, 7, 15)],
            f"Expected regions at [(1, 1, 9), (1, 17, 25), (2, 7, 15)], got {positions_second}",
        ),
        (
            len(regions_after_third) == 4,
            f"Expected 4 regions after third <M-n>, got {len(regions_after_third)}",
        ),
        (
            positions_third == [(1, 1, 9), (1, 17, 25), (2, 7, 15), (3, 1, 9)],
            f"Expected regions at [(1, 1, 9), (1, 17, 25), (2, 7, 15), (3, 1, 9)], "
            f"got {positions_third}",
        ),
    ]

    nv.command("call vm#reset()")
    wait_for_vm_inactive(nv)
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
            ("Find Under at line start", test_find_under_at_line_start),
            (
                "Find next with multi-match on line",
                test_find_next_single_line_multi_match,
            ),
            (
                "Find visual selection incremental",
                test_find_visual_selection_incremental,
            ),
            ("Visual find smart linewise", test_visual_find_smart_linewise),
            (
                "Visual find smart linewise all matches",
                test_visual_find_smart_linewise_all_matches,
            ),
            # TODO: Fix multiline search - currently searches only on current line  # pylint: disable=fixme
            # ("Search forward multiline", test_search_forward_multiline),
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
