; int A[10] = {...};
; int B[10] = {...};
; int C[10] = {...};
; 
; C[0] = A[0] + B[0];
; C[1] = A[1] + B[1];
; C[2] = A[2] + B[2];
; ...

.A: 25 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9     ; int A[10] = {...}
.B: 25 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9     ; int B[10] = {...}
.C: 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0     ; int C[10] = {...}

start:
    lw $0 A($4)             ; $0 = A[0]
    lw $1 B($4)             ; $1 = B[0]
    add $3 $0 $1           ; $3 = A[0] + B[0]
    sw $3 C($4)             ; c[0] = $3

    addi $4 $4 1
    lw $0 A($4)             ; $0 = A[1]
    lw $1 B($4)             ; $1 = B[1]
    add $3 $0 $1           ; $3 = A[1] + B[1]
    sw $3 C($4)             ; c[1] = $3

    addi $4 $4 1
    lw $0 A($4)             ; $0 = A[2]
    lw $1 B($4)             ; $1 = B[2]
    add $3 $0 $1           ; $3 = A[2] + B[2]
    sw $3 C($4)             ; c[2] = $3

    addi $4 $4 1
    lw $0 A($4)             ; $0 = A[3]
    lw $1 B($4)             ; $1 = B[3]
    add $3 $0 $1           ; $3 = A[3] + B[3]
    sw $3 C($4)             ; c[3] = $3

    addi $4 $4 1
    lw $0 A($4)             ; $0 = A[4]
    lw $1 B($4)             ; $1 = B[4]
    add $3 $0 $1           ; $3 = A[4] + B[4]
    sw $3 C($4)             ; c[4] = $3

    addi $4 $4 1
    lw $0 A($4)             ; $0 = A[5]
    lw $1 B($4)             ; $1 = B[5]
    add $3 $0 $1           ; $3 = A[5] + B[5]
    sw $3 C($4)             ; c[5] = $3

    addi $4 $4 1
    lw $0 A($4)             ; $0 = A[6]
    lw $1 B($4)             ; $1 = B[6]
    add $3 $0 $1           ; $3 = A[6] + B[6]
    sw $3 C($4)             ; c[6] = $3

    addi $4 $4 1
    lw $0 A($4)             ; $0 = A[7]
    lw $1 B($4)             ; $1 = B[7]
    add $3 $0 $1           ; $3 = A[7] + B[7]
    sw $3 C($4)             ; c[7] = $3

    addi $4 $4 1
    lw $0 A($4)             ; $0 = A[8]
    lw $1 B($4)             ; $1 = B[8]
    add $3 $0 $1           ; $3 = A[8] + B[8]
    sw $3 C($4)            ; c[8] = $3

    addi $4 $4 1
    lw $0 A($4)             ; $0 = A[9]
    lw $1 B($4)             ; $1 = B[9]
    add $3 $0 $1           ; $3 = A[9] + B[9]
    sw $3 C($4)            ; c[9] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[10]
    lw $1 B($4)            ; $1 = B[10]
    add $3 $0 $1           ; $3 = A[10] + B[10]
    sw $3 C($4)           ; c[10] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[11]
    lw $1 B($4)            ; $1 = B[11]
    add $3 $0 $1           ; $3 = A[11] + B[11]
    sw $3 C($4)           ; c[11] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[12]
    lw $1 B($4)            ; $1 = B[12]
    add $3 $0 $1           ; $3 = A[12] + B[12]
    sw $3 C($4)           ; c[12] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[13]
    lw $1 B($4)            ; $1 = B[13]
    add $3 $0 $1           ; $3 = A[13] + B[13]
    sw $3 C($4)           ; c[13] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[14]
    lw $1 B($4)            ; $1 = B[14]
    add $3 $0 $1           ; $3 = A[14] + B[14]
    sw $3 C($4)           ; c[14] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[15]
    lw $1 B($4)            ; $1 = B[15]
    add $3 $0 $1           ; $3 = A[15] + B[15]
    sw $3 C($4)            ; c[15] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[16]
    lw $1 B($4)            ; $1 = B[16]
    add $3 $0 $1           ; $3 = A[16] + B[16]
    sw $3 C($4)           ; c[16] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[17]
    lw $1 B($4)            ; $1 = B[17]
    add $3 $0 $1           ; $3 = A[17] + B[17]
    sw $3 C($4)           ; c[17] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[18]
    lw $1 B($4)            ; $1 = B[18]
    add $3 $0 $1           ; $3 = A[18] + B[18]
    sw $3 C($4)           ; c[18] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[19]
    lw $1 B($4)            ; $1 = B[19]
    add $3 $0 $1           ; $3 = A[19] + B[19]
    sw $3 C($4)           ; c[19] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[20]
    lw $1 B($4)            ; $1 = B[20]
    add $3 $0 $1           ; $3 = A[20] + B[20]
    sw $3 C($4)           ; c[20] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[21]
    lw $1 B($4)            ; $1 = B[21]
    add $3 $0 $1           ; $3 = A[21] + B[21]
    sw $3 C($4)          ; c[21] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[22]
    lw $1 B($4)            ; $1 = B[22]
    add $3 $0 $1           ; $3 = A[22] + B[22]
    sw $3 C($4)            ; c[22] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[23]
    lw $1 B($4)            ; $1 = B[23]
    add $3 $0 $1           ; $3 = A[23] + B[23]
    sw $3 C($4)            ; c[23] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[24]
    lw $1 B($4)            ; $1 = B[24]
    add $3 $0 $1           ; $3 = A[24] + B[24]
    sw $3 C($4)            ; c[24] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[25]
    lw $1 B($4)            ; $1 = B[25]
    add $3 $0 $1           ; $3 = A[25] + B[25]
    sw $3 C($4)            ; c[25] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[26]
    lw $1 B($4)            ; $1 = B[26]
    add $3 $0 $1           ; $3 = A[26] + B[26]
    sw $3 C($4)           ; c[26] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[27]
    lw $1 B($4)            ; $1 = B[27]
    add $3 $0 $1           ; $3 = A[27] + B[27]
    sw $3 C($4)            ; c[27] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[28]
    lw $1 B($4)            ; $1 = B[28]
    add $3 $0 $1           ; $3 = A[28] + B[28]
    sw $3 C($4)            ; c[28] = $3

    addi $4 $4 1
    lw $0 A($4)            ; $0 = A[29]
    lw $1 B($4)            ; $1 = B[29]
    add $3 $0 $1           ; $3 = A[29] + B[29]
    sw $3 C($4)            ; c[29] = $3

    addi $31 $31 1         ; set register 31 to 1 (halt)