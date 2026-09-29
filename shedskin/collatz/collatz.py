# find collatz/3x+1 delay records
# copyright mark dufour 2023
#
# tricks:
# -uses parity sequences to take multiple steps at once
# (https://en.wikipedia.org/wiki/Collatz_conjecture)
# -skips about half of the numbers since they cannot be records
# (https://math.stackexchange.com/questions/60573/reducing-the-time-to-calculate-collatz-sequences)
#
# caveat:
# - requires shedskin --long (64-bit integers.. no 128-bit support yet)
# - doesn't check for 64-bit overflow (in generated C++)!
#
# results (N=100000000) checked against:
#
# http://www.ericr.nl/wondrous/delrecs.html

import time
from tpy import int64

def step(n: int64, extra: bool = False) -> int64:
    if n % 2 == 0:
        return n // 2
    else:
        if extra:
            return (3*n + 1) // 2
        else:
            return (3*n + 1)

def main() -> None:
    N: int64 = 10000000
    K: int64 = 17
    bmask = 2**K-1

    # lookups to perform K steps in one
    lookup_multistep: list[int64] = [i for i in range(0, 2**K)]
    lookup_c: list[int64] = [0 for _ in lookup_multistep]

    for k in range(K):
        lookup_c = [c + (i%2) for (i, c) in zip(lookup_multistep, lookup_c)]
        lookup_multistep = [step(i, True) for i in lookup_multistep]

    lookup_pow = [3**c for c in range(K+1)]

    # lookup for final steps (< 2**K)
    lookup_tail = [0]
    for n in range(1, 2**K):
        steps = 0
        while n != 1:
            n = step(n)
            steps += 1
        lookup_tail.append(steps)

    print('1 2') # skipped record

    t0 = time.time()

    delay_record = 0
    rest9 = 1
    for n in range(2, N):
        # skip 2, 4, 5, 8 mod 9 and 5 mod 8
        # as these cannot be records (see link in top)
        rest9 += 1
        if rest9 == 9:
            rest9 = 0
        if rest9 in (2, 4, 5, 8):
            continue
        if n & 7 == 5: # 5 mod 8
           continue

        # use multistep lookups (see link in top)
        orign = n
        steps: int64 = 0

        while n > bmask:
            a = n >> K
            b = n & bmask

            c = lookup_c[b]
            d = lookup_multistep[b]

            steps += 2*c + (K-c)

            n = a*lookup_pow[c]+d

        # add final steps
        steps += lookup_tail[n]

        # check record
        if steps > delay_record:
            delay_record = steps
            print(delay_record, orign)

    print(f'{(N/((time.time()-t0))):.2f} numbers/second')

if __name__ == '__main__':
    t0 = 0.0
    for n in range(10):
        if n == 5:
            t0 = time.time()  # pypy has stabilized
        main()
    print(f'TIME {(time.time()-t0):.2f}')
