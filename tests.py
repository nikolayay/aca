tests = {
    'programs/adds_unrolled.asm': (lambda cpu: cpu.RF[1] == 90),
    'programs/adds.asm': (lambda cpu: cpu.RF[1] == 90),
    'programs/pi.asm': (lambda cpu: ''.join([str(val) for val in cpu.MEM[-8:]]) == '31415926535897932384626433832795'),
    'programs/gcd_iterative.asm': (lambda cpu: cpu.RF[0] == 30),
    'programs/bubblesort.asm': (lambda cpu: cpu.MEM == sorted([8, 14, 7, 22, 15, 1, 25, 13, 23, 24, 2, 25, 30, 9, 19, 28, 3, 23, 21, 19, 28, 24, 9, 6, 29, 12, 4, 29, 19, 24])),
    'programs/mat_mul_vec.asm': (lambda cpu: cpu.MEM[-10:] == [385, 935, 1485, 2035, 2585, 3135, 3685, 4235, 4785, 5335]),
    'programs/vector_adds.asm': (lambda cpu: cpu.MEM[-30:] == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 0, 2, 4, 6, 8, 10, 12, 14, 16, 18]),
    'programs/vector_adds_unrolled.asm': (lambda cpu: cpu.MEM[-30:] == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 0, 2, 4, 6, 8, 10, 12, 14, 16, 18]),
    'programs/mat_mul.asm': (lambda cpu: cpu.MEM[-64:] == [1380, 1416, 1452, 1488, 1524, 1560, 1596, 1632, 3236, 3336, 3436, 3536, 3636, 3736, 3836, 3936, 5092, 5256, 5420, 5584, 5748, 5912, 6076, 6240, 6948, 7176, 7404, 7632, 7860, 8088, 8316, 8544, 8804, 9096, 9388, 9680, 9972, 10264, 10556, 10848, 10660, 11016, 11372, 11728, 12084, 12440, 12796, 13152, 12516, 12936, 13356, 13776, 14196, 14616, 15036, 15456, 14372, 14856, 15340, 15824, 16308, 16792, 17276, 17760]),
    'programs/scheduling_block.asm': (lambda cpu: cpu.RF[12] == -88),
    'programs/simple_bubblesort.asm': (lambda cpu: cpu.MEM == [1, 2, 3, 3, 3, 4])
}
