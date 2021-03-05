
    addi $2 $2 8
    addi $4 $4 4
    addi $8 $8 2
    addi $14 $14 90

    idiv $0 $2 $4      ; $r0  = 8 / 4
    add $10 $0 $8      ; $r10 = $r0 + 2
    sub $12 $8 $14     ; $12  = 2 - 90


    addi $31 $31 1          ; halt