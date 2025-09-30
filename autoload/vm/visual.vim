""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" Add / Subtract
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

fun! vm#visual#add(mode) abort
    " Add visually selected pattern as region
    call s:init()
    if a:mode ==# 'v'     | call s:vchar()
    elseif a:mode ==# 'V' | call s:vline()
    else                  | let s:v.direction = s:vblock(1)
    endif

    call s:visual_merge()

    if a:mode ==# 'V'
        if !g:VM_use_first_cursor_in_line
            if s:v.silence
                call s:G.select_region(len(s:R())-1)
            else
                " Force select the last region to ensure proper cursor positioning
                call s:G.select_region(len(s:R())-1)
            endif
        else
            let ix = s:G.lines_with_regions(0, s:R()[-1].l)[s:R()[-1].l][0]
            call s:G.select_region(ix)
        endif
    else
        if s:v.silence
            call s:G.select_region(len(s:R())-1)
        else
            " Force select the last region to ensure proper cursor positioning
            call s:G.select_region(len(s:R())-1)
        endif
    endif
endfun

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

fun! vm#visual#subtract(mode) abort
    " Subtract a pattern from regions map.
    call s:init()
    if a:mode ==# 'v'     | call s:vchar()
    elseif a:mode ==# 'V' | call s:vline()
    else                  | call s:vblock(1)
    endif

    call s:visual_subtract()
    call s:G.update_and_select_region({'id': s:v.IDs_list[-1]})
    if X | call s:G.cursor_mode() | endif
endfun

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

fun! vm#visual#reduce() abort
    " Remove regions outside of visual selection.
    let X = s:backup_map()
    call s:G.rebuild_from_map(s:Bytes, [s:F.pos2byte("'<"), s:F.pos2byte("'>")])
    if X | call s:G.cursor_mode() | endif
    call s:G.update_and_select_region()
endfun

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

fun! vm#visual#cursors(mode) abort
    " Create cursors, one for each line of the visual selection.
    call s:init()
    let [pos, start, end] = [getpos('.')[1:2],
                \            getpos("'<")[1:2], getpos("'>")[1:2]]

    call s:create_cursors(start, end, a:mode, pos)

    if a:mode ==# 'V' && get(g:, 'VM_autoremove_empty_lines', 1)
        call s:G.remove_empty_lines()
    endif

    call s:G.update_and_select_region(pos)
endfun

fun! vm#visual#cursors_with_pos(mode, cursor_pos) abort
    " Create cursors with explicit cursor position (for preserving block cursor corner).
    call s:init()
    let [start, end] = [getpos("'<")[1:2], getpos("'>")[1:2]]

    call s:create_cursors(start, end, a:mode, a:cursor_pos)

    if a:mode ==# 'V' && get(g:, 'VM_autoremove_empty_lines', 1)
        call s:G.remove_empty_lines()
    endif

    call s:G.update_and_select_region(a:cursor_pos)
endfun

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

fun! vm#visual#split() abort
    " Split regions with regex pattern.
    call s:init()
    if !len(s:R()) | return
    elseif !s:X()  | return s:F.msg('Not in cursor mode.')  | endif

    echohl Type   | let pat = input('Pattern to remove > ') | echohl None
    if empty(pat) | return s:F.msg('Command aborted.')      | endif

    let start = s:R()[0]                "first region
    let stop = s:R()[-1]                "last region

    call s:F.Cursor(start.A)            "check for a match first
    if !search(pat, 'nczW', stop.L)     "search method: accept at cursor position
        call s:F.msg("\t\tPattern not found")
        return s:G.select_region(s:v.index)
    endif

    call s:backup_map()

    "backup old patterns and create new regions
    let oldsearch = copy(s:v.search)
    call s:V.Search.get_slash_reg(pat)

    call s:G.get_all_regions(start.A, stop.B)

    "subtract regions and rebuild from map
    call s:visual_subtract()
    call s:V.Search.join(oldsearch)
    call s:G.update_and_select_region()
endfun

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

fun! vm#visual#find_in_selection() abort
    " Find all occurrences of the current search pattern within visual selection.

    " Get visual mode first (before any initialization)
    let mode = visualmode()

    " Initialize VM if not already active
    if !get(get(g:, 'Vm', {}), 'buffer', 0)
        call vm#init_buffer(0)
    endif

    call s:init()

    " Get the current search pattern - use oldsearch backup if @/ is empty
    let pat = empty(@/) ? get(s:v, 'oldsearch', [''])[0] : @/
    if empty(pat)
        call s:F.msg('No search pattern set. Use / to search first.')
        return
    endif

    " For character-wise visual mode, find all occurrences in entire file
    if mode ==# 'v'
        " Use the current search pattern for the entire file
        call s:V.Search.get_slash_reg(pat)
        call s:G.get_all_regions()
        call s:G.update_and_select_region()
        return
    endif

    " Get visual selection boundaries
    let [startline, startcol] = getpos("'<")[1:2]
    let [endline, endcol] = getpos("'>")[1:2]

    " Save current search pattern and use it
    call s:V.Search.get_slash_reg(pat)

    " Get all regions within the selection boundaries
    call cursor(startline, 1)

    " Check if there's at least one match in the selection
    if !search(pat, 'nczW', endline)
        call s:F.msg('Pattern not found in selection')
        return
    endif

    " Find all matches within the selection
    let [ows, ei] = [&wrapscan, &eventignore]
    set nowrapscan eventignore=all

    call cursor(startline, 1)

    " Find first match
    if search(pat, 'czW', endline)
        call vm#highlightedyank#execute_silent('silent keepjumps normal! ygn')
        let match_line = getpos("'[")[1]
        if match_line >= startline && match_line <= endline
            if mode ==# 'V' || (mode ==# 'v')
                " For line-wise or character-wise, just check line boundaries
                call s:G.new_region()
            elseif mode == "\<C-v>"
                " For block-wise, check that BOTH start and end are within column boundaries
                let match_start_col = getpos("'[")[2]
                let match_end_col = getpos("']")[2]
                if match_start_col >= startcol && match_end_col <= endcol
                    call s:G.new_region()
                endif
            endif
        endif
    endif

    " Find remaining matches
    while 1
        if !search(pat, 'zW', endline)
            break
        endif
        call vm#highlightedyank#execute_silent('silent keepjumps normal! ygn')
        let match_line = getpos("'[")[1]

        if match_line > endline
            break
        elseif match_line >= startline
            if mode ==# 'V' || (mode ==# 'v')
                call s:G.new_region()
            elseif mode == "\<C-v>"
                " For block-wise, check that BOTH start and end are within column boundaries
                let match_start_col = getpos("'[")[2]
                let match_end_col = getpos("']")[2]
                if match_start_col >= startcol && match_end_col <= endcol
                    call s:G.new_region()
                endif
            endif
        endif
    endwhile

    let &wrapscan = ows
    let &eventignore = ei

    if !len(s:R())
        call s:F.msg('No matches found in selection')
        return
    endif

    call s:G.update_and_select_region()
endfun


""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" Helpers
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

fun! s:vchar() abort
    "characterwise selection
    call vm#highlightedyank#execute_silent('silent keepjumps normal! `<y`>`]')
    call s:G.check_mutliline(0, s:G.new_region())
endfun


fun! s:vline() abort
    "linewise selection
    let [line1, line2] = [getpos("'<")[1], getpos("'>")[1]]
    for n in range(line1, line2)
        call cursor(n, 1)
        " Exit any existing visual mode first, then select current line
        execute "normal! \<Esc>"
        call vm#highlightedyank#keepjumps_normal_silent('V$y')
        call s:G.new_region()
    endfor
endfun


fun! s:vblock(extend) abort
    "blockwise selection
    let start = getpos("'<")[1:2]
    let end = getpos("'>")[1:2]
    let orig_cursor = getpos('.')[1:2]


    if ( start[1] > end[1] )
        let s = end[1] | let e = start[1]
    else
        let s = start[1] | let e = end[1]
    endif


    if start == end
        if a:extend
            call vm#highlightedyank#execute_silent('keepjumps normal! gvy')
            return s:G.new_region()
        else | return | endif
    endif

    for n in range(start[0], end[0])
        call cursor(n, s)
        if s:F.char_under_cursor() =~ '\v\S'
            if s == e
                call vm#highlightedyank#execute_silent('keepjumps normal! vy')
            else
                call vm#highlightedyank#execute_silent('keepjumps normal! \<C-v>'.( e - s ).'l'.'y')
            endif
            call s:G.new_region()
        endif
    endfor

    " Position cursor based on where it originally was
    " Set direction for newly created regions
    if len(s:R()) > 0
        let num_regions_before = len(s:R())
        let regions_to_fix = s:R()[max([0, num_regions_before-3]):]  " Get the last few regions we just created

        if orig_cursor[1] == end[1]  " Cursor was at end column
            " Put cursor at end of each newly created region
            for region in regions_to_fix
                let region.dir = 1  " Set direction to forward (cursor at end)
            endfor
        else
            " Cursor was at start column
            for region in regions_to_fix
                let region.dir = 0  " Set direction to backward (cursor at start)
            endfor
        endif
    endif

    return s:v.direction
endfun

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

fun! s:create_cursors(start, end, mode, ...) abort
    "create cursors at each line of visual selection
    "start, end are lists: [line, column]
    "mode: visual mode ('v', 'V', or ctrl-v)
    "a:1 (optional): original cursor position [line, column]

    if a:mode ==# 'V'
        " Line-wise: start at first non-blank of each line (cursor mode)
        call cursor(a:start[0], 1)
        normal! ^
        call s:G.new_cursor()

        " Add cursors for remaining lines, each at first non-blank
        if a:end[0] > a:start[0]
            for line_num in range(a:start[0] + 1, a:end[0])
                call cursor(line_num, 1)
                normal! ^
                if s:F.char_under_cursor() =~ '\v\S'
                    call s:G.new_cursor()
                endif
            endfor
        endif
    elseif a:mode ==# "\<C-v>"
        " Block-wise: create regions matching the visual block
        " In visual block mode, when called from visual mode mapping,
        " the cursor position should still be correct
        let [actual_line, actual_col] = a:0 > 0 ? a:1 : [line('.'), col('.')]

        " Save the original visual marks before we mess with them
        let saved_vstart = getpos("'<")
        let saved_vend = getpos("'>")


        let [start_col, end_col] = [min([a:start[1], a:end[1]]), max([a:start[1], a:end[1]])]

        " Determine cursor position relative to selection
        let cursor_at_bottom = (actual_line == a:end[0])
        let cursor_at_top = (actual_line == a:start[0])
        let cursor_at_right = (actual_col == end_col)
        let cursor_at_left = (actual_col == start_col)

        " Determine if cursor should be at end of regions (1) or start (0)
        let region_dir = cursor_at_right ? 1 : 0

        let regions_created = []

        for line_num in range(a:start[0], a:end[0])
            call cursor(line_num, start_col)
            " Only create region if there's content in the block area
            if s:F.char_under_cursor() =~ '\v\S'
                " Create a region for just the block area on this line
                " Use visual selection but save/restore marks after
                let chars_to_select = end_col - start_col
                if chars_to_select == 0
                    " Single column selection - select just one character
                    call vm#highlightedyank#execute_silent('keepjumps normal! vy')
                else
                    " Multi-column selection
                    call vm#highlightedyank#execute_silent('keepjumps normal! v' . chars_to_select . 'ly')
                endif
                call s:G.new_region()
                let regions_created += [len(s:R()) - 1]  " Store region index
            endif
        endfor

        " Restore the original visual marks
        call setpos("'<", saved_vstart)
        call setpos("'>", saved_vend)

        " Set the visual mode to block by briefly entering and exiting block mode
        let save_cursor = getpos('.')
        call cursor(saved_vstart[1], saved_vstart[2])
        execute "normal! \<C-v>"
        call cursor(saved_vend[1], saved_vend[2])
        execute "normal! \<Esc>"
        call setpos('.', save_cursor)

        " Position active cursor based on original cursor position
        if len(regions_created) > 0
            let regions = s:R()

            " Set direction for ALL regions based on whether cursor was left/right
            for idx in regions_created
                let regions[idx].dir = region_dir
            endfor

            " Select the appropriate region based on top/bottom position
            let target_region_idx = cursor_at_bottom ? regions_created[-1] : regions_created[0]

            " Select the target region
            call s:G.select_region(target_region_idx)
        endif
    else
        " Character-wise: use original column positioning
        call cursor(a:start[0], a:start[1])

        " Ensure there's at least one cursor at the starting position
        if s:F.char_under_cursor() =~ '\v\S' || a:start[0] == a:end[0]
            call s:G.new_cursor()
        endif

        " Add cursors for remaining lines
        if a:end[0] > a:start[0]
            while line('.') < a:end[0]
                call vm#commands#add_cursor_down(0, 1)
            endwhile
        endif
    endif
endfun

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

let s:R   = { -> s:V.Regions      }
let s:v   = { -> b:VM_Selection.Vars }
let s:X   = { -> g:Vm.extend_mode  }
let s:Bytes = {}

fun! s:init() abort
    let s:V = b:VM_Selection | let s:v = s:V.Vars
    let s:F = s:V.Funcs      | let s:G = s:V.Global
endfun

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

fun! s:backup_map() abort
    "backup regions to merge, store X flag and return to cursor mode if active
    for r in s:R()
        let s:Bytes[r.id] = [r.A, r.B]
    endfor
    let X = s:X()
    if X | call s:G.cursor_mode() | endif
    return X
endfun

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

fun! s:visual_merge() abort
    "merge regions and update the regions list
    call s:G.merge_regions()
    for r in s:R()
        let s:Bytes[r.id] = [r.A, r.B]
    endfor
    call s:G.update_regions()
endfun

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

fun! s:visual_subtract() abort
    "subtract regions and rebuild from map
    let X = s:X()
    for r in s:R()
        if has_key(s:Bytes, r.id)
            unlet s:Bytes[r.id]
        endif
    endfor
    call s:G.rebuild_from_map(s:Bytes)
    if X | call s:G.cursor_mode() | endif
endfun

" vim: et ts=4 sw=4 sts=4 :
