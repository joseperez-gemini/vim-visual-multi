" Auto-exit VM mode when only one cursor/region remains
" This prevents confusion between VM single cursor and normal vim cursor

if exists('g:loaded_vm_auto_exit')
    finish
endif
let g:loaded_vm_auto_exit = 1

" Allow user to disable this feature
if exists('g:VM_auto_exit_single_region') && !g:VM_auto_exit_single_region
    finish
endif

" Track region count to detect changes
let s:last_region_count = 0

function! s:check_and_exit(...) abort
    " Only check if VM is actually active
    if !exists('b:visual_multi') || !exists('b:VM_Selection')
        return
    endif

    " Get the regions list
    let regions = b:VM_Selection.Regions
    let region_count = len(regions)

    " If we have 1 or fewer regions, exit VM mode
    " Simple and direct - no complex timing needed since we'll start with 2 regions when possible
    if region_count <= 1
        call timer_start(1, {-> s:do_exit()})
    endif

    " Update region count for change detection
    let s:last_region_count = region_count
endfunction

function! s:do_exit(...) abort
    " Double-check VM is still active before exiting
    if !exists('b:visual_multi') || !exists('b:VM_Selection')
        return
    endif

    let regions = b:VM_Selection.Regions
    if len(regions) != 1
        " If not exactly 1 region, use hard reset
        call vm#hard_reset()
        return
    endif

    " We have exactly 1 region - handle based on mode
    let region = regions[0]
    let extend_mode = exists('g:Vm') && get(g:Vm, 'extend_mode', 0)

    if extend_mode
        " Extend mode: restore visual selection
        try
            call s:restore_visual_from_region(region)
        catch
            call vm#hard_reset()
        endtry
    else
        " Cursor mode: restore cursor position and exit
        let cursor_pos = [region.l, region.a]
        call vm#hard_reset()
        call cursor(cursor_pos[0], cursor_pos[1])
    endif
endfunction

function! s:restore_visual_from_region(region) abort
    " Extract region bounds
    let start_line = a:region.l
    let end_line = a:region.L
    let start_col = a:region.a
    let end_col = a:region.b

    " Clear VM first
    call vm#hard_reset()

    " Restore visual selection based on region type
    if start_line == end_line
        " Single line selection
        call cursor(start_line, start_col)
        execute "normal! v" . (end_col - start_col) . "l"
    else
        " Multi-line selection
        call cursor(start_line, start_col)
        execute "normal! V" . (end_line - start_line) . "j"
    endif
endfunction

function! s:enhanced_region_check(...) abort
    " More frequent checking during VM operations, but less aggressive
    if !exists('b:visual_multi') || !exists('b:VM_Selection')
        return
    endif

    let current_count = len(b:VM_Selection.Regions)

    " Only trigger on significant changes, not during navigation
    " This reduces interference with find_next operations
    if current_count <= 1 && s:last_region_count > 1
        " Region count dropped to 1 - schedule delayed check
        call s:check_and_exit()
    endif

    let s:last_region_count = current_count
endfunction

" Setup autocmds
augroup VMAutoExit
    autocmd!
    " Check after VM starts - with longer delay to ensure all regions are created
    autocmd User visual_multi_start call s:delayed_check()

    " Check after any VM command that might change region count
    autocmd User visual_multi_after_cmd call s:check_and_exit()

    " Enhanced checking on cursor movement for merge scenarios
    autocmd CursorMoved,CursorMovedI * if exists('b:visual_multi') | call s:enhanced_region_check() | endif
augroup END

function! s:delayed_check() abort
    " Use a timer but capture the buffer number to maintain context
    let bufnr = bufnr('%')
    call timer_start(100, {-> s:check_in_buffer(bufnr)})
endfunction

function! s:check_in_buffer(bufnr) abort
    " Switch to the correct buffer and check
    if bufexists(a:bufnr)
        let current_buf = bufnr('%')
        if current_buf != a:bufnr
            execute 'buffer' a:bufnr
        endif
        call s:check_and_exit()
        if current_buf != a:bufnr && bufexists(current_buf)
            execute 'buffer' current_buf
        endif
    endif
endfunction
