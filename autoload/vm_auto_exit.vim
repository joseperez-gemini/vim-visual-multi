" Auto-exit VM mode when only one cursor/region remains
" This prevents confusion between VM single cursor and normal vim cursor

function! vm_auto_exit#check_and_exit() abort
    " Only check if VM is actually active
    if !exists('b:visual_multi') || !exists('b:VM_Selection')
        return
    endif

    " Skip auto-exit if temporarily disabled
    if exists('b:VM_disable_auto_exit')
        return
    endif

    " Get the regions list
    let regions = b:VM_Selection.Regions

    " If we have 1 or fewer regions, exit VM mode
    if len(regions) <= 1
        " Use a timer to avoid potential recursive calls during VM operations
        call timer_start(1, {-> vm_auto_exit#do_exit()})
    endif
endfunction

function! vm_auto_exit#do_exit() abort
    " Double-check VM is still active before exiting
    if exists('b:visual_multi') && exists('b:VM_Selection')
        " Restore cursor position if we had one region
        if has_key(b:VM_Selection, 'Regions') && len(b:VM_Selection.Regions) == 1
            let region = b:VM_Selection.Regions[0]
            call cursor(region.l, region.a)
        endif
        call vm#hard_reset()
    endif
endfunction

function! vm_auto_exit#setup_autocmds() abort
    augroup VMAutoExit
        autocmd!
        " Check after VM starts (for immediate single-region cases)
        autocmd User visual_multi_start call timer_start(10, {-> vm_auto_exit#check_and_exit()})

        " Check after any VM command that might change region count
        autocmd User visual_multi_after_cmd call vm_auto_exit#check_and_exit()

        " Check on cursor movement (for when regions get removed by movement/escape)
        autocmd CursorMoved,CursorMovedI * if exists('b:visual_multi') | call vm_auto_exit#check_and_exit() | endif
    augroup END
endfunction

" Initialize the autocmds
call vm_auto_exit#setup_autocmds()
