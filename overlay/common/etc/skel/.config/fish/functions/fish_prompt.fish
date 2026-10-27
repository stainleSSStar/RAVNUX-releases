function fish_prompt
    set -l previous_status $status
    set_color c084fc
    printf '%s' (prompt_pwd)
    if test $previous_status -ne 0
        set_color fb7185
        printf ' [%s]' $previous_status
    end
    set_color f472b6
    printf ' ❯ '
    set_color normal
end
