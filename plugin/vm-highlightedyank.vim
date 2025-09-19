" Integration with vim-highlightedyank plugin
" Prevents interference during VM internal operations

if exists('g:loaded_vm_highlightedyank')
    finish
endif
let g:loaded_vm_highlightedyank = 1

" The actual functions are in autoload/vm/highlightedyank.vim