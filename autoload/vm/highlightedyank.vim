" Integration with vim-highlightedyank plugin
" Prevents interference during VM internal operations

" Check if highlightedyank plugin is available
function! s:highlightedyank_available() abort
    return exists('#highlightedyank#TextYankPost')
endfunction

" Store the original autocmd state
let s:autocmd_was_enabled = 0

" Disable highlightedyank TextYankPost autocmd
function! s:disable_highlightedyank() abort
    if s:highlightedyank_available()
        autocmd! highlightedyank TextYankPost
        let s:autocmd_was_enabled = 1
        return 1
    endif
    return 0
endfunction

" Re-enable highlightedyank TextYankPost autocmd
function! s:enable_highlightedyank() abort
    if s:autocmd_was_enabled
        augroup highlightedyank
            autocmd!
            autocmd TextYankPost * call highlightedyank#debounce()
        augroup END
        let s:autocmd_was_enabled = 0
    endif
endfunction

" Execute a command with highlightedyank temporarily disabled
function! vm#highlightedyank#execute_silent(cmd) abort
    let was_disabled = s:disable_highlightedyank()
    try
        execute a:cmd
    finally
        if was_disabled
            call s:enable_highlightedyank()
        endif
    endtry
endfunction

" Execute normal mode command with highlightedyank temporarily disabled
function! vm#highlightedyank#normal_silent(cmd) abort
    let was_disabled = s:disable_highlightedyank()
    try
        execute 'normal! ' . a:cmd
    finally
        if was_disabled
            call s:enable_highlightedyank()
        endif
    endtry
endfunction

" Execute keepjumps normal command with highlightedyank temporarily disabled
function! vm#highlightedyank#keepjumps_normal_silent(cmd) abort
    let was_disabled = s:disable_highlightedyank()
    try
        execute 'keepjumps normal! ' . a:cmd
    finally
        if was_disabled
            call s:enable_highlightedyank()
        endif
    endtry
endfunction